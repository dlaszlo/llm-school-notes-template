"""Small offline manual-mode regressions; synthetic provider/auth, no native proof."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from school_notes import cli
from school_notes.agents import Agent
from school_notes.common import Blocked, RunLock, Window, atomic_json, digest
from school_notes.drive import DriveAPI, ReadOnlyDriveAPI
from school_notes.pipeline import Supervisor
from school_notes.state import State
from test_agent_transport import PROVIDER


class ManualTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.state=State.initialize(self.root/'state/db.sqlite',{'alpha':{'observed_sha':'a'*40},'beta':{'observed_sha':'b'*40}})
        self.addCleanup(self.state.close)
        with self.state.db:self.state.db.execute('UPDATE observations SET ack_sha=observed_sha')
        self.config={'agents':{},'lock_file':str(self.root/'state/run.lock'),'jobs_dir':str(self.root/'jobs'),'learners':{'alpha':{},'beta':{}}}
        self.lock=Mock()

    def supervisor(self,manual=True,push=None):
        return Supervisor(self.config,self.state,self.lock,Mock(side_effect=AssertionError('no Drive call')),
            owner_supervised=manual,supervised_learner='alpha' if manual else None,allow_private_push_job=push)

    def job(self,learner='alpha',phase='commit',kind='ingest'):
        n=self.state.enqueue(kind,learner,f'{learner}-{phase}-{kind}',{'build':'retained-preview','commit':'c'*40,'base':('a' if learner=='alpha' else 'b')*40})
        self.state.update_job(n,phase=phase);return n

    def observers(self,supervisor):
        for name in ('preflight_owner','observe_git','observe_drive'):
            setattr(supervisor,name,Mock())
        self.state.meta('drive-baseline:alpha','complete')

    def test_manual_cli_requires_explicit_learner_reader_and_exact_push_job(self):
        invalid=[['sync','--owner-supervised'],['run-once','--owner-supervised','--learner','alpha'],
                 ['sync','--drive-reader-config','/synthetic/reader'],
                 ['run-once','--allow-private-push','--learner','alpha','--job','1'],
                 ['run-once','--owner-supervised','--allow-private-push','--learner','alpha','--drive-reader-config','/synthetic/reader']]
        with patch.object(cli,'load',side_effect=AssertionError('invalid flags must stop before config')):
            for argv in invalid:
                with self.subTest(argv=argv),patch('sys.stderr',new=io.StringIO()):
                    self.assertEqual(cli.main(['--config','/synthetic/config',*argv]),2)
        args=cli.parser().parse_args(['--config','/synthetic/config','run-once','--owner-supervised','--learner','alpha','--job','7','--allow-private-push','--drive-reader-config','/synthetic/reader'])
        self.assertEqual(args.job,7)
        with patch('sys.stderr',new=io.StringIO()),self.assertRaises(SystemExit):
            cli.parser().parse_args(['--config','/synthetic/config','finalize-external','1','--owner-supervised'])

    def test_protected_agent_session_cannot_select_owner_supervised_authority(self):
        with patch.object(cli,'load',return_value={}),patch.object(cli.session,'verify',return_value={'learner':'alpha'}), \
             patch.object(cli.session,'Admission',side_effect=AssertionError('no admission')),patch('sys.stderr',new=io.StringIO()):
            self.assertEqual(cli.main(['--config','/synthetic/config','sync','--owner-supervised','--learner','alpha',
                                      '--drive-reader-config','/synthetic/reader']),2)

    def test_supervised_stops_after_commit_before_push_and_preserves_preview(self):
        n=self.job();self.state.update_job(n,'running');s=self.supervisor();s.push=Mock(side_effect=AssertionError('no push'))
        s.finalize=Mock(side_effect=lambda job:self.state.update_job(n,phase='push'))
        s.process(n)
        kept=self.state.job(n);self.assertEqual((kept['state'],kept['phase']),('owner_wait','push'))
        self.assertEqual(kept['payload']['build'],'retained-preview');self.assertTrue(kept['payload']['owner_supervised'])
        s.push.assert_not_called()

    def test_generic_resume_and_background_default_cannot_release_fence(self):
        n=self.job(phase='push');self.supervisor().process(n);self.state.admin_resume(n)
        normal=self.supervisor(False);self.observers(normal);normal.process=Mock(side_effect=AssertionError('no default process'))
        normal.run_once(learners=['alpha'])
        self.assertEqual(self.state.job(n)['state'],'owner_wait');normal.process.assert_not_called()
        direct=self.supervisor(False);direct.push=Mock(side_effect=AssertionError('no default push'))
        direct.process(n);direct.push.assert_not_called()

    def test_exact_retained_job_push_resumes_once_then_pauses_family_output(self):
        n=self.job(phase='push');self.supervisor().process(n)
        s=self.supervisor(push=n);self.observers(s)
        s.push=Mock(side_effect=lambda job:self.state.update_job(n,phase='family_output'))
        with patch('school_notes.pipeline.Archive',side_effect=AssertionError('no family output')):
            s.run_once(learners=['alpha'],job_id=n)
        s.push.assert_called_once();job=self.state.job(n)
        self.assertEqual((job['state'],job['phase']),('owner_wait','family_output'))
        with self.assertRaisesRegex(Blocked,'exact retained'):
            s.run_once(learners=['alpha'],job_id=n)
        self.state.admin_resume(n);normal=self.supervisor(False);self.observers(normal)
        normal.process=Mock(side_effect=AssertionError('no downstream processing'))
        normal.run_once(learners=['alpha']);normal.process.assert_not_called()

    def test_push_override_cannot_choose_an_unretained_or_different_job(self):
        n=self.job(phase='push');s=self.supervisor(push=n)
        with self.assertRaisesRegex(Blocked,'exact retained'):s.run_once(learners=['alpha'],job_id=n)
        with self.assertRaisesRegex(Blocked,'exact selected'):s.run_once(learners=['alpha'])

    def test_supervised_only_one_learner_and_no_public_external_jobs(self):
        s=self.supervisor();other=self.job('beta')
        with self.assertRaisesRegex(Blocked,'another learner'):s.process(other)
        with self.assertRaisesRegex(Blocked,'explicit learner'):s.run_once(learners=['alpha','beta'])
        with self.assertRaisesRegex(Blocked,'explicit learner'):s.sync(['beta'])
        for kind in ('public_release','external_change_review'):
            n=self.job(kind=kind)
            with self.assertRaisesRegex(Blocked,'private ingest'):s.process(n)
            self.assertNotIn('owner_supervised',self.state.job(n)['payload'])

    def test_manual_scope_run_does_not_process_other_learners_or_public_jobs(self):
        own=self.job(phase='push');other=self.job('beta',phase='push');public=self.job(kind='public_release')
        s=self.supervisor();self.observers(s)
        s.run_once(learners=['alpha'])
        self.assertEqual(self.state.job(own)['state'],'owner_wait')
        self.assertEqual(self.state.job(other)['state'],'queued');self.assertEqual(self.state.job(public)['state'],'queued')

    def test_crash_after_manual_admission_keeps_background_fence(self):
        n=self.job(phase='candidate');s=self.supervisor()
        s.candidate=Mock(side_effect=RuntimeError('synthetic interruption'))
        with self.assertRaises(RuntimeError):s.process(n)
        self.assertTrue(self.state.job(n)['payload']['owner_supervised'])
        s=self.supervisor(False);s.candidate=Mock(side_effect=AssertionError('no default candidate'))
        s.process(n);s.candidate.assert_not_called();self.assertEqual(self.state.job(n)['state'],'owner_wait')

    def test_initial_inventory_gate_is_not_marked_complete_by_supervision(self):
        s=self.supervisor();s.observe_drive=Mock(side_effect=AssertionError('baseline is unfinished'))
        with patch('school_notes.pipeline.Git') as git:
            git.return_value.head.return_value='a'*40;git.return_value.git.return_value='a'*40
            s.observe_git=Mock();s.sync(['alpha'])
        self.assertNotEqual(self.state.meta('drive-baseline:alpha'),'complete');s.observe_drive.assert_not_called()
        reasons=[self.state.job(x['id'])['error'] for x in self.state.rows("SELECT id FROM jobs WHERE kind='runtime_block'")]
        self.assertTrue(any('initial Drive inventory unfinished' in reason for reason in reasons))

    def test_supervised_real_synthetic_provider_works_without_proof_file(self):
        worker=self.root/'worker';worker.mkdir();provider=self.root/'fake-provider.py';provider.write_text(PROVIDER)
        n=self.job(phase='candidate');job=self.state.job(n);envelope={'job_id':n,'revision_seq':None,'inputs':[]}
        cfg={'python':sys.executable,'codex':{'model':'gpt-6.1-sol','effort':'high','evidence':str(self.root/'absent-proof'),
             'timeout':5,'argv':[sys.executable,str(provider),'{input}','{result}','success',str(self.root/'started'),digest(envelope)]}}
        with RunLock(self.root/'state/run.lock') as lock:
            agent=Agent(cfg,self.state,lock,Window(),owner_supervised=True)
            result,path=agent.call(job,'candidate',envelope,worker,self.root/'attempts','synthetic test')
            self.assertEqual(result['status'],'complete')
            runtime=json.loads((path.parent/'runtime.json').read_text())
            self.assertTrue(runtime['owner_supervised']);self.assertIsNone(runtime['proof_path']);self.assertIsNone(runtime['proof_sha256'])
            with self.assertRaises(FileNotFoundError):Agent(cfg,self.state,lock,Window())._gate('codex')
            bad=copy.deepcopy(cfg);bad['codex']['model']='wrong'
            with self.assertRaisesRegex(Blocked,'fixed model'):Agent(bad,self.state,lock,Window(),owner_supervised=True)._gate('codex')

    def test_bad_result_binding_still_rejected_in_supervised_provider(self):
        worker=self.root/'worker';worker.mkdir();provider=self.root/'fake-provider.py';provider.write_text(PROVIDER)
        n=self.job(phase='candidate');envelope={'job_id':n,'revision_seq':None,'inputs':[]}
        cfg={'python':sys.executable,'codex':{'model':'gpt-6.1-sol','effort':'high','evidence':str(self.root/'absent-proof'),
             'timeout':5,'argv':[sys.executable,str(provider),'{input}','{result}','success',str(self.root/'started'),'wrong-binding']}}
        with RunLock(self.root/'state/run.lock') as lock:
            with self.assertRaisesRegex(Blocked,'hash mismatch'):
                Agent(cfg,self.state,lock,Window(),owner_supervised=True).call(self.state.job(n),'candidate',envelope,worker,self.root/'attempts','synthetic')

    def test_drive_manual_proof_bypass_keeps_reader_scope_and_no_write_surface(self):
        tool=self.root/'fake-drive.py';tool.write_text('''from pathlib import Path
SCOPE='https://www.googleapis.com/auth/drive.file'
class Refused(Exception):pass
class ApiError(Exception):pass
class Drive:
 def __init__(self,directory):
  if (directory/'scope').read_text()!=SCOPE:raise Refused('synthetic scope mismatch')
 def request(self,*args):return (200,{}, {'id':'synthetic'})
''')
        writer=self.root/'writer';writer.mkdir();(writer/'scope').write_text('https://www.googleapis.com/auth/drive.file')
        reader=self.root/'reader';reader.mkdir();(reader/'scope').write_text('https://www.googleapis.com/auth/drive.readonly')
        missing=self.root/'absent-proof'
        api=DriveAPI(tool,writer,missing,reader_config={'scope':'https://www.googleapis.com/auth/drive.readonly','config_dir':str(reader)},owner_supervised=True)
        self.assertIsInstance(api.input_reader,ReadOnlyDriveAPI)
        self.assertEqual(api.input_reader.metadata('file'),{'id':'synthetic'})
        self.assertEqual(api.module.SCOPE,'https://www.googleapis.com/auth/drive.file')
        self.assertEqual(api.input_reader.module.SCOPE,'https://www.googleapis.com/auth/drive.readonly')
        with self.assertRaisesRegex(Blocked,'every mutation'):api.input_reader.request('POST','https://www.googleapis.com/drive/v3/files')
        with self.assertRaisesRegex(Blocked,'authentication'):ReadOnlyDriveAPI(tool,writer,None,owner_supervised=True)
        with self.assertRaises(FileNotFoundError):DriveAPI(tool,writer,missing)
        with self.assertRaises(FileNotFoundError):ReadOnlyDriveAPI(tool,reader,missing)


if __name__=='__main__':unittest.main()
