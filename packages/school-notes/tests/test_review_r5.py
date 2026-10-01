"""R5 integrity/recovery regressions; local bytes/Git and controlled adapters."""
import copy,hashlib,http.client,json
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r1 as r1
import test_review_r2 as r2
import test_review_r3 as r3
from school_notes import admin
from school_notes.cli import finalize_external
from school_notes.common import Blocked,atomic_json,digest,file_hash
from school_notes.drive import capture,DriveAPI,InventoryChanged
from school_notes.verify import Git

class R5Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def test_N501_short_capture_never_enters_progress_and_retry_downloads(self):
        original=self.drive.download
        def short(identity,path):self.drive.downloads.append(identity);Path(path).write_bytes(fixture.PNG[:16])
        self.drive.download=short;destination=self.root/'short'
        with self.assertRaises(InventoryChanged):capture(self.drive,'package',destination,reserve=0)
        progress=destination/'progress.json'
        self.assertFalse(progress.exists(),'unverified bytes must not become reusable progress')
        self.assertEqual(fixture.PNG[:16],(destination/'original/01.png').read_bytes())
        self.drive.download=original;manifest=capture(self.drive,'package',self.root/'retry',reserve=0)
        self.assertEqual(['file','file'],self.drive.downloads);self.assertEqual(self.drive.data['file'],Path(manifest['files'][0]['local']).read_bytes())

    def test_N501_every_reused_byte_checks_current_size_and_md5(self):
        previous=capture(self.drive,'package',self.root/'first',reserve=0)
        for mode in ('size','md5'):
            bad=copy.deepcopy(previous);local=Path(bad['files'][0]['local']);original=self.drive.data['file'];content=original[:-1] if mode=='size' else original[:-1]+bytes([original[-1]^1]);local.write_bytes(content);bad['files'][0].update(size=len(content),sha256=file_hash(local))
            # Exact old snapshot plus a self-consistent attacker/legacy progress
            # hash cannot replace authoritative current Drive size/MD5.
            before=len(self.drive.downloads);result=capture(self.drive,'package',self.root/mode,reserve=0,previous=bad)
            self.assertEqual(before+1,len(self.drive.downloads));self.assertEqual(original,Path(result['files'][0]['local']).read_bytes())
            Path(previous['files'][0]['local']).write_bytes(original)

    def test_N501_md5_mismatch_fresh_not_reusable(self):
        original=self.drive.download
        def wrong(identity,path):original(identity,path);p=Path(path);data=p.read_bytes();p.write_bytes(data[:-1]+bytes([data[-1]^1]))
        self.drive.download=wrong
        with self.assertRaises(InventoryChanged):capture(self.drive,'package',self.root/'wrong',reserve=0)
        self.assertFalse((self.root/'wrong/progress.json').exists())

    def test_N501_http_incomplete_read_maps_to_bounded_block(self):
        from types import SimpleNamespace
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):raise http.client.IncompleteRead(b'partial',20)
        api=DriveAPI.__new__(DriveAPI);api.window=None;api.drive=SimpleNamespace(token='synthetic',opener=SimpleNamespace(open=lambda *a,**k:Response()))
        with self.assertRaisesRegex(Blocked,'interrupted'):api.download('controlled-id',self.root/'partial.png')
        self.assertTrue((self.root/'partial.png').exists())

    def test_N502_ignored_output_rebase_preserves_bytes_and_completes(self):
        (self.repo/'.gitignore').write_text('wiki/assets/*.png\n');self.git('add','.');self.git('commit','-m','Owner ignore');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        class WritesIgnored(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                result,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):
                    target=Path(cwd)/'wiki/assets/hidden.png';target.parent.mkdir(exist_ok=True);target.write_bytes(fixture.PNG)
                return result,path
        supervisor.agents=WritesIgnored(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertIn('ignored',job['error']);old=Path(job['payload']['worktree']);retained=old/'wiki/assets/hidden.png';sha=file_hash(retained)
        (self.repo/'.gitignore').write_text('# Owner removed incorrect generated-output ignore\n');self.git('add','.');self.git('commit','-m','Owner correct ignore');self.git('push','origin','HEAD:main');supervisor.observe_git('student')
        external=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")[0]['id']);manifest=json.loads((self.repo/'publication/pilot.json').read_text());head=self.git('rev-parse','HEAD')
        evidence={'job_id':external['id'],'base':external['payload']['base'],'head':head,'changes':external['payload']['changes'],'open_reviews':[],'open_questions':[],'reason':'Owner corrected exact ignored-output policy','closure_records':self.evidence_records(),'manifest_impact':{'path':'publication/pilot.json','sha256':file_hash(self.repo/'publication/pilot.json'),'manifest':manifest}}
        admin.acknowledge_maintenance(supervisor,external['id'],evidence);admin.rebase_candidate(supervisor,job['id']);history=self.state.job(job['id'])['payload']['candidate_history'][0];self.assertEqual(sha,history['changes']['wiki/assets/hidden.png']);self.assertEqual(sha,file_hash(retained))
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertNotEqual(str(old),current['payload']['worktree']);self.assertEqual(sha,file_hash(retained))

    def test_N504_verified_external_reentry_resolves_symlink_jobs_path(self):
        jobs=Path(self.config['jobs_dir']);jobs.mkdir(exist_ok=True);link=self.root/'job-link';link.symlink_to(jobs,target_is_directory=True);self.config['jobs_dir']=str(link)
        supervisor=self.supervisor();jobid,base=r3.R3Tests.external_job(self,supervisor);first=finalize_external(supervisor,jobid);second=finalize_external(supervisor,jobid)
        self.assertEqual(first['commit'],second['commit']);self.assertEqual('complete',self.state.job(jobid)['state'])

    def test_N507_nested_git_policy_files_are_protected(self):
        git=Git(self.repo);base=git.head()
        for name in ('wiki/.gitattributes','wiki/math/.gitignore','sources/.gitattributes','docs/evidence/.gitignore'):
            p=self.repo/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text('*.md text eol=crlf\n')
            with self.assertRaisesRegex(Blocked,'protected'):git.changes(base)
            p.unlink()

class R5PublicTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    public_setup=r1.PublicR1Tests.public_setup
    run_public=r1.PublicR1Tests.run_public
    evidence_records=r2.R2Tests.evidence_records

    def test_N509_closed_public_new_request_retains_old_job(self):
        supervisor,private,public,api=self.public_setup();old=self.state.job(public);evidence={'job_id':public,'revision_seq':old['revision_seq'],'base':old['payload']['base'],'payload_sha256':digest(old['payload']),'reason':'Owner preserved aborted preview; explicit new proposal','closure_records':self.evidence_records()};admin.close_job(supervisor,public,evidence)
        manifest=old['payload']['public_manifest'];new=admin.request_public(supervisor,private,manifest);self.assertNotEqual(public,new['job_id']);self.assertEqual('closed_unprocessed',self.state.job(public)['state']);self.assertIn('manual_closure',self.state.job(public)['payload'])
        effect=self.state.effect(public,'github-release','synthetic','x','old-unknown');self.state.effect_state(effect['stable_key'],'unknown')
        with self.assertRaisesRegex(Blocked,'unknown'):admin.request_public(supervisor,private,manifest)
