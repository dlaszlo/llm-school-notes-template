"""R15 typed classification and precise owner/recovery diagnostics."""
import copy,json,subprocess,sys
from pathlib import Path
from unittest.mock import patch
import test_app as f
import test_review_r2 as r2
import test_review_r3 as r3
from school_notes import admin,cli
from school_notes.agents import Agent,validate_result
from school_notes.common import Blocked,Busy,Window,atomic_json,digest,file_hash
from school_notes.verify import Git

class R15Tests(f.Base):
    setUp=f.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def test_N1505_actual_classify_call_malformed_id_failed_receipt_and_later_job(self):
        supervisor=self.supervisor();config=json.loads((f.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable;agent=Agent(config,self.state,supervisor.lock,Window());proof=self.root/'synthetic-only.json';atomic_json(proof,{'synthetic_transport_only':True});settings=agent.role_settings('codex');settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}']);results=[]
        class BadIdentity(f.FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                if phase!='classify':return super().call(job,phase,envelope,cwd,directory,instructions)
                def provider(argv,*args,**kwargs):
                    Path(str(kwargs['log'])+'.stderr').write_text('')
                    response,_=super(BadIdentity,inner).call(job,phase,envelope,cwd,directory,instructions);response['classification'][0]['id']=[];attempt=Path(argv[-1]).parent;path=attempt/'result.json';atomic_json(path,response);Path(kwargs['log']).write_text('{"type":"turn.completed"}\n');results.append(path)
                with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',provider):return agent.call(job,phase,envelope,cwd,directory,instructions)
        supervisor.agents=BadIdentity(self.state,supervisor.lock);supervisor.observe_drive('student');ingest=self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'];later=self.state.enqueue('controlled','student','later-controlled',{});original=supervisor.process
        def process(job_id):
            if job_id==later:self.state.update_job(job_id,'complete','done')
            else:original(job_id)
        supervisor.process=process
        with patch('school_notes.pipeline.Renderer',f.FakeRenderer):supervisor.run_once()
        job=self.state.job(ingest);self.assertEqual('blocked',job['state']);self.assertEqual('classify',job['phase']);self.assertIn('classification',job['error']);self.assertNotIn('invalid_manifest_attempt',job['payload']);attempt=self.state.rows('SELECT * FROM attempts WHERE job_id=?',(ingest,))[0];self.assertEqual('failed',attempt['state']);self.assertEqual(file_hash(results[0]),attempt['result_hash']);self.assertEqual([],json.loads(results[0].read_text())['classification'][0]['id']);self.assertEqual('complete',self.state.job(later)['state']);self.assertFalse(self.state.rows('SELECT * FROM effects'));self.assertFalse(job['payload'].get('worktree'));self.assertEqual([],self.drive.writes)

    def test_N1505_identity_and_sha_types_are_rejected_before_hash_lookup(self):
        envelope={'job_id':1,'revision_seq':None,'inputs':[]};good=f.result(envelope);good['classification']=[{'id':'source-id','sha256':'a'*64,'source_class':'notebook','uncertain':False}];self.assertEqual('complete',validate_result(copy.deepcopy(good),envelope)['status'])
        for key,value in [('id',[]),('id',{}),('id',1),('sha256',[]),('sha256',{}),('sha256',1),('sha256','a'*63),('sha256','g'*64),('sha256','A'*64)]:
            with self.subTest(key=key,value=value):
                bad=copy.deepcopy(good);bad['classification'][0][key]=value
                with self.assertRaisesRegex(Blocked,'classification'):validate_result(bad,envelope)

    def remote_clone(self):
        clone=self.root/'remote-owner';subprocess.run(['git','clone','--branch','main',str(self.remote),str(clone)],check=True,capture_output=True)
        for key,value in [('user.name','Owner'),('user.email','owner@example.test')]:subprocess.run(['git','-C',str(clone),'config',key,value],check=True,capture_output=True)
        return clone

    def other_git(self,clone,*args):return subprocess.check_output(['git','-C',str(clone),*args],text=True).strip()

    def test_N1507_joined_behind_diagnostic_no_gate_or_checkout_change(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');clone=self.remote_clone();(clone/'wiki/math/remote.md').write_text('remote ahead');self.other_git(clone,'add','.');self.other_git(clone,'commit','-m','Remote ahead');self.other_git(clone,'push','origin','HEAD:main');self.git('fetch','origin','main')
        with self.assertRaisesRegex(Busy,'behind'):supervisor.preflight_owner(['student'])
        self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertFalse(self.state.rows('SELECT * FROM jobs'));supervisor.preflight_owner(['student'],allow_behind=True);self.assertEqual(old,self.git('rev-parse','HEAD'))

    def test_N1502_diverged_possible_remote_rewrite_diagnostic_preserves_checkout(self):
        supervisor=self.supervisor();base=self.git('rev-parse','HEAD');(self.repo/'wiki/math/old.md').write_text('old acknowledged');self.git('add','.');self.git('commit','-m','Old branch');self.git('push','origin','HEAD:main');old=self.git('rev-parse','HEAD');clone=self.remote_clone();self.other_git(clone,'checkout','-b','rewritten',base);(clone/'wiki/math/new.md').write_text('new branch');self.other_git(clone,'add','.');self.other_git(clone,'commit','-m','Owner rewrite');self.other_git(clone,'push','--force','origin','HEAD:main');self.git('fetch','origin','main')
        for operation in (lambda:supervisor.preflight_owner(['student']),lambda:Git(self.repo,supervisor.lock).inspect(fetch=False)):
            with self.assertRaisesRegex(Blocked,'diverged.*rewrite'):operation()
            self.assertEqual(old,self.git('rev-parse','HEAD'));self.assertEqual('old acknowledged',(self.repo/'wiki/math/old.md').read_text())
        self.assertFalse(self.state.rows('SELECT * FROM jobs'))

    def test_N1502_local_ahead_diagnostic_keeps_unpushed_bytes(self):
        supervisor=self.supervisor();remote=self.git('rev-parse','origin/main');(self.repo/'wiki/math/local.md').write_text('owner local');self.git('add','.');self.git('commit','-m','Owner local');head=self.git('rev-parse','HEAD')
        with self.assertRaisesRegex(Busy,'local ahead'):supervisor.preflight_owner(['student'])
        self.assertEqual(head,self.git('rev-parse','HEAD'));self.assertEqual(remote,self.git('ls-remote','origin','refs/heads/main').split()[0]);self.assertFalse(self.state.rows('SELECT * FROM jobs'))

    def test_N1504_obsolete_accepted_range_error_names_exact_close_route(self):
        supervisor=self.supervisor();first,_=r3.R3Tests.external_job(self,supervisor);before_reviews=self.state.rows('SELECT * FROM reviews WHERE job_id=?',(first,));(self.repo/'wiki/math/newer.md').write_text('newer owner content');self.git('add','.');self.git('commit','-m','Newer owner range');self.git('push','origin','HEAD:main');supervisor.observe_git('student');new=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review' AND id!=?",(first,))[0]['id']);path='publication/pilot.json';evidence={'job_id':new['id'],'base':new['payload']['base'],'head':new['payload']['head'],'changes':new['payload']['changes'],'manifest_impact':{'path':path,'sha256':file_hash(self.repo/path),'manifest':json.loads((self.repo/path).read_text())},'open_reviews':[],'open_questions':[],'reason':'Owner assessed exact later range','closure_records':self.evidence_records()};admin.acknowledge_maintenance(supervisor,new['id'],evidence)
        with self.assertRaisesRegex(Blocked,'close-job'):cli.finalize_external(supervisor,first)
        job=self.state.job(first);self.assertEqual('review_wait',job['state']);closure={'job_id':first,'revision_seq':job['revision_seq'],'base':job['payload']['base'],'payload_sha256':digest(job['payload']),'reason':'Exact obsolete retained range assessed by owner; no fresh acceptance claimed','closure_records':self.evidence_records()};admin.close_job(supervisor,first,closure);self.assertEqual('closed_unprocessed',self.state.job(first)['state']);self.assertEqual(before_reviews,self.state.rows('SELECT * FROM reviews WHERE job_id=?',(first,)));self.assertFalse(self.state.rows('SELECT * FROM effects WHERE job_id=?',(first,)))
