"""R6 finite candidate recovery, complete public family and byte/receipt gates."""
import http.client,json,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import test_app as fixture
import test_review_r1 as r1
import test_review_r2 as r2
from school_notes import admin
from school_notes.cli import wrapper
from school_notes.common import Blocked,atomic_json,digest,file_hash
from school_notes.drive import DriveAPI
from school_notes.publication import GitHub
from school_notes.verify import Git

class R6Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def test_N601_deleted_candidate_rebase_same_ack_preserves_and_completes(self):
        supervisor=self.supervisor()
        class Deletes(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                result,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):(Path(cwd)/'wiki/math/index.md').unlink()
                return result,path
        supervisor.agents=Deletes(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);old=Path(job['payload']['worktree']);base=job['payload']['base'];log=file_hash(old/'wiki/log.md')
        admin.rebase_candidate(supervisor,job['id']);current=self.state.job(job['id']);self.assertEqual(base,current['payload']['base']);self.assertEqual(log,current['payload']['candidate_history'][0]['changes']['wiki/log.md']);self.assertFalse((old/'wiki/math/index.md').exists())
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        self.assertEqual('complete',self.state.job(job['id'])['state']);self.assertFalse((old/'wiki/math/index.md').exists())

    def test_N601_candidate_violation_classes_cover_paths(self):
        from school_notes.verify import CandidateViolation
        git=Git(self.repo);base=git.head()
        for name in ('docs/notes.md','wiki/math/.gitignore'):
            p=self.repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('preserved bad candidate')
            with self.assertRaises(CandidateViolation):git.changes(base)
            p.unlink()
        source=self.repo/'wiki/math/link.md';source.symlink_to(self.repo/'wiki/log.md')
        with self.assertRaises(CandidateViolation):git.changes(base)
        source.unlink();(self.repo/'wiki/math/index.md').unlink()
        with self.assertRaises(CandidateViolation):git.changes(base)

    def test_N603_github_http_exception_preserves_unknown_effect(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*a):raise http.client.IncompleteRead(b'partial',7)
        api=GitHub.__new__(GitHub);api.window=None;api.settings={'repository':'owner/controlled'};api.token='synthetic';api.base='https://api.github.com/repos/owner/controlled';api.opener=SimpleNamespace(open=lambda *a,**k:Response())
        effect=self.state.effect(None,'github-release','controlled','hash','incomplete-release')
        with self.assertRaisesRegex(Blocked,'interrupted'):self.state.perform_effect(effect,lambda e:api.request('POST','/releases',{}),lambda e:None)
        self.assertEqual('unknown',self.state.rows("SELECT state FROM effects WHERE stable_key='incomplete-release'")[0]['state'])
        with patch('school_notes.publication.urllib.request.urlopen',return_value=Response()):
            with self.assertRaisesRegex(Blocked,'interrupted'):api.live_get('https://example.test/release.json')

    def test_N603_drive_request_http_exception_bounded_without_shared_change(self):
        class ApiError(Exception):pass
        class Refused(Exception):pass
        api=DriveAPI.__new__(DriveAPI);api.window=None;api.module=SimpleNamespace(ApiError=ApiError,Refused=Refused)
        def broken(*args):raise http.client.IncompleteRead(b'partial',2)
        api.drive=SimpleNamespace(request=broken)
        with self.assertRaisesRegex(Blocked,'interrupted'):api.request('GET','https://www.googleapis.com/drive/v3/files/controlled')

    def test_N604_wrapper_records_metadata_drift_and_original_exit(self):
        supervisor=self.supervisor();program="import subprocess;from pathlib import Path;subprocess.run(['git','config','owner.session','trusted-change'],check=True);Path('wiki/math/owner.md').write_text('owner retained');raise SystemExit(7)"
        supervisor.lock.__exit__();receipt=wrapper(self.config,'student',[sys.executable,'-c',program]);self.assertEqual(7,receipt['exit_code']);self.assertEqual('recorded',receipt['state']);self.assertTrue(receipt['metadata_drift']);self.assertIn('wiki/math/owner.md',receipt['hashes'])
        path=next((self.root/'jobs').glob('interactive-*/receipt.json'));self.assertEqual(receipt,json.loads(path.read_text()));self.assertEqual([],self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'"))

    def test_N604_wrapper_cleanup_error_still_records_exit_and_failure(self):
        supervisor=self.supervisor()
        with patch('school_notes.session.terminate_group',side_effect=OSError('controlled cleanup failure')):
            supervisor.lock.__exit__();receipt=wrapper(self.config,'student',[sys.executable,'-c','raise SystemExit(4)'])
        self.assertEqual(4,receipt['exit_code']);self.assertEqual('recovery-required',receipt['state']);self.assertTrue(receipt['cleanup_errors']);self.assertEqual(receipt,json.loads(next((self.root/'jobs').glob('interactive-*/receipt.json')).read_text()))

    def test_N605_nonmanifest_crlf_blocks_before_source_review_then_rebase(self):
        (self.repo/'.gitattributes').write_text('* text=auto eol=lf\n');self.git('add','.');self.git('commit','-m','Owner ordinary LF policy');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        class CRLF(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                result,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate' and not job['payload'].get('candidate_history'):
                    target=Path(cwd)/'wiki/log.md';target.write_bytes(target.read_bytes().replace(b'\n',b'\r\n'));result['file_changes']=[{**f,'sha256':file_hash(Path(cwd)/f['path'])} for f in result['file_changes']];atomic_json(path,result)
                return result,path
        supervisor.agents=CRLF(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('normaliz',job['error']);self.assertFalse(any(p.startswith('source_review') for p in supervisor.agents.calls));old=Path(job['payload']['worktree']);raw=(old/'wiki/log.md').read_bytes();admin.rebase_candidate(supervisor,job['id'])
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        self.assertEqual('complete',self.state.job(job['id'])['state']);self.assertEqual(raw,(old/'wiki/log.md').read_bytes())

    def test_N605_every_changed_blob_verified_and_filter_never_executes(self):
        git=Git(self.repo);base=git.head();(self.repo/'.gitattributes').write_text('wiki/log.md filter=forbidden\n');self.git('add','.');self.git('commit','-m','Owner explicit filter fixture');base=self.git('rev-parse','HEAD');canary=self.root/'filter-executed';self.git('config','filter.forbidden.clean','touch '+str(canary));git=Git(self.repo);(self.repo/'wiki/log.md').write_text('changed ordinary log\n')
        with self.assertRaises(Blocked):git.changes(base)
        self.assertFalse(canary.exists())

    def test_N605_nonmanifest_index_blob_must_match_reviewed_bytes(self):
        from school_notes.common import PreconditionFailed
        (self.repo/'.gitattributes').write_text('* text=auto eol=lf\n');self.git('add','.');self.git('commit','-m','Owner LF policy');git=Git(self.repo);base=git.head();(self.repo/'wiki/log.md').write_bytes(b'# Reviewed log\r\n');changes={'wiki/log.md':file_hash(self.repo/'wiki/log.md')};manifest=json.loads((self.repo/'publication/pilot.json').read_text());job={'id':1,'kind':'ingest','revision_seq':1,'payload':{'base':base}};identity={'name':'Owner','email':'owner@example.test'}
        # Bypass only the earlier changes() gate to exercise the independent
        # final index gate, as if this were a retained historical candidate.
        with patch.object(git,'changes',return_value=changes):
            with self.assertRaises(PreconditionFailed):git.commit(job,changes,[],identity,'publication/pilot.json',manifest)
        self.assertEqual(base,git.head())

    def test_N605_nonmanifest_committed_blob_reconcile_rejects_normalization(self):
        (self.repo/'.gitattributes').write_text('* text=auto eol=lf\n');self.git('add','.');self.git('commit','-m','Owner LF policy');git=Git(self.repo);base=git.head();(self.repo/'wiki/log.md').write_bytes(b'# Reviewed log\r\n');changes={'wiki/log.md':file_hash(self.repo/'wiki/log.md')};manifest=json.loads((self.repo/'publication/pilot.json').read_text());self.git('add','wiki/log.md');self.git('commit','-m','Historical normalized commit');job={'payload':{'base':base}}
        with self.assertRaisesRegex(Blocked,'blob differs'):git.reconcile_commit({},job,changes,[],'publication/pilot.json',manifest)

    def test_N605_unreviewed_index_entry_blocks_without_reset(self):
        from school_notes.common import PreconditionFailed
        extra=self.repo/'wiki/math/unlisted.md';extra.write_text('original\n');self.git('add','.');self.git('commit','-m','Owner baseline unlisted page');git=Git(self.repo);base=git.head();extra.write_text('preserved staged bytes\n');self.git('add','wiki/math/unlisted.md');oid=self.git('rev-parse',':wiki/math/unlisted.md');extra.write_text('original\n');(self.repo/'wiki/log.md').write_text('reviewed log\n');changes={'wiki/log.md':file_hash(self.repo/'wiki/log.md')};manifest=json.loads((self.repo/'publication/pilot.json').read_text());job={'id':1,'kind':'ingest','revision_seq':1,'payload':{'base':base}}
        with self.assertRaises(PreconditionFailed):git.commit(job,changes,[],{'name':'Owner','email':'owner@example.test'},'publication/pilot.json',manifest)
        self.assertEqual(base,git.head());self.assertEqual(oid,self.git('rev-parse',':wiki/math/unlisted.md'));self.assertEqual('original\n',extra.read_text())

class R6PublicTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    public_setup=r1.PublicR1Tests.public_setup
    evidence_records=r2.R2Tests.evidence_records

    def test_N602_active_retry_idempotent_and_all_family_unknown_guard(self):
        supervisor,private,public,api=self.public_setup();original=self.state.job(public);self.state.update_job(public,'closed_unprocessed');manifest=original['payload']['public_manifest'];first=admin.request_public(supervisor,private,manifest);second=admin.request_public(supervisor,private,manifest);self.assertEqual(first['job_id'],second['job_id']);self.assertNotEqual(public,first['job_id'])
        retry=first['job_id'];effect=self.state.effect(retry,'github-release','controlled','hash','retry-unknown');self.state.effect_state(effect['stable_key'],'unknown');self.state.update_job(retry,'blocked')
        with self.assertRaisesRegex(Blocked,'unknown'):admin.request_public(supervisor,private,manifest)
        self.assertEqual(2,len(self.state.rows("SELECT id FROM jobs WHERE kind='public_release'")))
