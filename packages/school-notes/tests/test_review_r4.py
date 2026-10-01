"""R4 pre-write recovery and whole-context gates; local services only."""
import copy,json,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
import test_app as fixture
import test_review_r1 as r1
import test_review_r2 as r2
import test_review_r3 as r3
from school_notes import admin
from school_notes.common import Blocked,WindowExhausted,atomic_json,digest,file_hash
from school_notes.pipeline import Supervisor
from school_notes.verify import Git

class R4Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def pause_committed(self):
        supervisor=self.supervisor();original=supervisor.push
        supervisor.push=lambda job:(_ for _ in ()).throw(WindowExhausted('synthetic boundary after local commit'))
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('push',job['phase']);self.assertTrue(self.state.rows("SELECT * FROM effects WHERE kind='git-commit' AND state='verified'"));supervisor.push=original
        return supervisor,job

    def test_N401_prewrite_ack_failure_stays_planned_and_local_commit_can_rebase(self):
        supervisor,job=self.pause_committed();old=Path(job['payload']['worktree']);commit=job['payload']['commit']
        (self.repo/'wiki/math/human.md').write_text('# Human change\n');self.git('add','.');self.git('commit','-m','Owner change');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        supervisor.observe_git('student');external=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")[0]['id']);manifest=json.loads((self.repo/'publication/pilot.json').read_text())
        evidence={'job_id':external['id'],'base':external['payload']['base'],'head':head,'changes':external['payload']['changes'],'open_reviews':[],'open_questions':[],'reason':'Controlled owner review of exact human change','closure_records':self.evidence_records(),'manifest_impact':{'path':'publication/pilot.json','sha256':file_hash(self.repo/'publication/pilot.json'),'manifest':manifest}}
        admin.acknowledge_maintenance(supervisor,external['id'],evidence)
        with self.assertRaises(Blocked):supervisor.push(self.state.job(job['id']))
        self.assertEqual([],self.state.rows("SELECT * FROM effects WHERE kind='git-push' AND state IN ('unknown','inflight')"))
        admin.rebase_candidate(supervisor,job['id']);current=self.state.job(job['id']);self.assertEqual(commit,current['payload']['candidate_history'][0]['commit']);self.assertTrue(old.is_dir())
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error'])

    def test_N401_last_prewrite_failure_restores_planned_not_unknown(self):
        from school_notes.common import PreconditionFailed
        effect=self.state.effect(None,'git-push','target','a'*40,'never-written')
        def no_write(e):raise PreconditionFailed('ack changed before actual push')
        with self.assertRaises(PreconditionFailed):self.state.perform_effect(effect,no_write,lambda e:None)
        self.assertEqual('planned',self.state.rows('SELECT state FROM effects')[0]['state'])

    def test_N402_external_and_public_chunks_bind_complete_text_context(self):
        supervisor=self.supervisor();self.config['review_chunk_items']=2
        for phase,kind in (('external_review','external-content'),('public_review','public-source')):
            text=self.root/(phase+'.md');text.write_text('complete teaching content');inputs=[{'path':str(text),'sha256':file_hash(text),'kind':kind}]
            for i in range(5):
                image=self.root/(phase+str(i)+'.png');image.write_bytes(b'controlled image'+bytes([i]));inputs.append({'path':str(image),'sha256':file_hash(image),'kind':'source-page'})
            jobid=self.state.enqueue('external_change_review' if phase=='external_review' else 'public_release','student',phase,{});seen=[]
            class Checking(fixture.FakeAgents):
                def call(inner,job,call_phase,envelope,*args,**kwargs):
                    seen.append(envelope);self.assertEqual([inputs[0]],envelope['comparison_context']);return super().call(job,call_phase,envelope,*args,**kwargs)
            supervisor.agents=Checking(self.state,supervisor.lock)
            supervisor.bounded_review(self.state.job(jobid),phase,inputs,'all content',require_visual=False)
            self.assertEqual(3,len(seen));self.assertTrue(all(e['comparison_context_hash'] for e in seen))

    def test_N403_verified_ingest_push_finishes_after_common_config_change(self):
        supervisor=self.supervisor();original=supervisor.push
        def verified_then_stop(job):original(job);self.state.update_job(job['id'],phase='push');raise WindowExhausted('synthetic postverified stop')
        supervisor.push=verified_then_stop
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.git('config','owner.review','changed-after-verified-push');supervisor.push=original
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error'])

    def test_N404_quota_gate_blocks_rescheduled_job_before_agent_or_renderer(self):
        supervisor=self.supervisor();supervisor.observe_drive('student');jobid=self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'];job=self.state.job(jobid);job['payload']['quota_block']=True;self.state.update_job(jobid,'queued',payload=job['payload'])
        with patch('school_notes.pipeline.Renderer',side_effect=AssertionError('quota renderer')):supervisor.process(jobid)
        self.assertEqual('retry_wait',self.state.job(jobid)['state']);self.assertEqual([],supervisor.agents.calls);self.assertTrue(self.state.job(jobid)['payload']['quota_block'])

    def test_N405_unsupported_middle_file_does_not_allocate_repeated_staging(self):
        supervisor=self.supervisor();self.drive.add('heic','package','02.heic',b'unsupported');self.drive.items['heic']['mimeType']='image/heic';self.drive.add('png3','package','03.png',fixture.PNG)
        for _ in range(4):supervisor.observe_drive('student')
        folders=list((self.root/'captures').glob('*'));self.assertEqual([],folders);self.assertEqual([],self.drive.downloads)
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='capture_block'")[0]['id']);self.assertFalse(job['payload'].get('retained_staging'));self.assertIsNone(job['payload']['staging'])

    def test_N408_ignored_generated_wiki_asset_blocks_before_render(self):
        (self.repo/'.gitignore').write_text('wiki/assets/*.png\n');self.git('add','.');self.git('commit','-m','Owner ignore');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        supervisor=self.supervisor()
        class WritesIgnored(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,*args,**kwargs):
                response,path=super().call(job,phase,envelope,cwd,*args,**kwargs)
                if phase=='candidate':target=Path(cwd)/'wiki/assets/hidden.png';target.parent.mkdir(exist_ok=True);target.write_bytes(fixture.PNG)
                return response,path
        supervisor.agents=WritesIgnored(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',side_effect=AssertionError('must block before render')):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('ignored',job['error'])

    def test_N411_base_change_stops_before_source_review(self):
        supervisor=self.supervisor();original=supervisor.candidate
        def ack_changes(job):
            original(job)
            with self.state.db:self.state.db.execute("UPDATE observations SET ack_sha=? WHERE id='baseline:student'",('0'*40,))
        supervisor.candidate=ack_changes
        with patch('school_notes.pipeline.Renderer',side_effect=AssertionError('no stale render')):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('rebase-candidate',job['error']);self.assertFalse(any(p.startswith('source_review') for p in supervisor.agents.calls))

    def test_N401_last_preflight_window_failure_is_planned_and_keeps_exception_type(self):
        effect=self.state.effect(None,'git-push','target','a'*40,'last-preflight');checks=[];writes=[]
        def preflight():
            checks.append(True)
            if len(checks)==2:raise WindowExhausted('window consumed before mutation')
        with self.assertRaises(WindowExhausted):self.state.perform_effect(effect,lambda e:writes.append(e),lambda e:None,preflight)
        self.assertEqual([],writes);self.assertEqual(2,len(checks));self.assertEqual('planned',self.state.rows('SELECT state FROM effects')[0]['state'])

    def test_N401_exact_remote_absence_resolves_unknown_push_without_erasing_receipt(self):
        supervisor,job=self.pause_committed();key='private-push:student:'+job['payload']['commit'];self.state.effect(job['id'],'git-push',str(self.repo)+':main',job['payload']['commit'],key);self.state.effect_state(key,'unknown',{'old':'retained ambiguous transport receipt'})
        admin.resume_effects(supervisor,job['id']);effect=self.state.rows('SELECT * FROM effects WHERE stable_key=?',(key,))[0];receipt=json.loads(effect['receipt'])
        self.assertEqual('planned',effect['state']);self.assertTrue(receipt['reconciliation']['absent']);self.assertEqual(job['payload']['commit'],receipt['reconciliation']['artifact_hash']);self.assertEqual('retained ambiguous transport receipt',receipt['previous_receipt']['old'])

    def test_N404_render_rescheduler_preserves_quota_wait_until_explicit_clear(self):
        supervisor=self.supervisor();supervisor.observe_drive('student');jobid=self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'];job=self.state.job(jobid);job['payload']['quota_block']=True;self.state.update_job(jobid,'retry_wait',payload=job['payload'])
        admin.retry_render(supervisor,jobid,'private');self.assertEqual('retry_wait',self.state.job(jobid)['state'])
        supervisor.process(jobid);self.assertEqual([],supervisor.agents.calls)
        admin.clear_quota(supervisor,jobid,{'job_id':jobid,'revision_seq':1,'reason':'Controlled direct-admin elapsed reset evidence','reset_epoch':0});self.assertEqual('queued',self.state.job(jobid)['state']);self.assertFalse(self.state.job(jobid)['payload']['quota_block'])

    def test_N406_stale_questions_hide_after_current_completion_and_close_retains_answers(self):
        supervisor=self.supervisor();self.state.revision('student','p',self.manifest('A'));old=self.state.rows('SELECT id FROM jobs WHERE package_id=1')[0]['id'];q=self.state.question(old,'content','author','Author?');self.state.answer(q,'classmate','admin-content');self.state.revision('student','p',self.manifest('B'));current=self.state.rows('SELECT id FROM jobs WHERE package_id=1 ORDER BY id DESC')[0]['id']
        self.assertTrue(any(row['id']==q for row in supervisor.status()['questions']));self.state.update_job(current,'complete','done');self.assertFalse(any(row['id']==q for row in supervisor.status()['questions']))
        admin.reject_package(supervisor,old,'controlled owner rejection');row=self.state.rows('SELECT * FROM questions WHERE id=?',(q,))[0];self.assertEqual('closed',row['state']);self.assertEqual('classmate',row['answer'])

    def test_N407_filter_rejects_before_writer_or_executable_filter_runs(self):
        (self.repo/'.gitattributes').write_text('sources/** filter=canary\n');self.git('add','.');self.git('commit','-m','Owner attributes');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        marker=self.root/'filter-executed';script=self.root/'filter.py';script.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("executed")\n');self.git('config','filter.canary.clean',sys.executable+' '+str(script))
        supervisor=self.supervisor()
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id']);self.assertEqual('blocked',job['state']);self.assertIn('transforming Git attribute',job['error']);self.assertNotIn('candidate',supervisor.agents.calls);self.assertFalse(marker.exists())

    def test_N407_text_auto_binary_allowed_actual_normalization_blocks_before_commit(self):
        (self.repo/'.gitattributes').write_text('* text=auto eol=lf\n');self.git('add','.');self.git('commit','-m','Shared attributes');git=Git(self.repo)
        binary=self.repo/'sources/ordinary.png';binary.write_bytes(fixture.PNG);git.source_attributes('sources/ordinary.png');git.git('add','--','sources/ordinary.png');git.verify_sources([{'path':str(binary),'sha256':file_hash(binary)}],':index')
        source=self.repo/'sources/textual.pdf';source.write_bytes(b'%PDF-1.4\r\nplain text\r\n');sources=[{'path':str(source),'sha256':file_hash(source)}];base=git.head();git.source_attributes('sources/textual.pdf')
        job={'id':999,'kind':'ingest','revision_seq':1,'payload':{'base':base,'git_sources':sources}}
        from school_notes.verify import OwnerPolicyViolation
        with self.assertRaises(OwnerPolicyViolation):git.changes(base,sources=[{'path':str(p),'sha256':file_hash(p)} for p in (binary,source)])
        changes={str(p.relative_to(self.repo)):file_hash(p) for p in (binary,source)}
        # The stronger candidate gate runs earlier now; bypass only that gate
        # to retain this independent final staged source-blob regression.
        with patch.object(git,'changes',return_value=changes):
            with self.assertRaisesRegex(Blocked,'no commit created; staged'):git.commit(job,changes,[],self.config['git_identity'])
        self.assertEqual(base,git.head())

    def test_N408_manifest_tree_gate_rejects_missing_or_changed_ordinary_blob(self):
        git=Git(self.repo);path=self.repo/json.loads((self.repo/'publication/pilot.json').read_text())['pages'][0]['path'];manifest={'pages':[{'path':str(path.relative_to(self.repo)),'sha256':file_hash(path)}]};git.verify_manifest_tree(manifest)
        path.write_text('uncommitted changed page');manifest['pages'][0]['sha256']=file_hash(path)
        with self.assertRaisesRegex(Blocked,'differs'):git.verify_manifest_tree(manifest)
        asset=self.repo/'wiki/math/missing.svg';asset.write_text('<svg/>');manifest={'pages':[],'assets':[{'path':str(asset.relative_to(self.repo)),'sha256':file_hash(asset)}]}
        with self.assertRaisesRegex(Blocked,'absent'):git.verify_manifest_tree(manifest)

    def test_N409_initial_ack_preserves_newer_observed_external_range(self):
        from school_notes.state import State
        from school_notes.cli import acknowledge_initial_baseline
        initial=self.git('rev-parse','HEAD');state=State.initialize(self.root/'fresh-baseline.sqlite',{'student':{'observed_sha':initial}});self.addCleanup(state.close)
        supervisor=self.supervisor();supervisor.state=state
        (self.repo/'wiki/math/after-init.md').write_text('# Human later\n');self.git('add','.');self.git('commit','-m','After init');self.git('push','origin','HEAD:main');later=self.git('rev-parse','HEAD');supervisor.observe_git('student')
        (self.repo/'wiki/math/second-after-init.md').write_text('# Second human later\n');self.git('add','.');self.git('commit','-m','Second after init');self.git('push','origin','HEAD:main');later=self.git('rev-parse','HEAD');supervisor.observe_git('student')
        evidence=self.root/'baseline-closure.json';atomic_json(evidence,{'observed_sha':initial,'ack_sha':initial,'open_reviews':[],'open_questions':[],'closure_records':self.evidence_records()})
        result=acknowledge_initial_baseline(supervisor,'student',evidence);row=state.rows("SELECT * FROM observations WHERE id='baseline:student'")[0]
        self.assertEqual(initial,result['baseline_ack']);self.assertEqual(initial,row['ack_sha']);self.assertEqual(later,row['observed_sha']);external=state.job(state.rows("SELECT id FROM jobs WHERE kind='external_change_review' ORDER BY id DESC")[0]['id']);self.assertEqual(initial,external['payload']['base']);self.assertEqual(later,external['payload']['head']);self.assertEqual({'wiki/math/after-init.md','wiki/math/second-after-init.md'},set(external['payload']['changes']))
        from school_notes.cli import finalize_external
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.external_review(external)
        finalized=finalize_external(supervisor,external['id']);self.assertEqual(finalized['commit'],state.rows("SELECT ack_sha FROM observations WHERE id='baseline:student'")[0]['ack_sha'])

    def test_N403_external_verified_push_reentry_avoids_old_git_after_config_drift(self):
        from school_notes.cli import finalize_external
        supervisor=self.supervisor();jobid,base=r3.R3Tests.external_job(self,supervisor);completed=finalize_external(supervisor,jobid);self.git('config','owner.review','external-postpush');old=Path(self.state.job(jobid)['payload']['maintenance_git_identity']['repo']);original=Git.git
        def forbid_old(git,*args,**kwargs):
            if git.repo==old:raise AssertionError('old external Git executed after verified push')
            return original(git,*args,**kwargs)
        with patch.object(Git,'git',forbid_old):again=finalize_external(supervisor,jobid)
        self.assertEqual(completed['commit'],again['commit']);self.assertEqual('complete',self.state.job(jobid)['state'])


class R4PublicTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    public_setup=r1.PublicR1Tests.public_setup
    run_public=r1.PublicR1Tests.run_public

    def test_N403_published_job_survives_config_drift_without_old_candidate_git(self):
        supervisor,private,public,api=self.public_setup();self.run_public(supervisor,api);self.state.approve(public,digest(self.state.job(public)['payload']['public_proposal']));api.complete=True;live=api.live_get;api.live_get=lambda url:b'{}' if url.endswith('release.json') else live(url);self.run_public(supervisor,api)
        job=self.state.job(public);self.assertEqual('retry_wait',job['state']);old=Path(job['payload']['worktree']);self.git('config','owner.review','after-public-push');api.live_get=live;self.state.update_job(public,'queued');original=Git.git
        def forbid_old(git,*args,**kwargs):
            if git.repo==old:raise AssertionError('old public Git executed after verified push')
            return original(git,*args,**kwargs)
        with patch.object(Git,'git',forbid_old):self.run_public(supervisor,api)
        job=self.state.job(public);self.assertEqual('complete',job['state'],job['error']);self.assertEqual(1,len([r for r in api.requests if r==('POST','/releases')]));self.assertEqual(1,len([r for r in api.requests if r[0]=='POST' and '/dispatches' in r[1]]))

class R4ClosureAndWrapperTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def test_N406_manual_close_closes_stale_rows_preserving_answer(self):
        supervisor=self.supervisor();self.state.revision('student','p',self.manifest('A'));old=self.state.rows('SELECT id FROM jobs WHERE package_id=1')[0]['id'];q=self.state.question(old,'content','author','Author?');self.state.answer(q,'teacher','admin-content');self.state.revision('student','p',self.manifest('B'));job=self.state.job(old)
        evidence={'job_id':old,'revision_seq':job['revision_seq'],'base':job['payload'].get('base'),'payload_sha256':digest(job['payload']),'reason':'Controlled owner manual closure retaining stale evidence','closure_records':self.evidence_records()};admin.close_job(supervisor,old,evidence)
        row=self.state.rows('SELECT * FROM questions WHERE id=?',(q,))[0];self.assertEqual('closed',row['state']);self.assertEqual('teacher',row['answer'])

    def test_N410_interactive_finite_grace_allows_sigterm_descendant_save(self):
        from school_notes.cli import wrapper
        supervisor=self.supervisor();self.config.update(run_seconds=1,interactive_terminate_grace_seconds=0.3);supervisor.lock.__exit__()
        child="import signal,time,sys;from pathlib import Path\ndef stop(*args):\n time.sleep(0.1);Path('wiki/math/saved.md').write_text('saved after SIGTERM');sys.exit(0)\nsignal.signal(signal.SIGTERM,stop);Path('wiki/math/dirty.md').write_text('retained');time.sleep(10)"
        program="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);time.sleep(.2)"
        receipt=wrapper(self.config,'student',[sys.executable,'-c',program])
        self.assertEqual('saved after SIGTERM',(self.repo/'wiki/math/saved.md').read_text());self.assertIn('wiki/math/saved.md',receipt['hashes']);self.assertEqual(0,receipt['exit_code'])


    def test_N4_worker_explicit_ignore_rules_bound_by_real_command_builder(self):
        from school_notes.agents import Agent
        from school_notes.common import Window
        config=json.loads((fixture.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable;agent=Agent(config,self.state,None,Window());job={'id':1,'revision_seq':None,'payload':{}}
        command=agent.build_command(job,'candidate',{'job_id':1,'revision_seq':None,'inputs':[]},self.repo,self.root/'rules-command','controlled builder',1)
        self.assertEqual(1,command['argv'].count('--ignore-rules'));self.assertIn('--ignore-user-config',command['argv']);self.assertIn('--strict-config',command['argv'])
        proof=self.root/'never-ready.json';atomic_json(proof,{})
        config['codex']['evidence']=str(proof)
        with self.assertRaisesRegex(Blocked,'proof'):agent._gate('codex')
