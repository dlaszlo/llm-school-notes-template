"""Owner-selected Astra stays limited to the existing supervised author role."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

from school_notes.agents import Agent
from school_notes.common import Blocked, private_dir


class SupervisedAstraTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.jobs = private_dir(root / 'jobs')
        self.repo = private_dir(root / 'repo')
        (self.repo / '.git').mkdir()
        package = Path(__file__).resolve().parents[1]
        self.base = json.loads((package / 'config.example.json').read_text())['agents']
        self.base['python'] = sys.executable
        self.config = copy.deepcopy(self.base)
        writer = self.config['codex']
        writer['model'] = 'gpt-6-astra'
        writer['argv'][writer['argv'].index('--model') + 1] = 'gpt-6-astra'
        writer['definition'] = str(package / 'agents/implementer-astra.md')

    def agent(self, manual=True):
        return Agent(self.config, None, None, None, owner_supervised=manual)

    def test_manual_astra_gate_and_launch_keep_high_and_original_permissions(self):
        agent = self.agent()
        self.assertEqual(agent._gate('codex')['model'], 'gpt-6-astra')
        job = {'id': 1, 'revision_seq': None, 'payload': {'worktree': str(self.repo)}}
        envelope = {'job_id': 1, 'revision_seq': None, 'inputs': []}
        args = agent.build_command(job, 'candidate', envelope, self.repo, self.jobs, 'fixture', 1)['argv']
        self.assertEqual(args[args.index('--model') + 1], 'gpt-6-astra')
        self.assertIn('model_reasoning_effort="high"', args)
        self.assertIn('approval_policy="never"', args)
        permission = next(x for x in args if x.startswith('permissions.school-notes='))
        self.assertIn(str(self.repo / '.git') + '"="deny"', permission)
        self.assertIn('network={enabled=false}', permission)

    def test_astra_cannot_enable_default_or_background_role(self):
        with self.assertRaisesRegex(Blocked, 'fixed model/effort'):
            self.agent(False)._gate('codex')
        with self.assertRaisesRegex(Blocked, 'fixed model/effort'):
            self.agent(False).role_settings('codex')

    def test_wrong_effort_model_or_definition_is_rejected(self):
        valid = copy.deepcopy(self.config)
        for effort in ('xhigh', 'max'):
            self.config = copy.deepcopy(valid)
            self.config['codex']['effort'] = effort
            with self.assertRaisesRegex(Blocked, 'fixed model/effort'):
                self.agent()._gate('codex')
        self.config = copy.deepcopy(valid)
        self.config['codex']['model'] = 'gpt-6-sol'
        with self.assertRaisesRegex(Blocked, 'fixed model/effort'):
            self.agent()._gate('codex')
        self.config = copy.deepcopy(valid)
        self.config['codex']['definition'] = str(Path(valid['codex']['definition']).with_name('implementer.md'))
        with self.assertRaisesRegex(Blocked, 'role definition'):
            self.agent()._gate('codex')

    def test_existing_sol_and_opus_contracts_are_preserved(self):
        for manual in (False, True):
            agent = Agent(self.base, None, None, None, owner_supervised=manual)
            self.assertEqual(agent.role_settings('codex')['model'], 'gpt-6.1-sol')
            self.assertEqual(agent.role_settings('claude')['model'], 'claude-opus-5-5')
        self.config['claude']['model'] = 'gpt-6-astra'
        with self.assertRaisesRegex(Blocked, 'fixed model/effort'):
            self.agent().role_settings('claude')

    def test_thirty_minutes_only_for_supervised_astra_author(self):
        for model, phase, timeout, accepted in (
            ('gpt-6-astra', 'candidate', 1800, True),
            ('gpt-6-astra', 'candidate', 1801, False),
            ('gpt-6-astra', 'candidate', 0, False),
            ('gpt-6.1-sol', 'candidate', 1800, False),
            ('claude-opus-5-5', 'source_review', 1800, False),
        ):
            with self.subTest(model=model, phase=phase, timeout=timeout):
                agent = self.agent()
                agent._gate = Mock(return_value={'model': model, 'timeout': timeout})
                agent.window = Mock()
                agent.window.require.side_effect = RuntimeError('window reached')
                if accepted:
                    with self.assertRaisesRegex(RuntimeError, 'window reached'):
                        agent.call({}, phase, {}, self.repo, self.jobs, '')
                    agent.window.require.assert_called_once_with(1805)
                else:
                    with self.assertRaisesRegex(Blocked, 'agent timeout'):
                        agent.call({}, phase, {}, self.repo, self.jobs, '')
                    agent.window.require.assert_not_called()


if __name__ == '__main__':
    unittest.main()
