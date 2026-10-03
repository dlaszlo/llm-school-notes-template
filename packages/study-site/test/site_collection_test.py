import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("collection", Path(__file__).resolve().parents[1] / "stage-site-collection.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CollectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def bundle(self, folder, base="/sample/", unsafe=False):
        path = self.root / folder
        path.mkdir()
        files = {"index.html": b"<h1>Lesson</h1>", "pdf/topic.pdf": b"%PDF-test"}
        if unsafe:
            files["../escaped.txt"] = b"private"
        record = {"schema": 1, "release": "r1", "base": base, "pages": 1, "pdfs": 1,
                  "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}
        files["release.json"] = json.dumps(record).encode()
        archive = path / "site.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        (path / "site.tar.gz.sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  site.tar.gz\n")
        return str(archive)

    def test_bootstrap_contains_no_lesson_and_separates_receipt(self):
        record = module.stage(self.root / "out", bootstrap=True)
        self.assertEqual(record["sources"], [])
        self.assertEqual(len(list((self.root / "out/site").iterdir())), 4)
        self.assertFalse((self.root / "out/site/staging-receipt.private.json").exists())
        self.assertIn("NOT PROVIDED", record["access_control"])

    def test_two_sites_preserve_bytes_and_paths(self):
        entries = [(self.bundle("a", "/a/"), "/a/", "r1", "A <notes>"),
                   (self.bundle("b", "/b/"), "/b/", "r1", "B")]
        record = module.stage(self.root / "out", entries)
        self.assertEqual((self.root / "out/site/a/pdf/topic.pdf").read_bytes(), b"%PDF-test")
        self.assertIn('href="/b/"', (self.root / "out/site/index.html").read_text())
        self.assertIn("A &lt;notes&gt;", (self.root / "out/site/index.html").read_text())
        self.assertEqual(len(record["sources"]), 2)

    def test_rejects_tampered_bundle_without_partial_output(self):
        archive = self.bundle("a")
        Path(archive).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            module.stage(self.root / "out", [(archive, "/sample/", "r1", "Sample")])
        self.assertFalse((self.root / "out").exists())

    def test_rejects_duplicate_and_traversal_bases(self):
        for bases in [("/a/", "/a/"), ("/../", "/b/")]:
            with self.assertRaises(ValueError):
                module.stage(self.root / "out", [("absent", base, "r1", "Sample") for base in bases])

    def test_rejects_archive_traversal(self):
        archive = self.bundle("a", unsafe=True)
        with self.assertRaisesRegex(ValueError, "Unsafe archive"):
            module.stage(self.root / "out", [(archive, "/sample/", "r1", "Sample")])
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_does_not_overwrite(self):
        module.stage(self.root / "out", bootstrap=True)
        with self.assertRaisesRegex(ValueError, "already exists"):
            module.stage(self.root / "out", bootstrap=True)


if __name__ == "__main__":
    unittest.main()
