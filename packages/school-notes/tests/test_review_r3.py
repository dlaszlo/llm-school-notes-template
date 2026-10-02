"""R3 real Git and finite orchestration regressions; no live services/proofs."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import test_app as fixture
import test_review_r1 as r1
import test_review_r2 as r2
from school_notes import admin
from school_notes.agents import Agent
from school_notes.cli import finalize_external,wrapper
from school_notes.common import Blocked,EffectPending,RunLock,Window,atomic_json,digest,file_hash,private_dir
from school_notes.config import load
from school_notes.drive import FOLDER
from school_notes.pipeline import Supervisor
from school_notes.verify import Git,Renderer,manifest_with_hashes


class R3Tests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor
    evidence_records=r2.R2Tests.evidence_records

    def test_R301_external_push_between_observe_and_candidate_waits_ack(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');original=supervisor.candidate
        def concurrent(job):
            (self.repo/'wiki/math/elsewhere.md').write_text('# External unreviewed\n')
            self.git('add','.');self.git('commit','-m','External concurrent');self.git('push','origin','HEAD:main')
            return original(job)
        supervisor.candidate=concurrent
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('ack_wait',job['state']);self.assertFalse(job['payload'].get('worktree'));self.assertNotIn('candidate',supervisor.agents.calls)
        self.assertEqual(old,self.state.rows("SELECT ack_sha FROM observations WHERE id='baseline:student'")[0]['ack_sha'])

    def external_job(self,supervisor):
        base=self.git('rev-parse','HEAD');name='wiki/math/human.md'
        (self.repo/name).write_text('# Human reviewed lesson\n');self.git('add','.');self.git('commit','-m','Human lesson');self.git('push','origin','HEAD:main')
        head=self.git('rev-parse','HEAD');payload={'base':base,'head':head,'changes':{name:file_hash(self.repo/name)}}
        jobid=self.state.enqueue('external_change_review','student','external',payload)
        build,_=fixture.FakeRenderer({},supervisor.lock,supervisor.window).build(self.repo,{},self.root/'external-render')
        payload.update(external_manifest=manifest_with_hashes(self.repo,json.loads((self.repo/'publication/pilot.json').read_text())),external_build=str(build),external_artifacts=Renderer.artifacts(build),external_review_envelope={'inputs':[{'path':str(self.repo/name),'sha256':file_hash(self.repo/name),'kind':'external-content'}]})
        review=self.root/'review.json';atomic_json(review,{'accepted':'controlled independent fixture'})
        supervisor.save_review(self.state.job(jobid),review,{},'external-content,visual')
        self.state.update_job(jobid,'review_wait','external_review',payload)
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=? WHERE id='baseline:student'",(head,))
        return jobid,base

    def test_R302_finalize_external_resume_after_failed_push_preserves_review_base(self):
        supervisor=self.supervisor();jobid,base=self.external_job(supervisor);original=Git.git;failed=[]
        def fail_push(git,*args,**kwargs):
            if args[:1]==('push',) and not failed:
                failed.append(True);raise Blocked('synthetic transient push failure')
            return original(git,*args,**kwargs)
        with patch.object(Git,'git',fail_push):
            with self.assertRaises(Blocked):finalize_external(supervisor,jobid)
        self.assertEqual(base,self.state.job(jobid)['payload']['base'])
        completed=finalize_external(supervisor,jobid)
        self.assertEqual('complete',self.state.job(jobid)['state']);self.assertEqual(completed['commit'],self.git('rev-parse','HEAD'))

    def test_R302_finalize_external_reconciles_successful_remote_push(self):
        supervisor=self.supervisor();jobid,base=self.external_job(supervisor);original=Git.git;failed=[]
        def lost_reply(git,*args,**kwargs):
            result=original(git,*args,**kwargs)
            if args[:1]==('push',) and not failed:
                failed.append(True);raise Blocked('synthetic lost reply after remote success')
            return result
        with patch.object(Git,'git',lost_reply):
            with self.assertRaises(Blocked):finalize_external(supervisor,jobid)
        supervisor.observe_git('student')
        completed=finalize_external(supervisor,jobid)
        self.assertEqual('complete',self.state.job(jobid)['state']);self.assertEqual(completed['commit'],self.git('rev-parse','HEAD'))
        self.assertEqual(base,self.state.job(jobid)['payload']['base'])

    def test_R303_unicode_and_quoted_source_filename_completes(self):
        supervisor=self.supervisor();self.drive.items['file']['name']='01-óra „idézet".png'
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('complete',job['state'],job['error'])
        names=Git(self.repo).names('ls-files','-z')
        self.assertTrue(any('01-óra „idézet".png' in name for name in names))

    def test_R304_rename_lists_removed_and_added_with_exact_unicode(self):
        supervisor=self.supervisor();old='wiki/math/óra "régi".md';new='wiki/math/új.md'
        (self.repo/old).write_text('# Rename source\n');self.git('add','.');self.git('commit','-m','Existing file');self.git('push','origin','HEAD:main')
        base=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(base,base))
        self.git('mv',old,new);self.git('commit','-m','Rename');self.git('push','origin','HEAD:main');supervisor.observe_git('student')
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")[0]['id'])
        self.assertEqual({old:None,new:file_hash(self.repo/new)},job['payload']['changes'])

    def test_R305_owner_session_outlives_window_retains_edits_without_false_review(self):
        supervisor=self.supervisor();self.config['run_seconds']=1
        supervisor.lock.__exit__()
        receipt=wrapper(self.config,'student',[sys.executable,'-c',"from pathlib import Path;import time;Path('wiki/math/dirty.md').write_text('retained');time.sleep(1.2)"])
        self.assertEqual('recorded',receipt['state']);self.assertIn('wiki/math/dirty.md',receipt['hashes']);self.assertEqual(0,receipt['exit_code'])
        self.assertEqual([],self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'"))


    def test_R306_all_source_chunks_have_complete_changed_text_context(self):
        supervisor=self.supervisor();self.config['review_chunk_items']=3
        inputs=[]
        for i in range(10):
            image=self.root/f'page-{i}.png';image.write_bytes(fixture.PNG+bytes([i]));inputs.append({'path':str(image),'sha256':file_hash(image),'kind':'source-page'})
        for name,kind in (('lesson.md','candidate'),('manifest.json','manifest-diff'),('result.json','agent-result')):
            path=self.root/name;path.write_text('complete changed teaching context '+name);inputs.append({'path':str(path),'sha256':file_hash(path),'kind':kind})
        jobid=self.state.enqueue('ingest','student','chunks',{})
        class Inspect(fixture.FakeAgents):
            def call(inner,job,phase,envelope,*args):
                self.assertEqual(3,len(envelope['comparison_context']));self.assertTrue(any(Path(item['path']).name=='lesson.md' for item in envelope['comparison_context']))
                self.assertEqual(envelope['comparison_context_hash'],digest([{k:v for k,v in item.items() if k!='path'} for item in envelope['comparison_context']]))
                self.assertTrue(all(item['kind']=='source-page' for item in envelope['inputs']))
                response,path=super().call(job,phase,envelope,*args);response['evidence'].append('comparison_context_sha256='+envelope['comparison_context_hash']);atomic_json(path,response);return response,path
        supervisor.agents=Inspect(self.state,supervisor.lock)
        supervisor.bounded_review(self.state.job(jobid),'source_review',inputs,'content',require_visual=False)
        self.assertEqual(4,len(supervisor.agents.calls))

    def test_R307_stale_candidate_stops_before_agent_or_renderer(self):
        supervisor=self.supervisor();supervisor.observe_drive('student');job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.state.update_job(job['id'],'queued','candidate');self.drive.items['package']['description']='new context';supervisor.observe_drive('student')
        self.state.update_job(job['id'],'queued')
        with patch('school_notes.pipeline.Renderer') as renderer:supervisor.process(job['id']);renderer.assert_not_called()
        current=self.state.job(job['id']);self.assertEqual('blocked',current['state']);self.assertIn('reconcile-job',current['error']);self.assertEqual([],supervisor.agents.calls)

    def test_R308_ignored_source_blocks_before_agent(self):
        supervisor=self.supervisor();(self.repo/'.gitignore').write_text('sources/**/*.png\n');self.git('add','.');self.git('commit','-m','Owner ignore');self.git('push','origin','HEAD:main')
        head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(head,head))
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('blocked',job['state']);self.assertIn('ignored source',job['error']);self.assertNotIn('candidate',supervisor.agents.calls)

    def test_R313_unchanged_packages_do_not_create_capture_directories(self):
        supervisor=self.supervisor();supervisor.observe_drive('student');count=len(list((self.root/'captures').iterdir()))
        for i in range(4):supervisor.observe_drive('student')
        self.assertEqual(count,len(list((self.root/'captures').iterdir())));self.assertEqual(1,len(self.drive.downloads))

    def test_R314_git_observation_runs_with_unready_drive_baseline(self):
        supervisor=self.supervisor();self.state.meta('drive-baseline:student','unfinished')
        (self.repo/'tools/subjects.json').write_text('{"maintenance":true}');self.git('add','.');self.git('commit','-m','Owner maintenance');self.git('push','origin','HEAD:main')
        supervisor.run_once()
        self.assertTrue(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'"));self.assertTrue(self.state.rows("SELECT id FROM jobs WHERE kind='runtime_block'"))

    def test_R315_teacher_background_root_rejected_before_adapter(self):
        value=json.loads((fixture.REPO/'packages/school-notes/config.example.json').read_text());first=next(iter(value['learners'].values()));first['inputs'][0]['source_role']='teacher_background'
        path=self.root/'invalid-config.json';atomic_json(path,value)
        with self.assertRaisesRegex(Blocked,'teacher_background'):load(path)


class R3PublicTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    public_setup=r1.PublicR1Tests.public_setup
    run_public=r1.PublicR1Tests.run_public

    def test_R309_published_job_survives_cdn_delay_and_descendant_private_push(self):
        supervisor,private,public,api=self.public_setup();self.run_public(supervisor,api)
        self.state.approve(public,digest(self.state.job(public)['payload']['public_proposal']));api.complete=True
        real_live=api.live_get
        api.live_get=lambda url:b'{}' if url.endswith('release.json') else real_live(url)
        self.run_public(supervisor,api)
        self.assertEqual('retry_wait',self.state.job(public)['state'])
        (self.repo/'wiki/math/later.md').write_text('# Later private commit\n');self.git('add','.');self.git('commit','-m','Later private');self.git('push','origin','HEAD:main');later=self.git('rev-parse','HEAD')
        # Simulate later independently reviewed private HEAD, no regression of ack.
        with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=? WHERE id='baseline:student'",(later,later))
        api.live_get=real_live;self.state.update_job(public,'queued');self.run_public(supervisor,api)
        completed=self.state.job(public);self.assertEqual('complete',completed['state'],completed['error'])
        self.assertEqual(later,self.state.rows("SELECT ack_sha FROM observations WHERE id='baseline:student'")[0]['ack_sha'])
        self.assertEqual(1,len([r for r in api.requests if r==('POST','/releases')]))
        self.assertEqual(1,len([r for r in api.requests if r[0]=='POST' and '/dispatches' in r[1]]))


class R3RecoveryTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    supervisor=r2.R2Tests.supervisor

    def retained_candidate(self):
        supervisor=self.supervisor()
        class Asking(fixture.FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                response,path=super().call(job,phase,envelope,cwd,directory,instructions)
                if phase=='candidate':response['uncertainties']=['Exact date?'];atomic_json(path,response)
                return response,path
        supervisor.agents=Asking(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('question_wait',job['state'],job['error'])
        return supervisor,job

    def test_R310_config_identity_drift_rebases_without_old_git_execution(self):
        supervisor,job=self.retained_candidate();old=Path(job['payload']['worktree']);lesson=old/'wiki/math/lesson.md';sha=file_hash(lesson)
        question=self.state.rows("SELECT id FROM questions WHERE job_id=? AND kind='content'",(job['id'],))[0]['id'];self.state.answer(question,'2026-09-30','admin-content')
        self.git('config','owner.review','maintenance')
        original=Git.git;old_calls=[]
        def guarded(git,*args,**kwargs):
            if git.repo==old:old_calls.append(args);raise AssertionError('untrusted old Git subprocess')
            return original(git,*args,**kwargs)
        with patch.object(Git,'git',guarded):admin.rebase_candidate(supervisor,job['id'])
        current=self.state.job(job['id']);history=current['payload']['candidate_history'][0]
        self.assertEqual([],old_calls);self.assertTrue(history['metadata_drift']);self.assertEqual(sha,history['changes']['wiki/math/lesson.md']);self.assertEqual(sha,file_hash(lesson))
        supervisor.agents=fixture.FakeAgents(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        current=self.state.job(job['id']);self.assertEqual('complete',current['state'],current['error']);self.assertNotEqual(str(old),current['payload']['worktree'])

    def test_R311_exact_phase_budget_visible_and_new_fix_phase_independent(self):
        supervisor=self.supervisor();config=json.loads((fixture.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable
        agent=Agent(config,self.state,supervisor.lock,Window());jobid=self.state.enqueue('ingest','student','attempt-budget',{})
        proof=self.root/'synthetic-proof.json';atomic_json(proof,{'synthetic_transport_only':True})
        settings=agent.role_settings('codex');settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c','pass','{result}'])
        def transport(argv,cwd,**kwargs):
            Path(str(kwargs['log'])+'.stderr').write_text('')
            directory=Path(argv[-1]).parent;envelope=json.loads((directory/'input.json').read_text());atomic_json(directory/'result.json',fixture.result(envelope));Path(kwargs['log']).write_text('{"type":"turn.completed"}\n')
        worker=self.root/'budget-worker';worker.mkdir()
        phase='candidate:1111111111111111'
        with patch.object(agent,'_gate',return_value=settings),patch('school_notes.agents.run',transport):
            for _ in range(3):agent.call(self.state.job(jobid),'candidate',{'job_id':jobid,'revision_seq':None,'inputs':[],'attempt_phase':phase},worker,self.root/'finite','test')
            with self.assertRaisesRegex(Blocked,phase+r' \(3/3\)'):agent.call(self.state.job(jobid),'candidate',{'job_id':jobid,'revision_seq':None,'inputs':[],'attempt_phase':phase},worker,self.root/'finite','test')
            agent.call(self.state.job(jobid),'candidate',{'job_id':jobid,'revision_seq':None,'inputs':[],'attempt_phase':'candidate:2222222222222222'},worker,self.root/'finite','test')
        attempts=admin.inspect_job(supervisor,jobid)['attempts'];self.assertEqual(4,len(attempts));self.assertEqual([phase]*3+['candidate:2222222222222222'],[a['phase'] for a in attempts]);self.assertTrue(all(a['state']=='complete' for a in attempts))

    def test_R312_disk_diagnostics_deduplicate_job_and_report_semantics(self):
        supervisor=self.supervisor()
        from school_notes.report import semantic
        supervisor.record_runtime_block('student','disk: free=123 estimate=456 reserve=789');first=semantic(supervisor.status())
        supervisor.record_runtime_block('student','disk: free=120 estimate=456 reserve=789');self.assertEqual(first,semantic(supervisor.status()))
        self.assertEqual(1,len(self.state.rows("SELECT id FROM jobs WHERE kind='runtime_block'")))
        source={'ready_id':'ready','subject_slug':'math','source_role':'notebook'}
        first_stage=self.root/'retained-a';second_stage=self.root/'retained-b';first_stage.mkdir();second_stage.mkdir()
        supervisor.capture_block('student','bad',source,False,str(first_stage),'disk: free=111 estimate=456 reserve=789','stable-files')
        supervisor.capture_block('student','bad',source,False,str(second_stage),'disk: free=110 estimate=456 reserve=789','stable-files')
        jobs=self.state.rows("SELECT id FROM jobs WHERE kind='capture_block'");self.assertEqual(1,len(jobs));saved=self.state.job(jobs[0]['id'])
        self.assertEqual(str(first_stage),saved['payload']['staging']);self.assertIn(str(second_stage),saved['payload']['retained_staging']);self.assertIn('free=110',saved['payload']['latest_diagnostic'])

    def test_R306_context_binding_and_size_are_required_for_coverage(self):
        supervisor=self.supervisor();jobid=self.state.enqueue('ingest','student','context-negative',{});job=self.state.job(jobid)
        source=self.root/'source.png';source.write_bytes(b'controlled source');text=self.root/'lesson.md';text.write_text('changed teaching content')
        inputs=[{'path':str(source),'sha256':file_hash(source),'kind':'source'},{'path':str(text),'sha256':file_hash(text),'kind':'candidate'}]
        class OmitsBinding(fixture.FakeAgents):
            def call(inner,*args,**kwargs):
                response,path=super().call(*args,**kwargs);response['evidence']=['claimed complete'];atomic_json(path,response);return response,path
        supervisor.agents=OmitsBinding(self.state,supervisor.lock)
        with self.assertRaisesRegex(Blocked,'comparison'):supervisor.bounded_review(job,'source_review',inputs,'source',require_visual=False)
        self.assertEqual([],self.state.rows("SELECT * FROM reviews WHERE state='accepted'"))
        text.write_text('x'*1024);inputs[1]['sha256']=file_hash(text)
        self.config['review_chunk_bytes']=1024
        with self.assertRaisesRegex(Blocked,'context'):supervisor.bounded_review(job,'source_review',inputs,'source',require_visual=False)

    def test_R308_exact_commit_blob_membership_requires_present_matching_source(self):
        path=self.repo/'sources/óra.png';path.parent.mkdir(exist_ok=True);path.write_bytes(b'original exact bytes');sources=[{'path':str(path),'sha256':file_hash(path)}]
        git=Git(self.repo)
        with self.assertRaisesRegex(Blocked,'absent'):git.verify_sources(sources)
        self.git('add','.');self.git('commit','-m','Exact source');git.verify_sources(sources)
        path.write_bytes(b'changed bytes');sources[0]['sha256']=file_hash(path)
        with self.assertRaisesRegex(Blocked,'differs'):git.verify_sources(sources)

    def test_R316_stale_questions_preserve_answers_and_respect_target_waiting(self):
        supervisor=self.supervisor();self.state.revision('student','p',self.manifest('A'));old=self.state.rows("SELECT id FROM jobs WHERE package_id IS NOT NULL")[0]['id'];q=self.state.question(old,'content','author','Author?');self.state.answer(q,'classmate','admin-content')
        unanswered=self.state.question(old,'content','date','Date?');self.state.revision('student','p',self.manifest('B'));target=self.state.rows('SELECT id FROM jobs WHERE package_id=1 ORDER BY id DESC')[0]['id']
        self.assertEqual(['stale','stale'],[r['state'] for r in self.state.rows('SELECT state FROM questions ORDER BY id')]);self.assertEqual('classmate',self.state.rows('SELECT answer FROM questions WHERE id=?',(q,))[0]['answer'])
        with self.assertRaises(Blocked):self.state.answer(unanswered,'late','admin-content')
        self.state.update_job(target,'question_wait');admin.reconcile_job(supervisor,old);self.assertEqual('question_wait',self.state.job(target)['state']);self.assertEqual('classmate',self.state.job(target)['payload']['reconciled_from']['answers'][0]['answer'])
        self.state.update_job(target,'complete')
        with self.assertRaisesRegex(Blocked,'eligible'):admin.reconcile_job(supervisor,old)

    def test_R301_push_rechecks_current_ack_before_remote_write(self):
        supervisor=self.supervisor();old=self.git('rev-parse','HEAD');original=supervisor.push
        def change_ack(job):
            with self.state.db:self.state.db.execute("UPDATE observations SET ack_sha=? WHERE id='baseline:student'",('0'*40,))
            return original(job)
        supervisor.push=change_ack
        with patch('school_notes.pipeline.Renderer',fixture.FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('blocked',job['state']);self.assertIn('ack',job['error']);self.assertEqual(old,self.git('rev-parse','refs/remotes/origin/main'));self.assertEqual([],self.state.rows("SELECT * FROM effects WHERE kind='git-push' AND state='verified'"))


    def test_R311_rebase_renews_identical_byte_review_task_phase(self):
        supervisor=self.supervisor();source=self.root/'source.png';source.write_bytes(b'controlled source');text=self.root/'lesson.md';text.write_text('identical teaching bytes')
        inputs=[{'path':str(source),'sha256':file_hash(source),'kind':'source'},{'path':str(text),'sha256':file_hash(text),'kind':'candidate'}]
        jobid=self.state.enqueue('ingest','student','review-task-scope',{'base':self.git('rev-parse','HEAD')});phases=[]
        class Records(fixture.FakeAgents):
            def call(inner,job,phase,*args,**kwargs):phases.append(phase);return super().call(job,phase,*args,**kwargs)
        supervisor.agents=Records(self.state,supervisor.lock)
        supervisor.bounded_review(self.state.job(jobid),'source_review',inputs,'source',require_visual=False)
        job=self.state.job(jobid);job['payload']['candidate_history']=[{'retained':'old review evidence'}];self.state.update_job(jobid,payload=job['payload'])
        supervisor.bounded_review(self.state.job(jobid),'source_review',inputs,'source',require_visual=False)
        self.assertEqual(2,len(phases));self.assertNotEqual(*phases)


class R3PublicBudgetTests(fixture.Base):
    setUp=fixture.PilotTests.setUp
    public_setup=r1.PublicR1Tests.public_setup
    run_public=r1.PublicR1Tests.run_public

    def test_R309_live_readonly_retries_stop_at_five_without_duplicate_writes(self):
        supervisor,private,public,api=self.public_setup();self.run_public(supervisor,api)
        self.state.approve(public,digest(self.state.job(public)['payload']['public_proposal']));api.complete=True
        real_live=api.live_get;api.live_get=lambda url:b'{}' if url.endswith('release.json') else real_live(url)
        for number in range(1,6):
            if number>1:self.state.update_job(public,'queued')
            self.run_public(supervisor,api);job=self.state.job(public)
            self.assertEqual(number,job['payload']['live_verification_attempts']);self.assertEqual('retry_wait' if number<5 else 'blocked',job['state'])
        self.state.update_job(public,'queued');self.run_public(supervisor,api);job=self.state.job(public)
        self.assertEqual(5,job['payload']['live_verification_attempts']);self.assertIn('(5/5)',job['error']);self.assertEqual(1,len([r for r in api.requests if r==('POST','/releases')]));self.assertEqual(1,len([r for r in api.requests if r[0]=='POST' and '/dispatches' in r[1]]))
