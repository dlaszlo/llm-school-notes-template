"""All ordinary Git inspections preserve owner HEAD; local fixtures only."""
import json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import test_app as f
import test_interactive as interactive
import test_review_r3 as r3
import test_review_r15 as r15
from school_notes.common import Blocked,atomic_json,file_hash
from school_notes import cli
from school_notes.verify import Git

class R17Tests(f.Base):
    setUp=f.PilotTests.setUp
    supervisor=r15.R15Tests.supervisor
    remote_clone=r15.R15Tests.remote_clone
    other_git=r15.R15Tests.other_git

    def prepare_remote(self):
        clone=self.remote_clone();(clone/'wiki/math/remote.md').write_text('remote independent change');self.other_git(clone,'add','.');self.other_git(clone,'commit','-m','Remote independent change');return clone

    def test_N1701_default_inspection_never_merges_and_standalone_observe_does(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');clone=self.prepare_remote();self.other_git(clone,'push','origin','HEAD:main')
        with self.assertRaisesRegex(Blocked,'behind'):Git(self.repo,supervisor.lock).inspect()
        self.assertEqual(old,self.git('rev-parse','HEAD'));supervisor.observe_git('student');self.assertEqual(self.other_git(clone,'rev-parse','HEAD'),self.git('rev-parse','HEAD'))

    def test_N1701_initialize_requires_exact_clean_head_without_implicit_ff(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');clone=self.prepare_remote();self.other_git(clone,'push','origin','HEAD:main');self.config['state_db']=str(self.root/'fresh.sqlite');self.config['learners']['student']['observed_sha']=old
        with self.assertRaisesRegex(Blocked,'behind'):cli.initialize(self.config,supervisor.lock)
        self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertFalse(Path(self.config['state_db']).exists())

    def test_N1701_sync_second_fetch_race_preserves_head_even_standalone(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');clone=self.prepare_remote();original=Git.git;fetches=[]
        def concurrent(git,*args,**kwargs):
            if git.repo==self.repo.resolve() and args[:1]==('fetch',):
                fetches.append(True)
                if len(fetches)==2:self.other_git(clone,'push','origin','HEAD:main')
            return original(git,*args,**kwargs)
        with patch.object(Git,'git',concurrent):supervisor.sync(['student'])
        self.assertEqual(2,len(fetches));self.assertEqual(old,self.git('rev-parse','HEAD'));blocks=self.state.rows("SELECT payload,error FROM jobs WHERE kind='runtime_block' AND state='blocked'");self.assertTrue(any(json.loads(row['payload']).get('category')=='git' and 'behind' in row['error'] for row in blocks));self.assertTrue(self.drive.downloads)

    def test_N1701_joined_candidate_after_observe_remote_race_blocks_before_agent(self):
        supervisor=self.supervisor();supervisor.actor_origin='owner-session';supervisor.observe_git('student');old=self.git('rev-parse','HEAD');job=self.state.enqueue('ingest','student','candidate-race',{'manifest':{'files':[]}});clone=self.prepare_remote();self.other_git(clone,'push','origin','HEAD:main')
        with self.assertRaisesRegex(Blocked,'behind'):supervisor.candidate(self.state.job(job))
        self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertFalse(self.state.job(job)['payload'].get('worktree'));self.assertFalse(supervisor.agents.calls)

class R17ProcessTests(f.Base):
    setUp=f.PilotTests.setUp
    config_file=interactive.InteractiveTests.config_file
    owner=interactive.InteractiveTests.owner
    supervisor=r15.R15Tests.supervisor
    remote_clone=r15.R15Tests.remote_clone
    other_git=r15.R15Tests.other_git

    def execute_joined(self,command,hook=''):
        cfg=self.config_file();out=self.root/'joined-command.json';script=self.root/'joined-controller.py';script.write_text("import json,sys,subprocess\nfrom pathlib import Path\nfrom school_notes import cli\nfrom school_notes.verify import Git\n"+hook+"\nraise SystemExit(cli.main(['--config',"+repr(str(cfg))+","+repr(command)[1:]+"))\n")
        program=f"import subprocess,sys,json;from pathlib import Path;p=subprocess.run([sys.executable,'-B',{str(script)!r}],capture_output=True,text=True);Path({str(out)!r}).write_text(json.dumps({{'code':p.returncode,'err':p.stderr,'out':p.stdout}}))"
        process=self.owner(program);_,err=process.communicate(timeout=15);self.assertEqual(0,process.returncode,err);return json.loads(out.read_text())

    def prepare_remote(self):return R17Tests.prepare_remote(self)

    def test_N1701_joined_rebase_candidate_stale_remote_keeps_head_and_snapshot(self):
        supervisor=self.supervisor();supervisor.observe_drive('student');job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);old=self.git('rev-parse','HEAD');candidate=Git(self.repo,supervisor.lock).worktree(self.root/'retained',old);payload={**job['payload'],'base':old,'worktree':str(candidate.repo),'git_identity':candidate.identity};self.state.update_job(job['id'],'blocked',payload=payload);supervisor.lock.__exit__();clone=self.prepare_remote();self.other_git(clone,'push','origin','HEAD:main');before=file_hash(candidate.repo/'wiki/log.md')
        result=self.execute_joined(['rebase-candidate',str(job['id'])]);self.assertEqual(2,result['code'],result);self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertEqual(before,file_hash(candidate.repo/'wiki/log.md'));self.assertFalse(self.state.job(job['id'])['payload'].get('candidate_history'))

    def test_N1701_joined_request_public_stale_remote_keeps_head(self):
        job=self.state.enqueue('ingest','student','completed-source',{});self.state.update_job(job,'complete');old=self.git('rev-parse','HEAD');manifest=self.root/'proposal.json';atomic_json(manifest,{});clone=self.prepare_remote();self.other_git(clone,'push','origin','HEAD:main')
        result=self.execute_joined(['request-public',str(job),str(manifest)]);self.assertEqual(2,result['code'],result);self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertFalse(self.state.rows("SELECT id FROM jobs WHERE kind='public_release'"))

    def test_N1701_joined_finalize_external_push_preflight_race_keeps_head(self):
        supervisor=self.supervisor();job,_=r3.R3Tests.external_job(self,supervisor);old=self.git('rev-parse','HEAD');supervisor.lock.__exit__();clone=self.prepare_remote()
        hook=f'''original=Git.git
fetches=[]
def concurrent(git,*args,**kwargs):
 if git.repo==Path({str(self.repo)!r}).resolve() and args[:1]==('fetch',):
  fetches.append(True)
  if len(fetches)==2:subprocess.run(['git','-C',{str(clone)!r},'push','origin','HEAD:main'],check=True,capture_output=True)
 return original(git,*args,**kwargs)
Git.git=concurrent
'''
        result=self.execute_joined(['finalize-external',str(job)],hook);self.assertEqual(2,result['code'],result);self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertTrue(self.state.job(job)['payload'].get('manifest_commit'));effects=self.state.rows("SELECT state FROM effects WHERE job_id=? AND kind='git-push'",(job,));self.assertEqual(['planned'],[row['state'] for row in effects])
