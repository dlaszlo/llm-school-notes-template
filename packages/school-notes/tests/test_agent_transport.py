"""Real subprocess synthetic provider/layout tests, not native sandbox proofs.

Gate mocking is explicit: these tests cannot accept production capabilities.
The worker writes decoy attempt/events.log while its actual stdout goes to the
supervisor stream. Original vulnerable Agent.call bytes fail these regressions.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from school_notes.agents import Agent, validate_result
from school_notes.common import Blocked, QuotaBlocked, RunLock, TimedOut, Window, atomic_json, file_hash, private_dir
from school_notes.state import State

PROVIDER = '''import json,sys,time
from pathlib import Path
envelope=json.loads(Path(sys.argv[1]).read_text())
result_path=Path(sys.argv[2]);mode=sys.argv[3]
Path(sys.argv[4]).write_text('synthetic provider actually started')
response={'job_id':envelope['job_id'],'revision_seq':envelope['revision_seq'],'input_hash':sys.argv[5],
 'status':'complete','file_changes':[],'coverage':[],'evidence':['synthetic subprocess only'],
 'uncertainties':[],'classification':[],'source_context':None,'manifest_proposal':None,'review':None}
result_path.write_text(json.dumps(response))
decoy=result_path.parent/'events.log'
if mode in ('success','claude-success'):
 decoy.write_text('{"type":"turn.failed","message":"quota_exceeded decoy"}\\n')
 (result_path.parent/'events.log.stderr').write_text('usage limit reached decoy')
else:
 decoy.write_text('{"type":"turn.completed"}\\n')
if mode=='timeout':time.sleep(10)
if mode.startswith('claude'):
 wrapper={'type':'result','subtype':'success' if mode=='claude-success' else 'error','is_error':mode!='claude-success',
  'modelUsage':{'claude-opus-5-5':{}},'structured_output':response}
 print(json.dumps(wrapper))
elif mode=='success':print('{"type":"turn.completed"}')
elif mode=='quota':print('{"type":"error","message":"quota_exceeded real stdout"}')
else:
 print('{"type":"turn.failed","message":"actual transport failure"}')
 if mode=='stderr-quota':
  print('usage limit reached real stderr',file=sys.stderr)
  sys.exit(1)
 if mode=='process-failure':sys.exit(7)
sys.stdout.flush()
# Rewrite after actual stdout was flushed. On the original implementation the
# decoy and supervisor stream are the same file, so the forged bytes win.
if mode=='claude-failure':
 decoy.write_text(json.dumps({'type':'result','subtype':'success','is_error':False,'modelUsage':{'claude-opus-5-5':{}},'structured_output':response})+'\\n')
else:
 decoy.write_text('{"type":"turn.failed","message":"quota_exceeded decoy"}\\n' if mode in ('success','claude-success','forged-quota') else '{"type":"turn.completed"}\\n')
'''


class ProtectedTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = State.initialize(self.root / 'state/state.sqlite', {})
        self.addCleanup(self.state.db.close)
        self.worker = private_dir(self.root / 'workspace')
        self.attempts = private_dir(self.root / 'jobs')
        self.provider = self.root / 'synthetic-provider.py'; self.provider.write_text(PROVIDER)
        self.marker = self.root / 'provider-started'
        self.proof = self.root / 'synthetic-only-proof.json'; atomic_json(self.proof, {'synthetic_only': True})

    def call(self, mode, *, cwd=None, suffix=None, lock_path=None):
        job_id = self.state.enqueue('ingest', 'synthetic', mode, {})
        job = self.state.job(job_id)
        envelope = {'job_id': job_id, 'revision_seq': None, 'inputs': []}
        from school_notes.common import digest
        role = 'claude' if mode.startswith('claude') else 'codex'
        config = {'python': sys.executable}
        with RunLock(lock_path or self.root / 'state/run.lock') as lock:
            agent = Agent(config, self.state, lock, Window())
            settings = Agent({role: {'model': 'claude-opus-5-5' if role == 'claude' else 'gpt-6.1-sol',
                                      'effort': 'high'}}, self.state, lock, Window()).role_settings(role)
            settings.update(evidence=str(self.proof), timeout=1 if mode == 'timeout' else 10,
                argv=[sys.executable, str(self.provider), '{input}', '{result}', mode,
                      str(self.marker), digest(envelope), *(suffix or [])])
            with patch.object(agent, '_gate', return_value=settings):
                return agent.call(job, 'review' if role == 'claude' else 'candidate', envelope,
                                  cwd or self.worker, self.attempts, 'synthetic transport test')

    def metadata(self):
        attempt = next(self.attempts.glob('attempt-*'))
        value = json.loads((attempt / 'transport.json').read_text())
        stdout, stderr = (Path(value[name]['path']) for name in ('stdout', 'stderr'))
        self.assertFalse(stdout.is_relative_to(attempt))
        self.assertFalse(stdout.is_relative_to(self.worker))
        self.assertFalse(stdout.is_relative_to(attempt / 'tmp'))
        self.assertEqual(json.loads((stdout.parent / 'transport.json').read_text()), value)
        self.assertEqual(value['stdout']['sha256'], file_hash(stdout))
        self.assertEqual(value['stderr']['sha256'], file_hash(stderr))
        self.assertEqual(stdout.stat().st_mode & 0o777, 0o600)
        self.assertEqual(stderr.stat().st_mode & 0o777, 0o600)
        self.assertEqual(stdout.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(value['stdout']['status'], 'retained')
        self.assertEqual(value['directory'], str(attempt))
        self.assertEqual(value['result_path'], str(attempt / 'result.json'))
        self.assertEqual(value['attempt_id'], self.state.rows('SELECT id FROM attempts')[0]['id'])
        return attempt, stdout, stderr

    def test_forged_attempt_success_cannot_override_failed_actual_stdout(self):
        with self.assertRaisesRegex(Blocked, 'failed/error event'): self.call('failure')
        attempt, stdout, _ = self.metadata()
        self.assertIn('turn.completed', (attempt / 'events.log').read_text())
        self.assertIn('actual transport failure', stdout.read_text())
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'failed')
        self.assertTrue(self.marker.exists())

    def test_genuine_success_ignores_forged_failure_and_quota_decoy(self):
        result, _ = self.call('success')
        self.assertEqual(result['status'], 'complete')
        attempt, stdout, _ = self.metadata()
        self.assertIn('quota_exceeded decoy', (attempt / 'events.log').read_text())
        self.assertEqual(stdout.read_text().strip(), '{"type":"turn.completed"}')
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'complete')

    def test_real_stdout_quota_marker_still_uses_protected_log(self):
        with self.assertRaises(QuotaBlocked): self.call('quota')
        _, stdout, _ = self.metadata()
        self.assertIn('quota_exceeded real stdout', stdout.read_text())
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'quota')

    def test_real_stderr_quota_marker_still_uses_protected_log(self):
        with self.assertRaises(QuotaBlocked): self.call('stderr-quota')
        _, _, stderr = self.metadata()
        self.assertIn('usage limit reached real stderr', stderr.read_text())
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'quota')

    def test_timeout_retains_protected_artifact_paths_and_attempt_state(self):
        with self.assertRaises(TimedOut): self.call('timeout')
        self.metadata()
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'timeout')

    def test_claude_failure_cannot_be_replaced_by_decoy_success(self):
        with self.assertRaisesRegex(Blocked, 'wrapper is not successful'): self.call('claude-failure')
        attempt, stdout, _ = self.metadata()
        decoy = json.loads((attempt / 'events.log').read_text())
        self.assertEqual(decoy['subtype'], 'success'); self.assertIs(decoy['is_error'], False)
        self.assertEqual(set(decoy['modelUsage']), {'claude-opus-5-5'})
        validate_result(decoy['structured_output'], json.loads((attempt / 'input.json').read_text()))
        self.assertIn('"is_error": true', stdout.read_text())

    def test_claude_success_uses_same_protected_transport(self):
        self.assertEqual(self.call('claude-success')[0]['status'], 'complete')
        _, stdout, _ = self.metadata()
        self.assertIn('claude-opus-5-5', stdout.read_text())

    def test_cwd_containing_log_root_rejects_before_provider(self):
        with self.assertRaisesRegex(Blocked, 'overlaps worker scope'):
            self.call('overlap', cwd=self.root)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.state.rows('SELECT * FROM attempts'))
        self.assertFalse((self.root / 'state/agent-logs').exists())

    def test_configured_absolute_write_grant_rejects_before_provider(self):
        table = 'permissions.school-notes={filesystem={"' + str(self.root) + '"="write"}}'
        with self.assertRaisesRegex(Blocked, 'overlaps worker scope'):
            self.call('grant-overlap', suffix=['-c', table])
        self.assertFalse(self.marker.exists())

    def test_unknown_symbolic_write_scope_rejects_before_provider(self):
        with self.assertRaisesRegex(Blocked, 'unknown configured agent write scope'):
            self.call('unknown-grant', suffix=['-c', 'permissions.school-notes={filesystem={":unknown"="write"}}'])
        self.assertFalse(self.marker.exists())

    def test_symlink_cwd_alias_to_log_ancestor_rejects(self):
        alias = self.root / 'worker-alias'; alias.symlink_to(self.root / 'state', target_is_directory=True)
        with self.assertRaisesRegex(Blocked, 'overlaps worker scope'):
            self.call('cwd-alias', cwd=alias)
        self.assertFalse(self.marker.exists())

    def test_existing_log_root_symlink_is_neither_followed_nor_chmodded(self):
        outside = self.root / 'outside'; outside.mkdir(mode=0o755)
        (self.root / 'state/agent-logs').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(Blocked, 'symlink'):
            self.call('log-root-alias')
        self.assertFalse(self.marker.exists())
        self.assertEqual(outside.stat().st_mode & 0o777, 0o755)
        self.assertEqual(list(outside.iterdir()), [])

    def test_existing_nonprivate_log_root_is_rejected_without_chmod(self):
        path = self.root / 'state/agent-logs'; path.mkdir(mode=0o755)
        with self.assertRaisesRegex(Blocked, 'private and owner controlled'):
            self.call('public-log-root')
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)
        self.assertFalse(self.marker.exists())

    def test_lock_ancestor_symlink_is_rejected_without_outside_log_creation(self):
        alias = self.root / 'lock-alias'; alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(Blocked, 'symlink in protected agent transport path'):
            self.call('lock-alias', lock_path=alias / 'state/run.lock')
        self.assertFalse((self.root / 'state/agent-logs').exists())
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.state.rows('SELECT * FROM attempts'))

    def test_real_nonquota_failure_ignores_forged_attempt_quota_marker(self):
        with self.assertRaisesRegex(Blocked, 'failed/error event') as caught:
            self.call('forged-quota')
        self.assertNotIsInstance(caught.exception, QuotaBlocked)
        attempt, _, _ = self.metadata()
        self.assertIn('quota_exceeded decoy', (attempt / 'events.log').read_text())
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'failed')

    def test_metadata_copy_failure_does_not_mask_actual_process_failure(self):
        from school_notes import agents
        original = agents.atomic_json
        def fail_sidecar(path, value):
            if Path(path).name == 'transport.json' and value['stdout']['status'] != 'pending':
                raise OSError('synthetic sidecar failure')
            return original(path, value)
        with patch.object(agents, 'atomic_json', fail_sidecar):
            with self.assertRaisesRegex(Blocked, r'child process failed \(7\)') as caught:
                self.call('process-failure')
        self.assertEqual(caught.exception.transport_metadata_error, 'OSError')
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'failed')
        self.assertTrue(list((self.root / 'state/agent-logs').glob('*/events.log')))

    def test_metadata_failure_after_successful_provider_cannot_leave_complete_attempt(self):
        from school_notes import agents
        original = agents.atomic_json
        def fail_sidecar(path, value):
            if Path(path).name == 'transport.json' and value['stdout']['status'] != 'pending':
                raise OSError('synthetic sidecar failure')
            return original(path, value)
        with patch.object(agents, 'atomic_json', fail_sidecar):
            with self.assertRaisesRegex(OSError, 'synthetic sidecar failure'):
                self.call('success')
        self.assertEqual(self.state.rows('SELECT state FROM attempts')[0]['state'], 'failed')

    def test_symlink_and_fifo_logs_metadata_never_reads_target(self):
        root = private_dir(self.root / 'metadata')
        target = self.root / 'never-read-secret'; target.write_text('sentinel')
        log = root / 'events.log'; log.symlink_to(target)
        os.mkfifo(str(log) + '.stderr')
        with patch('school_notes.agents.os.open', side_effect=AssertionError('nonordinary must not be opened')):
            metadata = Agent.transport_metadata(log)
        self.assertEqual(metadata['stdout']['status'], 'nonordinary-not-read')
        self.assertEqual(metadata['stderr']['status'], 'nonordinary-not-read')


if __name__ == '__main__':
    unittest.main()
