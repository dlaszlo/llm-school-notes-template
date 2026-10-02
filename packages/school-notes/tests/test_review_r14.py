"""R14 learner isolation, committed maintenance and finite transport recovery."""
import copy
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from unittest.mock import patch
import test_app as f
import test_review_r1 as r1
import test_review_r2 as r2
import test_review_r3 as r3
from school_notes import admin,cli,session
from school_notes.agents import Agent
from school_notes.common import Blocked,RunLock,TimedOut,Window,atomic_json,digest,file_hash,run
from school_notes.pipeline import Supervisor,register_external
from school_notes.verify import Git

class R14Tests(f.Base):
    setUp=f.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def accepted(self,job):
        path=self.root/f'accepted-{job}.json';atomic_json(path,{'control':'accepted fixture'})
        with self.state.db:self.state.db.execute("INSERT INTO reviews(job_id,path,sha256,inputs_hash,scope,state) VALUES (?,?,?,?,?,'accepted')",(job,str(path),file_hash(path),'a'*64,'control'))

    def commit(self,name,text='owner teaching content\n',push=True):
        (self.repo/name).write_text(text);self.git('add','.');self.git('commit','-m','Owner change')
        if push:self.git('push','origin','HEAD:main')
        return self.git('rev-parse','HEAD')

    def test_N1401_standalone_dirty_learner_keeps_all_jobs_and_other_proceeds(self):
        other=self.root/'other';subprocess.run(['git','clone',str(self.remote),str(other)],check=True,capture_output=True)
        subprocess.run(['git','-C',str(other),'checkout','main'],check=True,capture_output=True)
        self.config['learners']['other']=dict(self.config['learners']['student'],repo=str(other),inputs=[])
        with self.state.db:self.state.db.execute("INSERT INTO observations SELECT 'baseline:other','other',kind,state,manifest,observed_sha,ack_sha,created FROM observations WHERE id='baseline:student'")
        self.state.meta('drive-baseline:other','complete')
        ids=[]
        for status in ('queued','running','retry_wait'):
            job=self.state.enqueue('ingest','student','preserve-'+status,{'retry_at':0});self.state.update_job(job,status);ids.append(job)
        effect=self.state.effect(ids[1],'controlled','test','a'*64,'excluded-effect');self.state.effect_state(effect['stable_key'],'inflight')
        with self.state.db:self.state.db.execute("INSERT INTO attempts(job_id,number,phase,model,effort,state,started) VALUES (?,1,'candidate','gpt-6.1-sol','high','running','controlled')",(ids[1],))
        before=[self.state.job(i) for i in ids];attempt=self.state.rows('SELECT * FROM attempts')[0];effect_before=self.state.rows('SELECT * FROM effects')[0]
        healthy=self.state.enqueue('controlled','other','healthy',{})
        (self.repo/'wiki/math/owner.md').write_text('owner dirty bytes')
        def process(supervisor,job_id):supervisor.state.update_job(job_id,'complete','done')
        with patch('school_notes.cli.load',return_value=self.config),patch.object(Supervisor,'process',process),patch('school_notes.cli.DriveAPI',return_value=f.FakeDrive()),patch('sys.stdout',io.StringIO()),patch('sys.stderr',io.StringIO()):code=cli.main(['--config',str(self.root/'synthetic-config'),'run-once'])
        self.assertEqual(0,code);self.assertEqual('complete',self.state.job(healthy)['state']);self.assertEqual(before,[self.state.job(i) for i in ids]);self.assertEqual(attempt,self.state.rows('SELECT * FROM attempts')[0]);self.assertEqual(effect_before,self.state.rows('SELECT * FROM effects')[0]);self.assertEqual('owner dirty bytes',(self.repo/'wiki/math/owner.md').read_text());self.assertTrue(self.state.rows("SELECT id FROM jobs WHERE learner='student' AND kind='runtime_block' AND state='blocked'"))

    def test_N1401_clean_behind_checkout_fast_forwards_and_processes(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');other=self.root/'owner-other'
        subprocess.run(['git','clone','--branch','main',str(self.remote),str(other)],check=True,capture_output=True)
        for key,value in (('user.name','Owner'),('user.email','owner@example.test')):subprocess.run(['git','-C',str(other),'config',key,value],check=True,capture_output=True)
        (other/'wiki/math/human.md').write_text('human ahead');subprocess.run(['git','-C',str(other),'add','.'],check=True,capture_output=True);subprocess.run(['git','-C',str(other),'commit','-m','Owner push'],check=True,capture_output=True);subprocess.run(['git','-C',str(other),'push','origin','HEAD:main'],check=True,capture_output=True)
        self.git('fetch','origin','main');head=self.git('rev-parse','origin/main');self.assertEqual(old,self.git('rev-parse','HEAD'));self.drive.items={'ready':self.drive.items['ready']};controlled=self.state.enqueue('controlled','student','clean-behind',{})
        supervisor.process=lambda job_id:self.state.update_job(job_id,'complete','done')
        supervisor.run_once();self.assertEqual(head,self.git('rev-parse','HEAD'));self.assertEqual('complete',self.state.job(controlled)['state']);self.assertFalse(self.state.rows("SELECT id FROM jobs WHERE kind='runtime_block' AND state='blocked'"))

    def test_N1402_provisional_and_ready_new_range_preserve_accepted_job(self):
        git=Git(self.repo);base=git.head();head=self.commit('wiki/math/b.md');first=register_external(self.state,git,'student',base,head);self.accepted(first);self.state.update_job(first,'review_wait','external_review');before=self.state.job(first)
        newer=self.commit('wiki/math/c.md',push=False)
        for ready in (False,True):
            register_external(self.state,git,'student',base,newer,ready=ready);self.assertEqual(before,self.state.job(first))
        self.git('reset','--hard',head);self.assertEqual(first,register_external(self.state,git,'student',base,head));self.assertEqual(before,self.state.job(first))

    def maintenance_evidence(self,job):
        path='publication/pilot.json'
        return {'job_id':job['id'],'base':job['payload']['base'],'head':job['payload']['head'],'changes':job['payload']['changes'],'manifest_impact':{'path':path,'sha256':file_hash(self.repo/path),'manifest':json.loads((self.repo/path).read_text())},'open_reviews':[],'open_questions':[],'reason':'Exact direct-owner maintenance/retraction closure','closure_records':self.evidence_records(),**({'merge_base':job['payload']['merge_base']} if 'merge_base' in job['payload'] else {})}

    def test_N1403_divergence_observer_only_exact_manual_closure(self):
        supervisor=self.supervisor();common=self.git('rev-parse','HEAD');old=self.commit('wiki/math/retracted.md')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(old,old))
        self.git('checkout','-b','retracted-history',common);new=self.commit('wiki/math/replacement.md',push=False);self.git('push','--force','origin','HEAD:main')
        supervisor.observe_git('student');rows=self.state.rows("SELECT id FROM jobs WHERE kind='divergence_maintenance'");self.assertEqual(1,len(rows));job=self.state.job(rows[0]['id']);self.assertEqual(common,job['payload']['merge_base']);self.assertEqual(None,job['payload']['changes']['wiki/math/retracted.md']);self.assertEqual(new,job['payload']['head'])
        self.state.update_job(job['id'],'queued')
        with patch.object(supervisor,'external_review',side_effect=AssertionError('divergence must not enter LLM')),patch.object(supervisor.agents,'call',side_effect=AssertionError('no model')):supervisor.run_once()
        self.assertNotEqual('complete',self.state.job(job['id'])['state'])
        evidence=self.maintenance_evidence(job);bad=copy.deepcopy(evidence);bad['merge_base']='0'*40
        with self.assertRaises(Blocked):admin.acknowledge_maintenance(supervisor,job['id'],bad)
        admin.acknowledge_maintenance(supervisor,job['id'],evidence);self.assertEqual(new,self.state.rows("SELECT ack_sha FROM observations WHERE id='baseline:student'")[0]['ack_sha']);self.assertEqual('complete',self.state.job(job['id'])['state']);self.assertFalse(self.state.rows('SELECT * FROM attempts'))
        with self.assertRaisesRegex(Blocked,'diverged'):register_external(self.state,Git(self.repo),'student',old,new)

    def test_N1404_symlink_maintenance_uses_committed_tree_none(self):
        supervisor=self.supervisor();base=self.git('rev-parse','HEAD');(self.repo/'wiki/math/owner-link.md').symlink_to('index.md');self.git('add','.');self.git('commit','-m','Owner symlink');self.git('push','origin','HEAD:main');supervisor.observe_git('student')
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")[0]['id']);self.assertIsNone(job['payload']['changes']['wiki/math/owner-link.md']);self.assertEqual(base,job['payload']['base']);admin.acknowledge_maintenance(supervisor,job['id'],self.maintenance_evidence(job));self.assertEqual('complete',self.state.job(job['id'])['state'])

    def test_N1405_finalizer_refuses_closed_superseded_rejected_before_git(self):
        supervisor=self.supervisor();job=self.state.enqueue('external_change_review','student','closed',{'base':'a'*40,'head':'b'*40});self.accepted(job)
        for status in ('closed_unprocessed','superseded','rejected','complete'):
            self.state.update_job(job,status);before=self.state.job(job)
            with patch('school_notes.cli.Git',side_effect=AssertionError('terminal state must fail before Git')):
                with self.assertRaisesRegex(Blocked,'state|finaliz'):cli.finalize_external(supervisor,job)
            self.assertEqual(before,self.state.job(job))
        self.assertFalse(self.state.rows('SELECT * FROM effects'))

    def test_N1407_drive_success_retains_git_block_and_clears_only_drive(self):
        supervisor=self.supervisor();(self.repo/'wiki/math/dirty.md').write_text('owner edit');self.drive.items={'ready':self.drive.items['ready']}
        supervisor.sync(['student']);blocks=self.state.rows("SELECT * FROM jobs WHERE kind='runtime_block' AND state='blocked'");self.assertTrue(blocks);self.assertEqual({'git'},{json.loads(row['payload'])['category'] for row in blocks})
        supervisor.record_runtime_block('student','controlled Drive failed',category='drive');supervisor.observe_drive('student');self.assertTrue(self.state.rows("SELECT id FROM jobs WHERE kind='runtime_block' AND state='blocked'"));drive=[row for row in self.state.rows("SELECT * FROM jobs WHERE kind='runtime_block'") if json.loads(row['payload']).get('category')=='drive'];self.assertEqual(['complete'],[row['state'] for row in drive]);self.assertEqual('owner edit',(self.repo/'wiki/math/dirty.md').read_text())

    def test_N1408_absolute_deadline_cleans_delayed_guardian_sigterm_ignoring_worker(self):
        pidfile=self.root/'slow-worker.json';shim=self.root/'delayed-guardian.py';shim.write_text("import os,sys,time;time.sleep(3.08);os.execv(sys.executable,[sys.executable,*sys.argv[1:]])")
        worker="import os,signal,time,json;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path("+repr(str(pidfile))+").write_text(json.dumps({'pid':os.getpid()}));time.sleep(30)"
        real_popen=subprocess.Popen;children=[]
        def delayed(argv,*args,**kwargs):
            if len(argv)>1 and str(argv[1]).endswith('_process_guard.py'):argv=[argv[0],str(shim),*argv[1:]]
            process=real_popen(argv,*args,**kwargs);children.append(process);return process
        try:
            with RunLock(self.config['lock_file']) as lock,patch('school_notes.common.subprocess.Popen',side_effect=delayed):
                with self.assertRaises(TimedOut):run([sys.executable,'-c',worker],self.root,timeout=.15,lock=lock)
            if pidfile.exists():
                pid=json.loads(pidfile.read_text())['pid'];actual=session.process_identity(pid);self.assertTrue(actual is None or actual['state']=='Z','worker survived parent timeout')
            with RunLock(self.config['lock_file']):pass
        finally:
            if pidfile.exists():
                pid=json.loads(pidfile.read_text())['pid']
                try:os.killpg(pid,signal.SIGKILL)
                except ProcessLookupError:pass
            for process in children:
                if process.poll() is None:process.kill();process.wait()

    def test_N1409_outer_deep_result_blocks_attempt_and_other_job_proceeds(self):
        supervisor=self.supervisor();config=json.loads((f.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable;agent=Agent(config,self.state,supervisor.lock,Window());proof=self.root/'synthetic-only.json';atomic_json(proof,{'synthetic_transport_only':True});settings=agent.role_settings('codex');settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}']);seen=[]
        class Deep(f.FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                if phase!='candidate':return super().call(job,phase,envelope,cwd,directory,instructions)
                def provider(argv,*args,**kwargs):
                    Path(str(kwargs['log'])+'.stderr').write_text('')
                    attempt=Path(argv[-1]).parent;path=attempt/'result.json';path.write_text('{"uncertainties":'+('['*200000)+'0'+(']'*200000)+'}');Path(kwargs['log']).write_text('{"type":"turn.completed"}\n');seen.append(path)
                with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):return agent.call(job,phase,envelope,cwd,directory,instructions)
        supervisor.agents=Deep(self.state,supervisor.lock)
        supervisor.observe_drive('student')
        other=self.state.enqueue('controlled','student','following-job',{});original=supervisor.process
        def process(job_id):
            if job_id==other:supervisor.state.update_job(job_id,'complete','done')
            else:original(job_id)
        supervisor.process=process
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('nesting',job['error']);self.assertNotIn('invalid_manifest_attempt',job['payload']);self.assertEqual('complete',self.state.job(other)['state']);attempt=self.state.rows('SELECT * FROM attempts')[0];self.assertEqual('failed',attempt['state']);self.assertEqual(file_hash(seen[0]),attempt['result_hash']);self.assertFalse(any(c.startswith('source_review') for c in supervisor.agents.calls))

    def test_N1412_controller_guidance_disables_bytecode_and_network_dependency_resolution(self):
        self.config['interactive_command']=[sys.executable,'/tmp/synthetic-unavailable.py'];capture=self.root/'argv.json';launcher=self.root/'launcher.py';launcher.write_text('import sys,json;from pathlib import Path;Path('+repr(str(capture))+').write_text(json.dumps(sys.argv))');self.config['interactive_command']=[sys.executable,str(launcher)]
        receipt=session.wrapper(self.config,'student',[],config_path=self.root/'config.json');self.assertIn('UV_OFFLINE=1',receipt['controller_command']);self.assertIn(' -B ',receipt['controller_command']);self.assertIn('UV_OFFLINE=1',json.loads(capture.read_text())[-1])

class PublicR14Tests(f.Base):
    setUp=f.PilotTests.setUp
    public_setup=r1.PublicR1Tests.public_setup
    run_public=r1.PublicR1Tests.run_public

    def test_N1406_public_last_prewrite_rejects_local_unpushed_commit(self):
        supervisor,private,public,api=self.public_setup();self.run_public(supervisor,api);proposal=self.state.job(public)['payload']['public_proposal'];self.state.approve(public,digest(proposal));original=self.state.effect;injected=[];remote=self.git('rev-parse','origin/main')
        def effect(*args,**kwargs):
            retained=original(*args,**kwargs)
            if retained['stable_key'].startswith('public-manifest-push:') and not injected:
                (self.repo/'wiki/math/owner.md').write_text('late owner commit');self.git('add','.');self.git('commit','-m','Owner concurrent commit');injected.append(True)
            return retained
        with patch.object(self.state,'effect',side_effect=effect):self.run_public(supervisor,api)
        job=self.state.job(public);self.assertEqual('blocked',job['state']);self.assertIn('unpushed',job['error']);self.assertEqual(remote,self.git('rev-parse','origin/main'));self.assertEqual(remote,self.git('ls-remote','origin','refs/heads/main').split()[0]);effect=self.state.rows("SELECT * FROM effects WHERE stable_key LIKE 'public-manifest-push:%'")[0];self.assertEqual('planned',effect['state']);self.assertFalse(api.requests)

class TransportR14Tests(f.Base):
    def test_N1409_deep_codex_event_and_claude_wrapper_are_failed_bounded_attempts(self):
        with RunLock(self.root/'run.lock') as lock:
            worker=self.root/'transport-worker';worker.mkdir(mode=0o700)
            config=json.loads((f.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable;agent=Agent(config,self.state,lock,Window());proof=self.root/'synthetic-proof.json';atomic_json(proof,{'synthetic_only':True})
            for role,phase in (('codex','candidate'),('claude','review')):
                with self.subTest(role=role):
                    job_id=self.state.enqueue('controlled','student','deep-'+role,{});job=self.state.job(job_id);envelope={'job_id':job_id,'revision_seq':None,'inputs':[]};settings=agent.role_settings(role);settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}']);paths=[]
                    def provider(argv,*args,**kwargs):
                        Path(str(kwargs['log'])+'.stderr').write_text('')
                        path=Path(kwargs['log']);path.write_text('{"uncertainties":'+('['*200000)+'0'+(']'*200000)+'}');paths.append(path)
                    with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):
                        with self.assertRaisesRegex(Blocked,'nesting'):agent.call(job,phase,envelope,worker,self.root/'jobs','synthetic outer transport')
                    self.assertTrue(paths[0].is_file());self.assertEqual('failed',self.state.rows('SELECT state FROM attempts WHERE job_id=?',(job_id,))[0]['state']);self.assertNotIn('invalid_manifest_attempt',self.state.job(job_id)['payload'])

    def test_N1408_parent_timeout_signals_guardian_and_waits_cleanup_reserve(self):
        class Guardian:
            pid=123456789
            def __init__(inner):inner.code=None;inner.waits=[];inner.terminated=False
            def poll(inner):return inner.code
            def terminate(inner):inner.terminated=True
            def wait(inner,timeout=None):
                if inner.code is not None:return inner.code
                inner.waits.append(timeout)
                if len(inner.waits)==1:raise subprocess.TimeoutExpired('controlled',timeout)
                self.assertTrue(inner.terminated);self.assertGreaterEqual(timeout,3);inner.code=124;return 124
        guardian=Guardian()
        with patch('school_notes.common.subprocess.Popen',return_value=guardian),patch('school_notes.common.terminate_group',side_effect=AssertionError('must allow guardian cleanup before kill')):
            with self.assertRaises(TimedOut):run([sys.executable,'-c','pass'],self.root,timeout=1)
        self.assertEqual(4,guardian.waits[1])
