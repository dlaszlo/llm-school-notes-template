"""Behavioral regression checks for shared-tool migration and divergence detection."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import book_index
import check_shared


class SharedToolsTest(unittest.TestCase):
    def test_checker_detects_drift_and_ignores_local_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            template, child = base / 'template', base / 'child'
            for root in (template, child):
                root.mkdir()
                (root / 'shared-files.json').write_text(json.dumps({'version': 'test', 'files': ['AGENTS.md']}))
                (root / 'AGENTS.md').write_text('same rules\n')
            (child / 'PROFILE.md').write_text('different learner\n')
            self.assertEqual(check_shared.compare(template, child)[1], [])
            (child / 'AGENTS.md').write_text('local drift\n')
            self.assertEqual(check_shared.compare(template, child)[1], ['Different shared file: AGENTS.md'])
            (child / 'AGENTS.md').unlink()
            self.assertEqual(check_shared.compare(template, child)[1], ['Missing shared file: AGENTS.md'])

    def test_checker_rejects_path_outside_repo(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'shared-files.json').write_text(json.dumps({'version': 'test', 'files': ['../private']}))
            with self.assertRaises(ValueError):
                check_shared.read_manifest(root)

    def test_offset_formats_remain_supported(self):
        for text, expected in [('printed-page offset: 4', 4), ('one less', 1), ('eggyel kisebb', 1)]:
            self.assertEqual(book_index.readme_offset(text), expected)

    def test_checked_readme_overrides_plausible_but_incomplete_toc(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / 'book_index.py'
            script.write_bytes(Path(book_index.__file__).read_bytes())
            config = Path(book_index.__file__).with_name('book-index.json')
            (root / 'book-index.json').write_bytes(config.read_bytes())
            book = root / 'book'; book.mkdir()
            toc = '<table>' + ''.join(f'<tr><td>Unverified {i}</td><td>{i}</td></tr>' for i in range(1, 7)) + '</table>'
            doc = '<!-- element:p001-e001 kind=heading page=1 -->\n# Tartalom\n' + toc + '\n'
            doc += ''.join(f'<!-- element:p{i:03}-e001 kind=text page={i} -->\nText\n' for i in range(2, 9))
            (book / 'document.md').write_text(doc)
            readme = '# Example\nprinted-page offset: 0\n| Checked lesson | 2-8 |\n'
            for flag in ('--readme', 'marker'):
                (book / 'README.md').write_text(readme + ('<!-- book-index: readme -->\n' if flag == 'marker' else ''))
                args = [sys.executable, str(script), str(book)] + ([flag] if flag == '--readme' else [])
                subprocess.run(args, check=True, capture_output=True)
                result = (book / 'index.md').read_text()
                self.assertIn('| Checked lesson | 2-8 |', result)
                self.assertNotIn('Unverified', result)
                self.assertEqual((book / 'document.md').read_text(), doc)


if __name__ == '__main__':
    unittest.main()
