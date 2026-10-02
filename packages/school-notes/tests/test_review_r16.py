"""R16 narrow transport and protected-session regressions; synthetic providers only."""
import copy,json,os,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import test_app as f
import test_interactive as interactive
import test_review_r15 as r15
from school_notes.agents import Agent
from school_notes.common import Blocked,Window,atomic_json,file_hash

class R16Tests(f.Base):
    setUp=r15.R15Tests.setUp
    supervisor=r15.R15Tests.supervisor
    remote_clone=r15.R15Tests.remote_clone
    other_git=r15.R15Tests.other_git
    # Borrow helpers, not the parent test methods in this suite.
    def remote_ahead(self):
        clone=self.remote_clone();(clone/'wiki/math/remote.md').write_text('remote owner change');self.other_git(clone,'add','.');self.other_git(clone,'commit','-m','Remote owner change');self.other_git(clone,'push','origin','HEAD:main');return self.other_git(clone,'rev-parse','HEAD')

    def test_N1601_joined_actual_observe_refuses_remote_change_after_preflight(self):
        supervisor=self.supervisor();supervisor.actor_origin='owner-session';old=self.git('rev-parse','HEAD');supervisor.preflight_owner(['student']);new=self.remote_ahead()
        with self.assertRaisesRegex(Blocked,'behind'):supervisor.observe_git('student')
        self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertEqual(new,self.git('rev-parse','origin/main'));self.assertFalse(self.state.rows('SELECT * FROM jobs'))
        # The scheduler still supports its existing clean-behind fast-forward.
        supervisor.actor_origin='direct-vm-admin';supervisor.observe_git('student');self.assertEqual(new,self.git('rev-parse','HEAD'))

    def test_N1602_actual_calls_nonobject_events_retained_failed_attempts(self):
        supervisor=self.supervisor();config=json.loads((f.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable;agent=Agent(config,self.state,supervisor.lock,Window());proof=self.root/'synthetic-only.json';atomic_json(proof,{'synthetic_transport_only':True})
        job_id=self.state.enqueue('controlled','student','nonobject',{});job=self.state.job(job_id)
        for phase,role in [('classify','codex'),('review:0','claude')]:
            for number,value in enumerate([[],None,1,'text']):
                with self.subTest(phase=phase,value=value):
                    settings=agent.role_settings(role);settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}']);directory=self.root/('call-'+role+'-'+str(number));envelope={'job_id':job_id,'revision_seq':None,'inputs':[],'attempt_phase':phase.split(':')[0]+':'+format(number,'016x')}
                    def provider(argv,*args,**kwargs):
                        Path(str(kwargs['log'])+'.stderr').write_text('')
                        attempt=Path(argv[-1]).parent;atomic_json(attempt/'result.json',f.result(envelope));Path(kwargs['log']).write_text(json.dumps(value)+'\n')
                    with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):
                        with self.assertRaisesRegex(Blocked,'object'):agent.call(job,phase,envelope,self.repo,directory,'bounded synthetic transport')
                    attempt=self.state.rows('SELECT * FROM attempts WHERE job_id=? ORDER BY id DESC LIMIT 1',(job_id,))[0];self.assertEqual('failed',attempt['state']);results=list(directory.rglob('result.json'));self.assertEqual(1,len(results));self.assertEqual(file_hash(results[0]),attempt['result_hash']);self.assertNotIn('invalid_manifest_attempt',self.state.job(job_id)['payload'])

    def test_N1602_nonobject_event_blocks_job_and_later_job_completes(self):
        supervisor=self.supervisor();config=json.loads((f.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable;agent=Agent(config,self.state,supervisor.lock,Window());proof=self.root/'synthetic-only.json';atomic_json(proof,{'synthetic_transport_only':True});settings=agent.role_settings('codex');settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}']);results=[]
        class BadIdentity(f.FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                if phase!='classify':return super().call(job,phase,envelope,cwd,directory,instructions)
                def provider(argv,*args,**kwargs):
                    Path(str(kwargs['log'])+'.stderr').write_text('')
                    response,_=super(BadIdentity,inner).call(job,phase,envelope,cwd,directory,instructions);attempt=Path(argv[-1]).parent;path=attempt/'result.json';atomic_json(path,response);Path(kwargs['log']).write_text('[]\n');results.append(path)
                with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):return agent.call(job,phase,envelope,cwd,directory,instructions)
        supervisor.agents=BadIdentity(self.state,supervisor.lock);supervisor.observe_drive('student');ingest=self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'];later=self.state.enqueue('controlled','student','later-controlled',{});original=supervisor.process
        def process(job_id):
            if job_id==later:self.state.update_job(job_id,'complete','done')
            else:original(job_id)
        supervisor.process=process
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        job=self.state.job(ingest);self.assertEqual('blocked',job['state']);self.assertEqual('classify',job['phase']);self.assertIn('object',job['error']);self.assertNotIn('invalid_manifest_attempt',job['payload']);attempt=self.state.rows('SELECT * FROM attempts WHERE job_id=?',(ingest,))[0];self.assertEqual('failed',attempt['state']);self.assertEqual(file_hash(results[0]),attempt['result_hash']);self.assertEqual('[]\n',Path(json.loads((results[0].parent/'transport.json').read_text())['stdout']['path']).read_text());self.assertEqual('complete',self.state.job(later)['state']);self.assertFalse(self.state.rows('SELECT * FROM effects'));self.assertFalse(job['payload'].get('worktree'));self.assertEqual([],self.drive.writes)

class R16ProcessTests(f.Base):
    setUp=interactive.InteractiveTests.setUp
    config_file=interactive.InteractiveTests.config_file
    owner=interactive.InteractiveTests.owner
    def test_N1601_stale_remote_real_joined_command_keeps_checkout(self):
        old=self.git('rev-parse','HEAD');r15.R15Tests.remote_clone(self)
        clone=self.root/'remote-owner';(clone/'wiki/math/remote.md').write_text('remote bytes')
        for args in [('add','.'),('commit','-m','Remote owner'),('push','origin','HEAD:main')]:r15.R15Tests.other_git(self,clone,*args)
        # Deliberately leave origin/main stale in the protected owner checkout.
        self.assertEqual(old,self.git('rev-parse','origin/main'));cfg=self.config_file();output=self.root/'joined-output.json'
        program=f"import subprocess,sys,json;from pathlib import Path;p=subprocess.run([sys.executable,'-m','school_notes','--config',{str(cfg)!r},'run-once'],capture_output=True,text=True);Path({str(output)!r}).write_text(json.dumps({{'code':p.returncode,'err':p.stderr}}))"
        process=self.owner(program);_,err=process.communicate(timeout=15);self.assertEqual(0,process.returncode,err);value=json.loads(output.read_text());self.assertEqual(75,value['code'],value);self.assertIn('behind',value['err']);self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertFalse(self.state.rows('SELECT * FROM attempts'))

    def test_N1603_real_joined_recover_preserves_other_and_null_effects(self):
        jobs={}
        for learner in ['student','other']:
            job=self.state.enqueue('controlled',learner,'recover-'+learner,{});jobs[learner]=job;self.state.update_job(job,'running')
            with self.state.db:self.state.db.execute("INSERT INTO attempts(job_id,number,phase,model,effort,state,started) VALUES(?,1,'controlled','synthetic','high','running','retained')",(job,))
            effect=self.state.effect(job,'upload','target','a'*64,'recover-effect-'+learner);self.state.effect_state(effect['stable_key'],'inflight')
        effect=self.state.effect(None,'upload','status','b'*64,'global-status');self.state.effect_state(effect['stable_key'],'inflight');other_job=self.state.job(jobs['other']);other_attempt=self.state.rows('SELECT * FROM attempts WHERE job_id=?',(jobs['other'],));other_effect=self.state.rows("SELECT * FROM effects WHERE stable_key='recover-effect-other'");null_effect=self.state.rows("SELECT * FROM effects WHERE stable_key='global-status'");cfg=self.config_file();out=self.root/'recover-result.json'
        program=f"import subprocess,sys,json;from pathlib import Path;p=subprocess.run([sys.executable,'-m','school_notes','--config',{str(cfg)!r},'recover'],capture_output=True,text=True);Path({str(out)!r}).write_text(json.dumps({{'code':p.returncode,'err':p.stderr}}))"
        process=self.owner(program);_,err=process.communicate(timeout=15);self.assertEqual(0,process.returncode,err);self.assertEqual(0,json.loads(out.read_text())['code']);self.assertEqual('queued',self.state.job(jobs['student'])['state']);self.assertEqual('interrupted',self.state.rows('SELECT state FROM attempts WHERE job_id=?',(jobs['student'],))[0]['state']);self.assertEqual('unknown',self.state.rows("SELECT state FROM effects WHERE stable_key='recover-effect-student'")[0]['state']);self.assertEqual(other_job,self.state.job(jobs['other']));self.assertEqual(other_attempt,self.state.rows('SELECT * FROM attempts WHERE job_id=?',(jobs['other'],)));self.assertEqual(other_effect,self.state.rows("SELECT * FROM effects WHERE stable_key='recover-effect-other'"));self.assertEqual(null_effect,self.state.rows("SELECT * FROM effects WHERE stable_key='global-status'"))
