"""Real process/lock/session tests. None establish native provider capability."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import test_app as f
import test_review_r2 as r2
from school_notes import admin,session
from school_notes.cli import build_preview
from school_notes.common import Blocked,Busy,RunLock,Window,atomic_json,file_hash,run
from school_notes.pipeline import Supervisor,register_external
from school_notes.state import State
from school_notes.verify import Git

APP=str(f.REPO/'packages/school-notes')

class InteractiveTests(f.Base):
    setUp=f.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def config_file(self):
        self.config['drive_tool']=str(self.root/'unused_drive.py')
        self.config['learners']['student'].update(drive_config_dir=str(self.root/'unused_auth'),drive_evidence=str(self.root/'unready.json'),observed_sha=self.git('rev-parse','HEAD'))
        path=self.root/'config.json';atomic_json(path,self.config);return path

    def cli(self,*args,env=None):
        childenv=dict(os.environ,PYTHONPATH=APP,PYTHONDONTWRITEBYTECODE='1');childenv.update(env or {})
        return subprocess.run([sys.executable,'-m','school_notes','--config',str(self.config_file()),*args],env=childenv,capture_output=True,text=True,timeout=15)

    def wait_file(self,path):
        deadline=time.monotonic()+8
        while not path.exists():
            if time.monotonic()>deadline:self.fail('timed out waiting for '+str(path))
            time.sleep(.02)

    def owner(self,program):
        env=dict(os.environ,PYTHONPATH=APP,PYTHONDONTWRITEBYTECODE='1')
        process=subprocess.Popen([sys.executable,'-m','school_notes','--config',str(self.config_file()),'interactive','student','--',sys.executable,'-c',program],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda:process.kill() if process.poll() is None else None)
        return process

    def test_nested_controller_answer_status_and_authorization_rejection(self):
        job=self.state.enqueue('runtime_block','student','manual-content',{})
        q=self.state.question(job,'content','context','What lesson?');answer=self.root/'answer.txt';answer.write_text('Owner content answer')
        result=self.root/'nested.json';cfg=self.config_file()
        program=f'''import json,subprocess,sys;from pathlib import Path
base=[sys.executable,'-m','school_notes','--config',{str(cfg)!r}]
results=[]
for cmd in (["answer",{str(q)!r},{str(answer)!r}],["status"],["inspect-job",{str(job)!r}],["approve-public",{str(job)!r},"a"*64]):
 p=subprocess.run(base+cmd,capture_output=True,text=True);results.append({{'code':p.returncode,'out':p.stdout,'err':p.stderr}})
Path({str(result)!r}).write_text(json.dumps(results))
'''
        process=self.owner(program);out,err=process.communicate(timeout=15);self.assertEqual(0,process.returncode,err)
        results=json.loads(result.read_text());self.assertEqual([0,0,0,2],[r['code'] for r in results]);self.assertIn('outside protected session',results[-1]['err'])
        self.assertEqual('owner-session',self.state.rows('SELECT origin FROM questions WHERE id=?',(q,))[0]['origin'])
        self.assertIn('paused: protected owner session student since ',json.loads(results[1]['out'])['scheduled_processing'])
        self.assertTrue(json.loads(out)['pinned_default'] is False)

    def test_long_owner_session_scheduler_busy_and_direct_edits_preserved(self):
        self.config['run_seconds']=1;ready=self.root/'ready';stop=self.root/'stop';edited=self.repo/'wiki/math/owner.md'
        program=f"from pathlib import Path;import time;Path({str(edited)!r}).write_text('retained owner bytes');Path({str(ready)!r}).write_text('ready');\nwhile not Path({str(stop)!r}).exists():time.sleep(.02)"
        process=self.owner(program);self.wait_file(ready);time.sleep(1.1)
        self.assertIsNone(process.poll());before=file_hash(self.root/'state.sqlite');result=self.cli('run-once');self.assertEqual(75,result.returncode,result.stderr);self.assertEqual(before,file_hash(self.root/'state.sqlite'));self.assertEqual('retained owner bytes',edited.read_text())
        stop.write_text('done');out,err=process.communicate(timeout=8);self.assertEqual(0,process.returncode,err);receipt=json.loads(out);self.assertIn('wiki/math/owner.md',receipt['hashes']);self.assertFalse(receipt['review']);self.assertEqual([],self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'"))

    def test_nested_dirty_run_once_leaves_job_and_sync_observes_drive(self):
        job=self.state.enqueue('runtime_block','student','queued-owner',{});before=self.state.job(job)
        output=self.root/'dirty-result.json';cfg=self.config_file()
        program=f"from pathlib import Path;import subprocess,sys,json;Path('wiki/math/owner.md').write_text('owner editing');p=subprocess.run([sys.executable,'-m','school_notes','--config',{str(cfg)!r},'run-once','--job',{str(job)!r}],capture_output=True,text=True);Path({str(output)!r}).write_text(json.dumps({{'code':p.returncode,'err':p.stderr}}))"
        process=self.owner(program);_,err=process.communicate(timeout=15);self.assertEqual(0,process.returncode,err);self.assertEqual(75,json.loads(output.read_text())['code']);self.assertEqual(before,self.state.job(job))
        supervisor=self.supervisor();supervisor.sync(['student']);self.assertTrue(self.drive.downloads);self.assertEqual('owner editing',(self.repo/'wiki/math/owner.md').read_text())
        self.assertFalse(self.state.rows('SELECT * FROM attempts'))

    def test_readonly_inspect_status_database_and_reports_unchanged(self):
        job=self.state.enqueue('runtime_block','student','inspect-readonly',{});before=file_hash(self.root/'state.sqlite');self.config_file()
        with RunLock(self.config['lock_file']):
            for command in (('status',),('inspect-job',str(job))):
                result=self.cli(*command);self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual(before,file_hash(self.root/'state.sqlite'));self.assertFalse((self.root/'reports').exists())
        readonly=State(self.root/'state.sqlite',readonly=True)
        try:
            with self.assertRaises(__import__('sqlite3').OperationalError):readonly.meta('attempted-write','forbidden')
        finally:readonly.close()

    def test_foreign_marker_stale_identity_and_other_learner_fail_closed(self):
        ready=self.root/'ready';stop=self.root/'stop';process=self.owner(f"from pathlib import Path;import time;Path({str(ready)!r}).write_text('ready');\nwhile not Path({str(stop)!r}).exists():time.sleep(.02)");self.wait_file(ready)
        result=self.cli('status',env={session.ENV:str(session.paths(self.config)[1])});self.assertEqual(2,result.returncode);self.assertIn('not the recorded',result.stderr)
        value=session.marker(self.config);value['command']['start_ticks']='stale';atomic_json(session.paths(self.config)[1],value)
        result=self.cli('status',env={session.ENV:str(session.paths(self.config)[1])});self.assertEqual(2,result.returncode);self.assertIn('stale session',result.stderr)
        stop.write_text('stop');process.communicate(timeout=8)
        # Nested learner mismatch is tested at the actual process boundary.
        self.config['learners']['other']=copy.deepcopy(self.config['learners']['student']);other=self.state.enqueue('runtime_block','other','other-private',{'private':'other learner secret'});cfg=self.config_file();outpath=self.root/'scoped.json'
        program=f"import subprocess,sys,json;from pathlib import Path;base=[sys.executable,'-m','school_notes','--config',{str(cfg)!r}];values=[];\nfor args in (['status'],['inspect-job',{str(other)!r}]):\n p=subprocess.run(base+args,capture_output=True,text=True);values.append({{'code':p.returncode,'out':p.stdout,'err':p.stderr}})\nPath({str(outpath)!r}).write_text(json.dumps(values))"
        process=self.owner(program);_,err=process.communicate(timeout=15);self.assertEqual(0,process.returncode,err);values=json.loads(outpath.read_text());self.assertNotIn('other-private',values[0]['out']);self.assertNotIn('other learner secret',values[0]['out']);self.assertEqual(2,values[1]['code'])

    def test_wrapper_sigkill_marker_and_child_exclusion_then_explicit_recovery(self):
        ready=self.root/'ready';stop=self.root/'stop';process=self.owner(f"from pathlib import Path;import time;Path({str(ready)!r}).write_text('ready');\nwhile not Path({str(stop)!r}).exists():time.sleep(.02)");self.wait_file(ready);process.kill();process.wait(timeout=3)
        self.assertEqual(75,self.cli('run-once').returncode)
        with self.assertRaises(Busy):session.recover(self.config)
        stop.write_text('done');time.sleep(.15)
        process.communicate(timeout=3)
        recovered=session.recover(self.config);self.assertEqual('recovered',recovered['state']);self.assertEqual('available',session.diagnostics(self.config)['scheduled_processing'])

    def test_independent_worker_deadline_survives_controller_sigkill_and_retains_unknown_effect(self):
        worker=self.root/'worker.json';controller=self.root/'controller.py';cfg=self.config_file()
        worker_code=f"import os,subprocess,sys,time,json;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True);Path({str(worker)!r}).write_text(json.dumps({{'worker':os.getpid(),'grandchild':p.pid}}));time.sleep(30)"
        controller.write_text(f"from school_notes.common import RunLock,run;from school_notes.state import State;\nwith RunLock({self.config['lock_file']!r}) as lock:\n s=State({self.config['state_db']!r});e=s.effect(None,'upload','controlled','a'*64,'controlled-orphan');s.effect_state(e['stable_key'],'inflight');run([{sys.executable!r},'-c',{worker_code!r}],{str(self.root)!r},timeout=10,lock=lock)\n")
        process=subprocess.Popen([sys.executable,str(controller)],env=dict(os.environ,PYTHONPATH=APP));self.wait_file(worker);ids=json.loads(worker.read_text());process.kill();process.wait(timeout=3)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and any(session.same_process(session.process_identity(pid)) for pid in ids.values()):time.sleep(.02)
        self.assertFalse(any(session.process_identity(pid) and session.process_identity(pid)['state']!='Z' for pid in ids.values()))
        while True:
            try:
                with RunLock(self.config['lock_file']):self.state.recover()
                break
            except Busy:
                if time.monotonic()>deadline:raise
                time.sleep(.02)
        self.assertEqual('unknown',self.state.rows("SELECT state FROM effects WHERE stable_key='controlled-orphan'")[0]['state'])

    def test_finite_worker_receives_operation_fd_only_not_session_env_guard(self):
        with session.Admission(self.config),RunLock(self.config['lock_file']) as lock:
            guard=session.paths(self.config)[0];fd=os.open(guard,os.O_RDWR);os.set_inheritable(fd,True)
            try:
                result=run([sys.executable,'-c',"import os,json;from pathlib import Path;print(json.dumps({'env':os.environ.get('SCHOOL_NOTES_SESSION'),'fds':[os.readlink(p) for p in Path('/proc/self/fd').iterdir() if p.exists()]}))"],self.root,lock=lock,env={session.ENV:'must-not-leak'})
                value=json.loads(result);self.assertIsNone(value['env']);self.assertIn(self.config['lock_file'],value['fds']);self.assertNotIn(str(guard),value['fds'])
            finally:os.close(fd)

    def test_default_launcher_pinned_override_not_misreported(self):
        self.config['interactive_command']=[sys.executable,'/tmp/trusted-codex-placeholder.py']
        command=session.default_command(self.config);self.assertEqual(['--no-daemon','--model','gpt-6.1-sol','-c','model_reasoning_effort="high"'],command[-5:])
        self.config['interactive_command']=['relative']
        with self.assertRaises(Blocked):session.default_command(self.config)

    def test_external_committed_hash_dedup_review_wait_complete_and_current_ack(self):
        git=Git(self.repo);base=git.head();path=self.repo/'wiki/math/owner.md';path.write_text('committed owner bytes\n');self.git('add','.');self.git('commit','-m','Owner change');head=git.head();path.write_text('dirty later bytes\n')
        job=register_external(self.state,git,'student',base,head);self.assertNotEqual(file_hash(path),self.state.job(job)['payload']['changes']['wiki/math/owner.md'])
        for state in ('review_wait','complete'):
            self.state.update_job(job,state,'external_review');again=register_external(self.state,git,'student',base,head,ready=False);self.assertEqual(job,again);self.assertEqual(state,self.state.job(job)['state'])
        with self.state.db:self.state.db.execute("UPDATE observations SET ack_sha=? WHERE id='baseline:student'",(head,))
        path.write_text('committed owner bytes\n');self.git('push','origin','HEAD:main')
        receipt=session.wrapper(self.config,'student',[sys.executable,'-c','pass']);self.assertEqual(head,receipt['review_base']);self.assertEqual(1,len(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")))

    def test_unpushed_owner_commit_and_diverged_range_not_processed(self):
        supervisor=self.supervisor();(self.repo/'wiki/math/owner.md').write_text('owner committed');self.git('add','.');self.git('commit','-m','Unpushed owner')
        job=self.state.enqueue('runtime_block','student','queued-unpushed',{});before=self.state.job(job)
        with self.assertRaises(Busy):supervisor.preflight_owner(['student'])
        self.assertEqual(before,self.state.job(job));base=self.git('rev-parse','HEAD~1');head=self.git('rev-parse','HEAD');self.git('checkout','-b','other-range',base);(self.repo/'wiki/math/other.md').write_text('separate branch');self.git('add','.');self.git('commit','-m','Diverged')
        with self.assertRaisesRegex(Blocked,'diverged'):register_external(self.state,Git(self.repo),'student',head,self.git('rev-parse','HEAD'))

    def test_build_preview_jobs_only_no_state_upload_acceptance(self):
        supervisor=self.supervisor();before=file_hash(self.root/'state.sqlite')
        with patch('school_notes.cli.Renderer',f.FakeRenderer):result=build_preview(supervisor,'student')
        self.assertTrue(Path(result['preview']).is_relative_to(self.root/'jobs'));self.assertEqual(before,file_hash(self.root/'state.sqlite'));self.assertEqual([],self.drive.writes);self.assertFalse(self.state.rows('SELECT * FROM reviews'));self.assertFalse(self.state.rows('SELECT * FROM jobs'))

    def test_default_interactive_entry_records_exact_pinned_request_and_controller_guidance(self):
        capture=self.root/'default-argv.json';launcher=self.root/'synthetic-launcher.py'
        launcher.write_text("import json,sys;from pathlib import Path;Path("+repr(str(capture))+").write_text(json.dumps(sys.argv[1:]))")
        self.config['interactive_command']=[sys.executable,str(launcher)]
        result=self.cli('interactive','student');self.assertEqual(0,result.returncode,result.stderr);receipt=json.loads(result.stdout)
        self.assertTrue(receipt['pinned_default']);self.assertEqual('unverified',receipt['native_proof']);self.assertEqual(str(self.root/'config.json'),receipt['config_path']);args=json.loads(capture.read_text());self.assertEqual(['--no-daemon','--model','gpt-6.1-sol','-c','model_reasoning_effort="high"'],args[:5]);self.assertIn('run-once --job JOB_ID',args[-1]);self.assertIn(str(self.root/'config.json'),receipt['controller_command'])

    def test_provisional_accepted_wait_complete_never_reset_and_initial_wait_promotes(self):
        path=self.repo/'wiki/math/owner.md';path.write_text('owner committed\n');git=Git(self.repo);base=git.head();self.git('add','.');self.git('commit','-m','Owner range');head=git.head()
        job=register_external(self.state,git,'student',base,head,ready=False)
        # Original unreviewed provisional wait can become a processable range.
        self.assertEqual(job,register_external(self.state,git,'student',base,head,ready=True));self.assertEqual('queued',self.state.job(job)['state'])
        payload=self.state.job(job)['payload'];payload['provisional']=True
        receipt=self.root/'accepted-control.json';atomic_json(receipt,{'accepted_control':True})
        with self.state.db:self.state.db.execute("INSERT INTO reviews(job_id,path,sha256,inputs_hash,scope,state) VALUES (?,?,?,?,?,'accepted')",(job,str(receipt),file_hash(receipt),'d'*64,'control'))
        for state in ('review_wait','complete'):
            self.state.update_job(job,state,payload=payload,error='review accepted; finalize-external required')
            before=self.state.job(job);self.assertEqual(job,register_external(self.state,git,'student',base,head,ready=True));self.assertEqual(before,self.state.job(job))

    def test_recovery_refuses_replaced_guard_inode_even_dead_marker(self):
        guard,pointer=session.paths(self.config);guard.write_bytes(b'');guard.chmod(0o600)
        atomic_json(pointer,{'state':'recovery-required','guard_inode':[0,0],'wrapper':{'pid':99999999,'start_ticks':'absent','uid':os.getuid()},'command':None})
        before=file_hash(pointer)
        with self.assertRaisesRegex(Blocked,'inode changed'):session.recover(self.config)
        self.assertEqual(before,file_hash(pointer))
