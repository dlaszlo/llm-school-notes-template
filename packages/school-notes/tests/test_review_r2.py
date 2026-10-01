"""R2 exact recovery regressions; real local Git/Poppler, transport fakes only."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_app as fixture
from test_app import Base,FakeAgents,FakeRenderer
from test_review_r1 import PublicR1Tests,PublicRenderer
from school_notes import admin
from school_notes.cli import main,wrapper
from school_notes.common import Blocked,EffectPending,RunLock,atomic_json,digest,file_hash,private_dir
from school_notes.drive import DriveAPI,ReadOnlyDriveAPI
from school_notes.pipeline import Supervisor
from school_notes.report import pdf_bytes,semantic,write
from school_notes.verify import Git,manifest_with_hashes


class R2Tests(Base):
    setUp=fixture.PilotTests.setUp

    def supervisor(self):
        lock=RunLock(self.config['lock_file']);lock.__enter__();self.addCleanup(lock.__exit__)
        supervisor=Supervisor(self.config,self.state,lock,lambda _:self.drive)
        supervisor.agents=FakeAgents(self.state,lock)
        return supervisor

    def evidence_records(self):
        path=self.root/'owner-closure.txt';path.write_text('Owner verified exact closure')
        return [{'path':str(path),'sha256':file_hash(path)}]

    def test_N01_question_candidate_rebased_after_other_package_push(self):
        supervisor=self.supervisor()
        # First package reaches retained candidate and asks a content question.
        class Asking(FakeAgents):
            def call(inner,job,phase,envelope,cwd,directory,instructions):
                response,path=super().call(job,phase,envelope,cwd,directory,instructions)
                if phase=='candidate':
                    for name in ('wiki/math/lesson.md','wiki/log.md'):
                        target=Path(cwd)/name;target.write_text(target.read_text()+f"job {job['id']}\n")
                    changes=Git(cwd,inner.lock).changes(job['payload']['base'],sources=job['payload'].get('git_sources',[]))
                    response['file_changes']=[{'path':name,'sha256':sha} for name,sha in changes.items() if not name.startswith('sources/')]
                    atomic_json(path,response)
                if phase=='candidate' and job['package_id']==1 and not job['payload'].get('candidate_history'):
                    response['uncertainties']=['exact lesson date?'];atomic_json(path,response)
                return response,path
        supervisor.agents=Asking(self.state,supervisor.lock)
        with patch('school_notes.pipeline.Renderer',FakeRenderer):supervisor.run_once()
        first=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('question_wait',first['state']);old=Path(first['payload']['worktree'])
        # Different actual bytes avoid the independent duplicate-origin gate.
        from PIL import Image
        image=io.BytesIO();Image.new('RGB',(9,9),'black').save(image,format='PNG')
        self.drive.add('package2','ready','Other notebook');self.drive.add('file2','package2','01.png',image.getvalue())
        with patch('school_notes.pipeline.Renderer',FakeRenderer):supervisor.run_once()
        second=self.state.job(self.state.rows("SELECT id FROM jobs WHERE package_id=2 AND kind='ingest'")[0]['id'])
        self.assertEqual('complete',second['state'],second['error'])
        question=self.state.rows("SELECT id FROM questions WHERE job_id=? AND kind='content'",(first['id'],))[0]['id']
        self.state.answer(question,'2026-09-30','admin-content')
        with patch('school_notes.pipeline.Renderer',FakeRenderer):supervisor.run_once()
        self.assertEqual('blocked',self.state.job(first['id'])['state'])
        rebase=admin.rebase_candidate(supervisor,first['id'])
        self.assertEqual(self.git('rev-parse','HEAD'),rebase['base'])
        with patch('school_notes.pipeline.Renderer',FakeRenderer):supervisor.run_once()
        final=self.state.job(first['id']);self.assertEqual('complete',final['state'],final['error'])
        self.assertNotEqual(str(old),final['payload']['worktree']);self.assertTrue(old.is_dir())
        self.assertEqual('2026-09-30',final['payload']['candidate_history'][0]['answers'][0]['answer'])

    def test_N02_pure_rename_before_commit_refreshes_without_revision(self):
        supervisor=self.supervisor()
        original=supervisor.stable
        def rename(job):
            if job['phase']=='commit':
                self.drive.items['file'].update(name='renamed.png',version='2',modifiedTime='new')
            return original(job)
        supervisor.stable=rename
        with patch('school_notes.pipeline.Renderer',FakeRenderer):supervisor.run_once()
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.assertEqual('complete',job['state'],job['error'])
        supervisor.observe_drive('student')
        self.assertEqual(1,self.state.rows('SELECT COUNT(*) n FROM revisions')[0]['n'])
        self.assertEqual(1,len(self.drive.downloads))
        self.assertEqual('renamed.png',next(f['name'] for f in job['payload']['manifest']['inventory'] if f['id']=='file'))

    def test_N03_maintenance_ack_exact_manifest_closure_wakes_jobs(self):
        supervisor=self.supervisor();base=self.git('rev-parse','HEAD')
        (self.repo/'tools/subjects.json').write_text('{"labels":{},"subjects":{}}\n')
        self.git('add','.');self.git('commit','-m','Human configuration');self.git('push','origin','HEAD:main')
        supervisor.observe_git('student')
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")[0]['id'])
        wait=self.state.enqueue('ingest','student','waiting',{});self.state.update_job(wait,'ack_wait')
        path='publication/pilot.json';evidence={'job_id':job['id'],'base':base,'head':self.git('rev-parse','HEAD'),'changes':job['payload']['changes'],
            'manifest_impact':{'path':path,'sha256':file_hash(self.repo/path),'manifest':json.loads((self.repo/path).read_text())},'open_reviews':[],'open_questions':[],
            'reason':'Owner reviewed maintenance','closure_records':self.evidence_records()}
        bad=copy.deepcopy(evidence);bad['changes']={}
        with self.assertRaises(Blocked):admin.acknowledge_maintenance(supervisor,job['id'],bad)
        result=admin.acknowledge_maintenance(supervisor,job['id'],evidence)
        self.assertEqual(evidence['head'],result['ack_sha']);self.assertEqual('queued',self.state.job(wait)['state'])
        self.assertEqual('complete',self.state.job(job['id'])['state'])

    def test_N04_gitfile_and_config_tampering_block_before_subprocess(self):
        main=Git(self.repo);candidate=main.worktree(self.root/'candidate',main.head());identity=candidate.identity
        marker=candidate.repo/'.git';original=marker.read_bytes();marker.write_text('gitdir: /tmp/untrusted\n')
        with patch('school_notes.verify.run') as invoked:
            with self.assertRaises(Blocked):Git(candidate.repo,identity=identity).head()
            invoked.assert_not_called()
        marker.write_bytes(original)
        config=Path(identity['common'])/'config';config.write_text(config.read_text()+'\n[core]\nfsmonitor = /tmp/untrusted-command\n')
        with patch('school_notes.verify.run') as invoked:
            with self.assertRaises(Blocked):candidate.clean()
            invoked.assert_not_called()

    def test_N04_git_commands_pin_metadata_disable_execution_hooks(self):
        git=Git(self.repo)
        with patch('school_notes.verify.run',return_value='') as invoked:git.clean()
        argv=invoked.call_args.args[0]
        self.assertIn('--git-dir',argv);self.assertIn('--work-tree',argv)
        self.assertIn('core.hooksPath=/dev/null',argv);self.assertIn('core.fsmonitor=false',argv)

    def test_N05_renderer_branding_contract_png_only(self):
        directory=private_dir(self.repo/'publication/assets');(directory/'light.png').write_bytes(self.drive.data['file'])
        manifest=json.loads((self.repo/'publication/pilot.json').read_text());manifest['branding']={theme:{'path':'publication/assets/light.png','sha256':'pending'} for theme in ('light','dark')}
        bound=manifest_with_hashes(self.repo,manifest)
        self.assertEqual(file_hash(directory/'light.png'),bound['branding']['dark']['sha256'])
        for name in ('wiki/math/index.md','publication/assets/light.svg','publication/assets/../pilot.json'):
            bad=copy.deepcopy(manifest);bad['branding']['light']['path']=name
            with self.assertRaises(Blocked):manifest_with_hashes(self.repo,bad)
        (directory/'light.png').write_text('not PNG')
        with self.assertRaises(Blocked):manifest_with_hashes(self.repo,manifest)

    def test_N06_delta_page_reuse_excludes_oversized_aggregate(self):
        supervisor=self.supervisor();jobid=self.state.enqueue('ingest','student','render-review',{})
        build=private_dir(self.root/'build');page={'route':'old','html':'<p>'+'a'*3000+'</p>','title':'Old'}
        atomic_json(build/'payload.json',{'pages':[page],'collections':[{'id':'dup','chapters':[{'html':'x'*60000}]}]})
        job=self.state.job(jobid);job['payload'].update(build=str(build),artifacts={'payload.json':file_hash(build/'payload.json')})
        self.state.update_job(jobid,payload=job['payload']);self.config['review_chunk_bytes']=8192
        inputs=supervisor.render_review_inputs(job)
        self.assertTrue(all(Path(i['path']).stat().st_size<8192 for i in inputs))
        supervisor.bounded_review(job,'review',inputs,'visual',reuse_visual=True)
        calls=len(supervisor.agents.calls)
        newer=self.state.enqueue('ingest','student','render-review2',job['payload']);newjob=self.state.job(newer)
        atomic_json(build/'payload.json',{'pages':[page,{'route':'new','html':'<p>new</p>','title':'New'}],'collections':[]})
        supervisor.bounded_review(newjob,'review',supervisor.render_review_inputs(newjob),'visual',reuse_visual=True)
        self.assertEqual(calls+1,len(supervisor.agents.calls))
        closure=json.loads(self.state.rows('SELECT closure FROM reviews WHERE job_id=?',(newer,))[0]['closure'])
        self.assertFalse(any(i.get('page_key')=='old' for i in closure['inputs']))
        # An exact page accepted in a later-invalidated closure is not reused.
        with self.state.db:self.state.db.execute("UPDATE reviews SET state='invalidated' WHERE job_id=?",(jobid,))
        third=self.state.enqueue('ingest','student','render-review3',job['payload'])
        supervisor.bounded_review(self.state.job(third),'review',supervisor.render_review_inputs(newjob),'visual',reuse_visual=True)
        last=json.loads(self.state.rows('SELECT closure FROM reviews WHERE job_id=? ORDER BY id DESC',(third,))[0]['closure'])
        self.assertTrue(any(i.get('page_key')=='old' for i in last['inputs']))

    def test_N07_readonly_adapter_reuses_exact_existing_scope_get_only(self):
        # Fake shared-helper module owns refresh; no real credentials/network.
        tool=self.root/'helper.py';tool.write_text("SCOPE='https://www.googleapis.com/auth/drive.file'\nclass Refused(Exception):pass\nclass ApiError(Refused):pass\nclass Drive:\n def __init__(self,home):\n  self.scope=SCOPE\n  self.token='fake'\n def request(self,*args):return 200,{}, {'id':'file'}\n")
        proof=self.root/'proof.json';atomic_json(proof,{k:True for k in ('manual_upload_read','recursive_visibility','child_account_access','token_refresh','oauth_project_status_checked')} | {'scope':'https://www.googleapis.com/auth/drive.readonly','config_dir':str(self.root.resolve()),'readonly_only':True})
        api=DriveAPI(str(tool),str(self.root),str(proof),reader_config={'config_dir':str(self.root),'scope':'https://www.googleapis.com/auth/drive.readonly','evidence':str(proof)})
        writerproof=self.root/'writer-proof.json';atomic_json(writerproof,{'manual_upload_read':False,'recursive_visibility':False,'child_account_access':False,'token_refresh':True,'oauth_project_status_checked':True})
        api=DriveAPI(str(tool),str(self.root),str(writerproof),reader_config={'config_dir':str(self.root),'scope':'https://www.googleapis.com/auth/drive.readonly','evidence':str(proof)})
        with self.assertRaises(Blocked):DriveAPI(str(tool),str(self.root),str(writerproof))
        self.assertEqual('https://www.googleapis.com/auth/drive.file',api.drive.scope)
        self.assertEqual('https://www.googleapis.com/auth/drive.readonly',api.input_reader.drive.scope)
        self.assertEqual('file',api.input_reader.metadata('file')['id'])
        for operation in (lambda:api.input_reader.reserve_id(),lambda:api.input_reader.create_folder('a'),lambda:api.input_reader.upload('a'),lambda:api.input_reader.request('POST','https://www.googleapis.com/drive/v3/files',{})):
            with self.assertRaises(Blocked):operation()

    def test_N08_emoji_control_report_poppler_and_nonfatal_missing_font(self):
        target=self.root/'report.pdf';target.write_bytes(pdf_bytes(['Hungarian őű 🤖📗\t\x01\u202e']))
        text=subprocess.check_output(['/usr/bin/pdftotext',str(target),'-'],text=True)
        self.assertIn('őű',text);self.assertIn('\\U0001F916',text);self.assertIn('\\u0001',text);self.assertIn('\\u202E',text)
        self.config['report_font']=str(self.root/'missing.ttf');supervisor=self.supervisor()
        job=self.state.enqueue('ingest','student','mutation-test',{});self.state.update_job(job,'blocked')
        self.config['learners']['student'].update(drive_config_dir=str(self.root),drive_evidence='unused')
        with patch('school_notes.cli.load',return_value=self.config),patch('school_notes.cli.RunLock',return_value=supervisor.lock),patch('sys.stdout',new=io.StringIO()) as output:
            # Reentering a lock would conflict; use existing lock context shim.
            class Held:
                def __enter__(inner):return supervisor.lock
                def __exit__(inner,*args):pass
            with patch('school_notes.cli.RunLock',return_value=Held()):
                self.assertEqual(0,main(['--config','unused','recover']))
        self.assertIn('report_error',output.getvalue());self.assertTrue(self.state.meta('report-failure'))
        self.assertFalse(list((self.root/'reports').glob('*.pdf')))

    def test_N09_wrapper_uses_ack_range_and_dirty_wait(self):
        supervisor=self.supervisor();ack=self.git('rev-parse','HEAD')
        (self.repo/'wiki/math/prior.md').write_text('# Prior\n');self.git('add','.');self.git('commit','-m','Unreviewed prior');self.git('push','origin','HEAD:main')
        supervisor.lock.__exit__();receipt=wrapper(self.config,'student',[sys.executable,'-c',"from pathlib import Path;Path('wiki/math/dirty.md').write_text('dirty')"])
        self.assertEqual(ack,receipt['review_base']);self.assertIn('wiki/math/prior.md',receipt['hashes']);self.assertIn('wiki/math/dirty.md',receipt['hashes'])
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='external_change_review'")[0]['id'])
        self.assertEqual(ack,job['payload']['base']);self.assertEqual('review_wait',job['state']);self.assertIn('commit and push',job['error'])

    def test_N10_link_baseline_exact_hash_later_changes_queue(self):
        supervisor=self.supervisor();supervisor.observe_drive('student',baseline=True)
        row=self.state.rows('SELECT p.*,r.bytes_hash,r.metadata_hash,r.manifest FROM packages p JOIN revisions r ON r.package_id=p.id AND r.seq=p.current_seq')[0]
        manifest=json.loads(row['manifest'])
        inspection=admin.inspect_package(supervisor,'student','package')
        self.assertEqual(row['bytes_hash'],inspection['binding']['bytes_hash'])
        from PIL import Image
        prepared=self.repo/'sources/previous/read.png';prepared.parent.mkdir(parents=True)
        Image.new('RGB',(6,6),'gray').save(prepared)
        self.assertNotEqual(file_hash(prepared),manifest['files'][0]['sha256'])
        source=self.repo/'wiki/math/source.md';source.write_text('# Source summary\nresource: sources/previous/read.png\ncontent_sha256: '+file_hash(prepared)+'\n')
        self.git('add','.');self.git('commit','-m','Reviewed existing source');self.git('push','origin','HEAD:main');head=self.git('rev-parse','HEAD')
        with self.state.db:self.state.db.execute('UPDATE observations SET observed_sha=?,ack_sha=? WHERE id=?',(head,head,'baseline:student'))
        evidence={k:row[k] for k in ('bytes_hash','metadata_hash')};evidence.update(learner='student',source_id='package',revision_seq=1,files={f['id']:f['sha256'] for f in manifest['files']},head=head,source_summary={'path':'wiki/math/source.md','sha256':file_hash(source)},closure_records=self.evidence_records(),open_reviews=[],open_questions=[],reason='Owner reviewed original/photo-to-read-source projection',source_bindings=[{'file_id':manifest['files'][0]['id'],'original_sha256':manifest['files'][0]['sha256'],'read_source':{'path':'sources/previous/read.png','sha256':file_hash(prepared)}}])
        bad=copy.deepcopy(evidence);bad['files']={}
        with self.assertRaises(Blocked):admin.link_baseline(supervisor,'student','package',bad)
        self.assertEqual('baseline_pending',supervisor.status()['packages'][0]['state'])
        admin.link_baseline(supervisor,'student','package',evidence)
        self.drive.items['package']['description']='Catch-up';supervisor.observe_drive('student')
        job=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='metadata_update'")[0]['id'])
        self.assertEqual(2,job['revision_seq']);self.assertIsNotNone(job['payload']['previous'])
        self.drive.add('newfile','package','02.png',self.drive.data['file']);supervisor.observe_drive('student')
        self.assertEqual(3,self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])['revision_seq'])

    def test_N12_public_proposal_canonical_hash_not_file_hash(self):
        supervisor=self.supervisor();proposal={'artifact':'concrete'}
        job=self.state.enqueue('public_release','student','proposal',{'public_proposal':proposal})
        path=self.root/'proposal.json';atomic_json(path,proposal)
        self.assertEqual(digest(proposal),admin.public_proposal(supervisor,job)['proposal_sha256'])
        self.assertNotEqual(file_hash(path),digest(proposal))

    def test_N13_N15_runtime_success_prunes_observations_preserves_baseline(self):
        supervisor=self.supervisor();supervisor.record_runtime_block('student','previous visibility failure')
        for i in range(35):supervisor.observe_drive('student')
        self.assertEqual('complete',self.state.rows("SELECT state FROM jobs WHERE kind='runtime_block'")[0]['state'])
        self.assertEqual(20,self.state.rows("SELECT COUNT(*) n FROM observations WHERE kind='drive'")[0]['n'])
        status=supervisor.status();self.assertTrue(any(o['id']=='baseline:student' for o in status['observations']))
        saved=self.state.rows("SELECT manifest FROM observations WHERE kind='drive'")
        self.assertEqual(1,len([r for r in saved if isinstance(json.loads(r['manifest']),list)]))
        self.assertTrue(any(p['source_id']=='package' for p in semantic(status)['packages']))

    def test_N13_disappeared_capture_stays_retained_with_explicit_next_step(self):
        supervisor=self.supervisor();self.drive.add('bad-package','ready','Opaque');self.drive.add('bad-file','bad-package','broken.png',b'bad-signature')
        supervisor.observe_drive('student')
        block=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='capture_block'")[0]['id'])
        del self.drive.items['bad-file'];del self.drive.items['bad-package']
        supervisor.observe_drive('student')
        retained=self.state.job(block['id']);self.assertEqual('blocked',retained['state']);self.assertTrue(Path(retained['payload']['staging']).is_dir())
        self.assertIn('absent from configured ready roots',retained['error']);self.assertIn('reject-package',retained['error'])

    def test_N14_move_same_package_to_matching_role_creates_context_revision(self):
        supervisor=self.supervisor();supervisor.observe_drive('student')
        first=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest'")[0]['id'])
        self.drive.add('teacher-ready','incoming','Kész');self.drive.items['package']['parents']=['teacher-ready']
        self.config['learners']['student']['inputs'].append({'ready_id':'teacher-ready','subject_slug':'math','source_role':'teacher_learn'})
        supervisor.observe_drive('student')
        current=self.state.job(self.state.rows("SELECT id FROM jobs WHERE kind='ingest' ORDER BY id DESC")[0]['id'])
        self.assertEqual(first['package_id'],current['package_id']);self.assertEqual(2,current['revision_seq']);self.assertEqual('teacher_learn',current['payload']['manifest']['input_context']['source_role'])
        self.assertEqual(1,len(self.drive.downloads))

    def test_N17_exact_effect_admin_absence_once_then_new_outcome_required(self):
        supervisor=self.supervisor();job=self.state.enqueue('public_release','student','effect-job',{'base':'a'*40})
        effect=self.state.effect(job,'dispatch','owner/repo','b'*64,'dispatch')
        self.state.effect_state('dispatch','unknown',{'request':'retained'})
        current=self.state.rows('SELECT * FROM effects')[0]
        inspection=admin.inspect_effect(supervisor,'dispatch')
        self.assertEqual(digest(current),inspection['observed_effect_sha256'])
        self.assertEqual('a'*40,inspection['source_head'])
        evidence={'effect':{k:current[k] for k in ('stable_key','job_id','kind','target','artifact_hash','external_id','receipt')},'observed_effect_sha256':digest(current),'source_head':'a'*40,'decision':'verified_absent','reason':'Owner verified absence from exact complete provider evidence','closure_records':self.evidence_records()}
        bad=copy.deepcopy(evidence);bad['effect']['artifact_hash']='wrong'
        with self.assertRaises(Blocked):admin.resolve_effect(supervisor,'dispatch',bad)
        admin.resolve_effect(supervisor,'dispatch',evidence)
        planned=self.state.rows('SELECT * FROM effects')[0];calls=[]
        with self.assertRaises(EffectPending):self.state.perform_effect(planned,lambda e:calls.append(e) or None,lambda e:None)
        self.assertEqual(1,len(calls))
        with self.assertRaises(Blocked):admin.resolve_effect(supervisor,'dispatch',evidence)
        with self.assertRaises(EffectPending):self.state.perform_effect(self.state.rows('SELECT * FROM effects')[0],lambda e:self.fail('blind repeat'),lambda e:None)

    def test_N18_manual_close_retains_files_and_does_not_accept_learning(self):
        supervisor=self.supervisor();capture=self.root/'retained.txt';capture.write_text('retained candidate')
        jobid=self.state.enqueue('ingest','student','close',{'base':'a'*40,'worktree':str(capture),'fix_round':2})
        self.state.update_job(jobid,'review_wait');self.state.question(jobid,'content','review','manual fix needed')
        job=self.state.job(jobid);self.assertEqual(digest(job['payload']),admin.inspect_job(supervisor,jobid)['payload_sha256']);evidence={'job_id':jobid,'revision_seq':None,'base':'a'*40,'payload_sha256':digest(job['payload']),'reason':'Owner closes unsupported automatic correction; manual workflow retained','closure_records':self.evidence_records()}
        result=admin.close_job(supervisor,jobid,evidence)
        self.assertEqual('closed_unprocessed',result['state']);self.assertEqual('retained candidate',capture.read_text());self.assertEqual([],self.state.rows("SELECT * FROM reviews WHERE state='accepted'"))
        self.assertEqual('closed',self.state.rows('SELECT state FROM questions')[0]['state'])

    def test_N04_N11_policy_context_builder_bound_without_coverage_or_private_metadata(self):
        from school_notes.agents import Agent
        from school_notes.common import Window
        for name,text in (('AGENTS.md','Owner learner rules'),('PROFILE.md','Learner level'),('instructions/school-notes.md','Original privacy policy')):
            target=self.repo/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
        policies=Supervisor.trusted_policy(self.repo)
        self.assertEqual({'AGENTS.md','PROFILE.md','instructions/school-notes.md'},{p['logical_path'] for p in policies})
        config=json.loads((fixture.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable
        agent=Agent(config,self.state,None,Window());job={'id':1,'revision_seq':1,'payload':{'worktree':str(self.repo)}}
        envelope={'job_id':1,'revision_seq':1,'inputs':[],'trusted_policy':policies}
        codex=agent.build_command(job,'candidate',envelope,self.repo,self.root/'job','fixed role',1)
        self.assertIn('project_doc_max_bytes=0',codex['argv']);self.assertIn('project_doc_fallback_filenames=[]',codex['argv'])
        import tomllib
        table=tomllib.loads(next(arg for arg in codex['argv'] if arg.startswith('permissions.school-notes=')))['permissions']['school-notes']['filesystem']
        self.assertNotIn(str(self.repo),table)
        self.assertEqual('write',table[':workspace_roots']['.'])
        self.assertEqual('deny',table[str(self.repo/'.git')])
        for phase in ('source_review:abcdef0123456789','review:abcdef0123456789','public_review:abcdef0123456789','external_review:abcdef0123456789'):
            command=agent.build_command(job,phase,envelope,self.root,self.root/'job','review rules',2)
            self.assertIn(str(self.repo),command['read_dirs']);self.assertTrue(Path(command['cwd']).is_relative_to(self.root/'job'))
            bound=json.loads((command['directory']/'input.json').read_text())
            self.assertEqual([],bound['inputs']);self.assertEqual(policies,bound['trusted_policy'])
            self.assertFalse(any('private-classify' in directory for directory in command['read_dirs']))

    def test_successful_finite_adapter_records_bound_read_dirs_without_runtime_attestation(self):
        from school_notes.agents import Agent
        from school_notes.common import Window
        config=json.loads((fixture.REPO/'packages/school-notes/config.example.json').read_text())['agents'];config['python']=sys.executable
        proof=self.root/'synthetic-proof.json';atomic_json(proof,{'synthetic_transport_only':True})
        agent=Agent(config,self.state,self.supervisor().lock,Window())
        (self.repo/'PROFILE.md').write_text('Trusted learner context')
        envelope={'job_id':1,'revision_seq':None,'phase':'candidate','inputs':[],'trusted_policy':Supervisor.trusted_policy(self.repo)}
        jobid=self.state.enqueue('ingest','student','successful-local-wrapper',{})
        self.assertEqual(1,jobid)
        response=self.root/'response.json';atomic_json(response,fixture.result(envelope))
        settings=agent.role_settings('codex')
        settings.update(evidence=str(proof),timeout=30,argv=[sys.executable,'-c',"import pathlib,sys;pathlib.Path(sys.argv[2]).write_bytes(pathlib.Path(sys.argv[1]).read_bytes());print('{' + chr(34) + 'type' + chr(34) + ':' + chr(34) + 'turn.completed' + chr(34) + '}')",str(response),'{result}'])
        with patch.object(agent,'_gate',return_value=settings):
            result,path=agent.call(self.state.job(jobid),'candidate',envelope,self.root,self.root/'job','synthetic finite wrapper')
        runtime=json.loads((path.parent/'runtime.json').read_text())
        self.assertEqual([str(self.repo)],runtime['read_dirs']);self.assertIsNone(runtime['resolved_model']);self.assertIsNone(runtime['resolved_effort'])
        self.assertEqual('complete',result['status']);self.assertEqual('complete',self.state.rows('SELECT state FROM attempts')[0]['state'])

    def test_N17_verified_and_explicitly_closed_effect_preserve_original_receipt(self):
        supervisor=self.supervisor();job=self.state.enqueue('public_release','student','manual-effects',{'base':'a'*40})
        for key,decision in (('asset','verified'),('dispatch','closed')):
            self.state.effect(job,'release-asset' if key=='asset' else 'dispatch','exact-target','b'*64,key)
            self.state.effect_state(key,'unknown',{'allocated_id':'retained'})
            current=self.state.rows('SELECT * FROM effects WHERE stable_key=?',(key,))[0]
            evidence={'effect':{k:current[k] for k in ('stable_key','job_id','kind','target','artifact_hash','external_id','receipt')},'observed_effect_sha256':digest(current),'source_head':'a'*40,'decision':decision,'external_id':'provider-exact-id','reason':'Owner verified provider identity/bytes or explicitly closes without success claim','closure_records':self.evidence_records()}
            admin.resolve_effect(supervisor,key,evidence)
            saved=self.state.rows('SELECT * FROM effects WHERE stable_key=?',(key,))[0]
            self.assertIn('allocated_id',json.loads(saved['receipt'])['previous_receipt'])
            if decision=='verified':
                result=self.state.perform_effect(saved,lambda e:self.fail('verified repeat'),lambda e:self.fail('verified reconcile'))
                self.assertEqual('provider-exact-id',result['external_id'])
            else:
                with self.assertRaises(Blocked):self.state.perform_effect(saved,lambda e:self.fail('closed repeat'),lambda e:None)

    def test_N18_unknown_effect_blocks_job_closure(self):
        supervisor=self.supervisor();jobid=self.state.enqueue('public_release','student','blocked-closure',{})
        effect=self.state.effect(jobid,'dispatch','target','hash','unknown-dispatch');self.state.effect_state(effect['stable_key'],'unknown')
        job=self.state.job(jobid);evidence={'job_id':jobid,'revision_seq':None,'base':None,'payload_sha256':digest(job['payload']),'reason':'manual','closure_records':self.evidence_records()}
        with self.assertRaises(Blocked):admin.close_job(supervisor,jobid,evidence)


class R2PublicTests(PublicR1Tests):
    def test_N16_github_gate_before_private_commit_and_all_chunks_recorded(self):
        supervisor,private,public,api=self.public_setup();self.config['review_chunk_items']=1
        self.run_public(supervisor,api);job=self.state.job(public);head=self.git('rev-parse','HEAD')
        self.state.approve(public,digest(job['payload']['public_proposal']))
        from school_notes import publication
        actual_run=publication.run
        def offline_run(argv,*args,**kwargs):
            if any('check-browser.mjs' in a for a in argv):return 'controlled browser fixture'
            return actual_run(argv,*args,**kwargs)
        with patch('school_notes.publication.Renderer',PublicRenderer),patch('school_notes.publication.GitHub',side_effect=Blocked('actual capability proof missing')),patch('school_notes.publication.run',offline_run):supervisor.run_once()
        self.assertEqual(head,self.git('rev-parse','HEAD'));self.assertFalse((self.repo/'publication/public.json').exists());self.assertEqual([],api.requests)
        self.state.update_job(public,'queued');api.complete=True;self.run_public(supervisor,api)
        final=self.state.job(public);self.assertEqual('complete',final['state'],final['error'])
        paths=final['payload']['public_review_paths'];self.assertGreater(len(paths),1)
        tracked=self.git('ls-files','docs/review').splitlines()
        for path in paths:
            name=f"docs/review/school-notes-{public}-public-{digest(path)[:16]}.json"
            self.assertIn(name,tracked);self.assertEqual(file_hash(path),file_hash(self.repo/name))
