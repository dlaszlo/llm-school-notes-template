"""Fresh project command-line setup, without home credentials or network calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class FreshCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root/'repo'
        self.repo.mkdir()
        (self.repo/'tools').mkdir()
        source = Path(__file__).resolve().parent.parent
        for f in ['learning_image.py', 'drive_media.py', 'drive_connect.py']:
            shutil.copyfile(source/'tools'/f, self.repo/'tools'/f)
        shutil.copyfile(source/'learning-images.example.json', self.repo/'learning-images.example.json')
        self.home = self.root/'empty-home'
        self.home.mkdir()
        self.env = {k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ['KEY', 'TOKEN', 'SECRET', 'HERMES'])}
        self.env.update(HOME=str(self.home), PYTHONDONTWRITEBYTECODE='1')

    def cli(self, *args, script='learning_image.py'):
        return subprocess.run([sys.executable, str(self.repo/'tools'/script), *args],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def test_unconfigured_commands_are_read_only_and_ignore_global_policy(self):
        old = self.home/'.config/school-media'
        old.mkdir(parents=True)
        (old/'active.json').write_text('{"requests": ["must never be used"]}')
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        for cmd in ['status', 'check']:
            r = self.cli(cmd)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)['state'], 'not-configured')
        self.assertEqual(sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')), before)
        self.assertFalse((self.home/'.hermes').exists())

    def test_default_policy_resolves_from_checkout_even_with_other_cwd(self):
        shutil.copyfile(self.repo/'learning-images.example.json', self.repo/'learning-images.json')
        r = self.cli('check')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(json.loads(r.stdout)['credential_available'])
        self.assertFalse(json.loads(r.stdout)['spending_enabled'])
        self.assertFalse((self.repo/'.learning-images-state').exists())
        r = self.cli('init-state')
        self.assertEqual(r.returncode, 0, r.stderr)
        ledger = self.repo/'.learning-images-state/ledger.json'
        before = ledger.read_bytes()
        self.assertEqual(self.cli('init-state').returncode, 0)
        self.assertEqual(ledger.read_bytes(), before)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_help_needs_no_credentials_or_agent_home(self):
        for script in ['drive_connect.py', 'drive_media.py', 'learning_image.py']:
            r = self.cli('--help', script=script)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertFalse((self.repo/'.drive-state').exists())
