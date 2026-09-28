import subprocess
import tempfile
import unittest
from pathlib import Path
from install_hermes_images import install


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.hermes = self.root / 'hermes'
        self.source = self.repo / 'integrations/hermes/learning-images/SKILL.md'
        self.source.parent.mkdir(parents=True)
        self.source.write_text('versioned skill\n')
        for args in [('init', '-q'), ('add', '.'), ('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')]:
            subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True)
        self.target = self.hermes / 'skills/learning-images/SKILL.md'

    def test_fresh_install_repeat_and_check(self):
        self.assertEqual(install(self.repo, self.hermes), 'linked')
        self.assertEqual(self.target.resolve(), self.source)
        self.assertEqual(install(self.repo, self.hermes), 'already linked')
        self.assertEqual(install(self.repo, self.hermes, check=True), 'already linked')
        self.assertEqual(sorted(p.relative_to(self.hermes).as_posix() for p in self.hermes.rglob('*') if p.is_file()), ['skills/learning-images/SKILL.md'])

    def test_check_does_not_install(self):
        with self.assertRaises(ValueError):
            install(self.repo, self.hermes, check=True)
        self.assertFalse(self.hermes.exists())

    def test_existing_content_is_preserved(self):
        self.target.parent.mkdir(parents=True)
        self.target.write_text('local skill\n')
        with self.assertRaises(ValueError):
            install(self.repo, self.hermes)
        self.assertEqual(self.target.read_text(), 'local skill\n')

    def test_uncommitted_source_is_rejected(self):
        self.source.write_text('uncommitted change\n')
        with self.assertRaises(ValueError):
            install(self.repo, self.hermes)
        self.assertFalse(self.hermes.exists())

    def test_other_symlink_is_preserved(self):
        self.target.parent.mkdir(parents=True)
        other = self.root / 'missing'
        self.target.symlink_to(other)
        with self.assertRaises(ValueError):
            install(self.repo, self.hermes)
        self.assertEqual(self.target.readlink(), other)


if __name__ == '__main__':
    unittest.main()
