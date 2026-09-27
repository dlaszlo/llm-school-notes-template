"""Regression checks for bounded evidence retrieval and source immutability."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import curriculum


class CurriculumTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "example"
        self.folder.mkdir()
        self.text = "<!-- element:p001-e001 kind=paragraph page=1 -->\n3.5.2.6.1 Statika\n\n<!-- element:p001-e002 kind=table page=1 -->\n<table><tr><th>Középszint</th><th>Emelt szint</th></tr><tr><td>Alap</td><td>Bizonyítás</td></tr></table>\n"
        (self.folder / "document.md").write_text(self.text)
        (self.folder / "manifest.json").write_text(json.dumps({"source": {"sha256": "example-pdf-hash", "pdf_pages": 1}, "run": {"run_id": "test"}}))
        (self.folder / "provenance.json").write_text(json.dumps({"source_sha256": "example-pdf-hash", "run_id": "test", "page_count": 1, "elements": [{"id": "p001-e001"}, {"id": "p001-e002"}]}))
        self.entry = {"id": "example", "title": "Example", "source_pdf_sha256": "example-pdf-hash", "files": {p.name: curriculum.digest(p) for p in self.folder.iterdir()}}
        (self.root / "catalog.json").write_text(json.dumps({"documents": [self.entry]}))
        self.root_patch = patch.object(curriculum, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.run_cli("build")

    def run_cli(self, *args):
        out = io.StringIO()
        with patch("sys.argv", ["curriculum.py", *args]), contextlib.redirect_stdout(out):
            curriculum.main()
        return out.getvalue()

    def test_complete_table_and_numeric_paragraph_navigation(self):
        index = (self.folder / "index.md").read_text()
        self.assertIn("3.5.2.6.1 Statika", index)
        result = self.run_cli("read", "--document", "example", "--element", "p001-e002")
        self.assertIn("<th>Középszint</th><th>Emelt szint</th>", result)
        self.assertIn("</table>", result)
        self.assertEqual((self.folder / "document.md").read_text(), self.text)

    def test_oversized_table_is_not_silently_truncated(self):
        with self.assertRaisesRegex(ValueError, "exceeds bound"):
            self.run_cli("read", "--document", "example", "--element", "p001-e002", "--max-chars", "20")

    def test_changed_source_and_stale_index_block_evidence_read(self):
        (self.folder / "index.md").write_text("stale\n")
        with self.assertRaisesRegex(ValueError, "Stale navigation"):
            self.run_cli("search", "--document", "example", "--query", "Statika")
        (self.folder / "document.md").write_text(self.text + "changed\n")
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            self.run_cli("build")

    def test_build_refuses_symlink_index_without_touching_target(self):
        target = self.root / "outside.md"
        target.write_text("untouched\n")
        index = self.folder / "index.md"
        index.unlink()
        index.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink index"):
            self.run_cli("build")
        self.assertEqual(target.read_text(), "untouched\n")

    def test_mixed_conversion_runs_are_rejected_even_with_fresh_hash(self):
        path = self.folder / "provenance.json"
        data = json.loads(path.read_text())
        data["run_id"] = "another-run"
        path.write_text(json.dumps(data))
        self.entry["files"]["provenance.json"] = curriculum.digest(path)
        with self.assertRaisesRegex(ValueError, "Mismatched conversion runs"):
            curriculum.checked(self.entry)

    def test_symlink_parent_is_rejected(self):
        alias = self.root / "parent-link"
        alias.symlink_to(self.root, target_is_directory=True)
        with patch.object(curriculum, "ROOT", alias):
            with self.assertRaisesRegex(ValueError, "symlink"):
                curriculum.catalog()

    def test_partial_read_keeps_hash_and_explicit_limit(self):
        result = self.run_cli("read", "--document", "example", "--element", "p001-e002", "--lines", "5:5")
        self.assertIn("PARTIAL", result)
        self.assertIn(self.entry["files"]["document.md"], result)
        with self.assertRaisesRegex(ValueError, "stay inside"):
            self.run_cli("read", "--document", "example", "--element", "p001-e002", "--lines", "1:5")


if __name__ == "__main__":
    unittest.main()
