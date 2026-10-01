"""Offline preservation, race, effect-recovery and private pilot regression tests."""
from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from school_notes.agents import Agent, CHECKS, RESULT_SCHEMA, validate_result
from school_notes.common import Blocked, Busy, RunLock, TimedOut, Window, atomic_json, digest, file_hash, private_dir, run
from school_notes.drive import Archive, FOLDER, InventoryChanged, capture, check_classification, inventory, semantic_metadata, snapshot_signature, supported
from school_notes.pipeline import Supervisor
from school_notes.report import pdf_bytes, write as report
from school_notes.state import State
from school_notes.verify import Git, Renderer, manifest_with_hashes, review_gate

REPO = Path(__file__).resolve().parents[3]
PNG = b"\x89PNG\r\n\x1a\n"  # signature tests only; pilot supplies a real Pillow image


class FakeDrive:
    def __init__(self):
        self.items = {"ready": dict(id="ready", name="Kész", mimeType=FOLDER, parents=["incoming"])}
        self.data = {}
        self.downloads = []
        self.writes = []
        self.fail_page = None
        self.mutate_after_download = None
        self.counter = 0

    def add(self, identity, parent, name, content=None, description=""):
        mime = FOLDER if content is None else "image/png" if name.endswith(".png") else "application/pdf"
        self.items[identity] = dict(id=identity, name=name, mimeType=mime, parents=[parent], description=description, version="1")
        if content is not None:
            import hashlib
            self.data[identity] = content
            self.items[identity].update(size=str(len(content)), md5Checksum=hashlib.md5(content).hexdigest())
        return self.items[identity]

    def metadata(self, identity):
        return copy.deepcopy(self.items[identity])

    def list_page(self, parent, token=None):
        if self.fail_page == (parent, token):
            raise Blocked("permission denied: not an empty folder")
        children = sorted([copy.deepcopy(f) for f in self.items.values() if f.get("parents") == [parent]], key=lambda f: f["id"])
        index = int(token or "0")
        return children[index:index + 1], str(index + 1) if index + 1 < len(children) else None

    def download(self, identity, path):
        self.downloads.append(identity)
        Path(path).write_bytes(self.data[identity])
        os.chmod(path, 0o600)
        if self.mutate_after_download:
            self.mutate_after_download(self)
            self.mutate_after_download = None

    def reserve_id(self):
        self.counter += 1
        return "reserved-" + str(self.counter)

    def create_folder(self, identity, name, parent, key):
        self.writes.append(("folder", identity))
        self.add(identity, parent, name)
        self.items[identity]["appProperties"] = {"school_notes_effect": key}

    def upload(self, identity, path, mime, parent, key, sha, *, name=None):
        self.writes.append(("upload", identity))
        self.add(identity, parent, name or Path(path).name, Path(path).read_bytes())
        self.items[identity]["mimeType"] = mime
        self.items[identity]["appProperties"] = {"school_notes_effect": key, "sha256": sha}

    def reconcile(self, effect, folder=False):
        identity = effect["external_id"]
        if identity not in self.items:
            return {"absent": True}
        meta = self.items[identity]
        if meta["parents"] != [effect["target"]] or meta.get("appProperties", {}).get("school_notes_effect") != effect["stable_key"]:
            raise Blocked("ownership mismatch")
        if not folder:
            import hashlib
            if hashlib.sha256(self.data[identity]).hexdigest() != effect["artifact_hash"]:
                raise Blocked("readback hash mismatch")
        return {"verified": True, "external_id": identity, "sha256": effect["artifact_hash"], "target": effect["target"]}


def result(envelope):
    return {"job_id": envelope["job_id"], "revision_seq": envelope["revision_seq"], "input_hash": digest(envelope), "status": "complete",
            "file_changes": [], "coverage": [f["path"] for f in envelope["inputs"]], "evidence": ["verified input coverage"]+(["comparison_context_sha256="+envelope["comparison_context_hash"]] if envelope.get("comparison_context") else []), "uncertainties": [],
            "classification": [], "source_context": None, "manifest_proposal": None,
            "review": {k: True for k in ("content", "source_coverage", "privacy", "provenance", "curriculum", "reading_order", "formulae", "banners", "visual", "all_pdf_pages", "public_privacy", "asset_rights")}}


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = State.initialize(self.root / "state.sqlite", {"student": {"observed_sha": "a" * 40}})

    def tearDown(self):
        self.state.close()
        self.temp.cleanup()

    def manifest(self, context="A", sha="a" * 64):
        return {"files": [{"id": "file", "sha256": sha}], "metadata_hash": digest(context)}


class StateTests(Base):
    def test_exclusive_init_and_missing_corrupt_database(self):
        before = file_hash(self.root / "state.sqlite")
        with self.assertRaises(FileExistsError):
            State.initialize(self.root / "state.sqlite", {})
        self.assertEqual(before, file_hash(self.root / "state.sqlite"))
        with self.assertRaises(Blocked):
            State(self.root / "missing.sqlite")
        (self.root / "broken.sqlite").write_bytes(b"not a database")
        with self.assertRaises(Blocked):
            State(self.root / "broken.sqlite")
        row = self.state.rows("SELECT * FROM observations")[0]
        self.assertIsNone(row["ack_sha"])
        self.assertEqual("baseline_pending", row["state"])

    def test_aba_and_fast_updates_use_sequence_not_unique_hash(self):
        for context in ("A", "B", "A"):
            self.state.revision("student", "package", self.manifest(context))
        revisions = self.state.rows("SELECT * FROM revisions ORDER BY seq")
        self.assertEqual([1, 2, 3], [r["seq"] for r in revisions])
        self.assertEqual(revisions[0]["metadata_hash"], revisions[2]["metadata_hash"])
        jobs = self.state.rows("SELECT * FROM jobs ORDER BY id")
        self.assertEqual(["superseded", "superseded", "queued"], [j["state"] for j in jobs])
        self.assertEqual(["ingest", "ingest", "ingest"], [j["kind"] for j in jobs])
        self.assertEqual(3, len({j["stable_key"] for j in jobs}))
        _, seq, changed = self.state.revision("student", "package", self.manifest("A"))
        self.assertEqual((3, False), (seq, changed))
        self.assertFalse(self.state.current(self.state.job(jobs[0]["id"])))

    def test_baseline_requires_selection_and_new_package_is_normal(self):
        self.state.revision("student", "existing", self.manifest(), baseline=True)
        self.assertEqual([], self.state.rows("SELECT * FROM jobs"))
        job_id = self.state.select_baseline("student", "existing")
        self.assertEqual("queued", self.state.job(job_id)["state"])
        with self.assertRaises(Blocked):
            self.state.select_baseline("student", "existing")
        self.state.revision("student", "new", self.manifest())
        self.assertEqual(2, len(self.state.rows("SELECT * FROM jobs")))

    def test_required_nonnull_external_key_deduplication(self):
        key = "external-review:" + digest({"repo": "x", "base": "a", "head": "b", "hashes": {"p": "h"}})
        first = self.state.enqueue("external_change_review", "student", key, {})
        second = self.state.enqueue("external_change_review", "student", key, {})
        self.assertEqual(first, second)
        with self.assertRaises(Blocked):
            self.state.enqueue("external_change_review", "student", "", {})

    def test_authorization_cannot_be_source_answer_and_hash_must_match(self):
        job_id = self.state.enqueue("release", "student", "release:target:hash", {"public_proposal": {"pages": ["p"]}})
        sha = digest(self.state.job(job_id)["payload"]["public_proposal"])
        q = self.state.question(job_id, "authorization", "public", "approve", sha)
        for origin in ("drive-txt", "drive-description", "private-git", "admin-content"):
            with self.assertRaises(Blocked):
                self.state.answer(q, "yes", origin)
        with self.assertRaises(Blocked):
            self.state.approve(job_id, "b" * 64)
        self.state.approve(job_id, sha)
        self.assertEqual("direct-vm-admin", self.state.rows("SELECT * FROM questions")[0]["origin"])

    def test_stale_content_answer_requires_reconciliation(self):
        self.state.revision("student", "p", self.manifest("A"))
        job = self.state.rows("SELECT * FROM jobs")[0]
        q = self.state.question(job["id"], "content", "context", "who authored source")
        self.state.answer(q, "other learner, catch-up", "drive-description")
        self.state.revision("student", "p", self.manifest("B"))
        saved=self.state.rows("SELECT * FROM questions")[0]
        self.assertEqual("stale", saved["state"])
        self.assertEqual("other learner, catch-up",saved["answer"])
        with self.assertRaises(Blocked):self.state.answer(q,"late correction","admin-content")

    def test_unknown_effect_no_blind_repeat_and_exact_reconciliation(self):
        effect = self.state.effect(None, "upload", "target", "a" * 64, "upload:key")
        calls = []
        def crash(e):
            calls.append(e)
            raise OSError("crash after remote write")
        with self.assertRaises(OSError):
            self.state.perform_effect(effect, crash, lambda e: None)
        effect = self.state.rows("SELECT * FROM effects")[0]
        with self.assertRaises(Blocked):
            self.state.perform_effect(effect, crash, lambda e: None)
        self.assertEqual(1, len(calls))
        receipt = self.state.perform_effect(effect, crash, lambda e: {"verified": True, "external_id": "remote", "sha256": "a" * 64})
        self.assertTrue(receipt["verified"])
        self.assertEqual(1, len(calls))
        with self.assertRaises(Blocked):
            self.state.effect(None, "upload", "other-target", "a" * 64, "upload:key")

    def test_crash_recovery_preserves_effects_and_candidate_phase(self):
        job_id = self.state.enqueue("ingest", "student", "ingest:s:p:1", {})
        self.state.update_job(job_id, "running", "push")
        effect = self.state.effect(job_id, "push", "remote", "a" * 40, "push:key")
        self.state.effect_state(effect["stable_key"], "inflight")
        self.state.recover()
        self.assertEqual("unknown", self.state.rows("SELECT * FROM effects")[0]["state"])
        self.assertEqual(("queued", "push"), (self.state.job(job_id)["state"], self.state.job(job_id)["phase"]))


class CaptureTests(Base):
    def setUp(self):
        super().setUp()
        self.drive = FakeDrive()
        self.drive.add("package", "ready", "bundle")
        self.drive.add("one", "package", "01.png", PNG + b"one")
        self.drive.add("two", "package", "02.pdf", b"%PDF-test")

    def test_all_paginated_recursive_pages_required(self):
        self.drive.add("nested", "package", "slides")
        self.drive.add("three", "nested", "03.png", PNG + b"three")
        self.assertEqual(6, len(inventory(self.drive, "ready")))
        self.drive.fail_page = ("package", "1")
        with self.assertRaises(Blocked):
            capture(self.drive, "package", self.root / "capture", reserve=0)
        self.assertEqual([], self.drive.downloads)
        self.assertEqual([], self.drive.writes)

    def test_late_page_rejects_capture_before_archive(self):
        self.drive.mutate_after_download = lambda api: api.add("late", "package", "03.png", PNG)
        with self.assertRaises(InventoryChanged):
            capture(self.drive, "package", self.root / "capture", reserve=0)
        self.assertEqual([], self.drive.writes)

    def test_supported_signature_and_disk_reserve_fail_closed(self):
        p = self.root / "x.png"
        p.write_bytes(b"not PNG")
        with self.assertRaises(Blocked):
            supported(p, "image/png")
        p.write_bytes(PNG)
        with self.assertRaises(Blocked):
            supported(p, "image/heic")
        with self.assertRaises(Blocked):
            capture(self.drive, "package", self.root / "capture", reserve=10**20)
        self.assertEqual([], self.drive.downloads)

    def test_unchanged_and_metadata_only_capture_reuses_original_bytes(self):
        first = capture(self.drive, "package", self.root / "one", reserve=0)
        self.assertEqual(2, len(self.drive.downloads))
        second = capture(self.drive, "package", self.root / "two", reserve=0, previous=first)
        self.assertEqual(2, len(self.drive.downloads))
        self.assertEqual([f["local"] for f in first["files"]], [f["local"] for f in second["files"]])
        self.drive.items["package"]["description"] = "Catch-up notebook from another learner"
        self.drive.items["package"]["version"] = "2"
        third = capture(self.drive, "package", self.root / "three", reserve=0, previous=second)
        self.assertEqual(2, len(self.drive.downloads))
        self.assertNotEqual(second["metadata_hash"], third["metadata_hash"])
        self.state.revision("student", "package", second)
        self.state.update_job(self.state.rows('SELECT id FROM jobs')[0]['id'],'complete')
        self.state.revision("student", "package", third)
        self.assertEqual("metadata_update", self.state.rows("SELECT * FROM jobs ORDER BY id")[-1]["kind"])

    def test_pure_rename_vs_interpretation_order(self):
        items = inventory(self.drive, "package")
        sha = semantic_metadata(items)
        self.drive.items["one"]["name"] = "01-renamed.png"
        self.assertEqual(sha, semantic_metadata(inventory(self.drive, "package")))
        self.drive.items["one"]["name"] = "99.png"
        self.assertNotEqual(sha, semantic_metadata(inventory(self.drive, "package")))

    def test_mixed_book_classification_blocks_whole_package_before_write(self):
        manifest = capture(self.drive, "package", self.root / "capture", reserve=0)
        package, seq, _ = self.state.revision("student", "package", manifest)
        job = self.state.job(self.state.rows("SELECT * FROM jobs")[0]["id"])
        classified = [{"id": f["id"], "sha256": f["sha256"], "source_class": "notebook" if index == 0 else "book_suspect", "uncertain": False} for index, f in enumerate(manifest["files"])]
        with self.assertRaises(Blocked):
            Archive(self.drive, self.state, "archive").package(job, classified)
        self.assertEqual([], self.drive.writes)

    def test_archive_nested_paths_idempotent_and_readback_receipts(self):
        self.drive.add("nested", "package", "slides")
        self.drive.add("three", "nested", "03.png", PNG + b"three")
        manifest = capture(self.drive, "package", self.root / "capture", reserve=0)
        self.state.revision("student", "package", manifest)
        job = self.state.job(self.state.rows("SELECT * FROM jobs")[0]["id"])
        classified = [{"id": f["id"], "sha256": f["sha256"], "source_class": "teacher_learn", "uncertain": False} for f in manifest["files"]]
        archive = Archive(self.drive, self.state, "archive")
        receipts = archive.package(job, classified)
        writes = len(self.drive.writes)
        self.assertTrue(all(r["verified"] for r in receipts))
        self.assertEqual(receipts, archive.package(job, classified))
        self.assertEqual(writes, len(self.drive.writes))

    def test_multiple_ready_roots_do_not_consume_uploading(self):
        self.drive.add("incoming", "none", "incoming")
        self.drive.add("uploading", "incoming", "Feltöltés")
        self.drive.add("do-not-consume", "uploading", "secret.png", PNG)
        self.drive.add("ready-two", "incoming", "Kész-math")
        self.drive.add("package-two", "ready-two", "another-package")
        self.drive.add("other-file", "package-two", "01.pdf", b"%PDF-other")
        config = {"learners": {"student": {"inputs": [{"ready_id": "ready", "subject_slug": "science", "source_role": "notebook"},
                                                      {"ready_id": "ready-two", "subject_slug": "math", "source_role": "teacher_learn"}]}},
                  "captures_dir": str(self.root / "captures"), "reserve_bytes": 0, "agents": {}}
        supervisor = Supervisor(config, self.state, None, lambda learner: self.drive)
        supervisor.observe_drive("student", baseline=True)
        self.assertNotIn("do-not-consume", self.drive.downloads)
        self.assertEqual(2, len(self.state.rows("SELECT * FROM packages")))
        manifests = [json.loads(r["manifest"]) for r in self.state.rows("SELECT * FROM revisions")]
        self.assertEqual({"science", "math"}, {m["input_context"]["subject_slug"] for m in manifests})
        self.assertEqual("complete", self.state.meta("drive-baseline:student"))


class AdapterTests(Base):
    def test_inventory_total_run_window_stops_before_transport(self):
        drive = FakeDrive()
        window = Window(seconds=0)
        with self.assertRaises(Blocked):
            inventory(drive, "ready", window.require)
        self.assertEqual([], drive.downloads)
    def test_schema_has_no_unconstrained_objects(self):
        def visit(node):
            if isinstance(node, dict):
                typ = node.get("type")
                if typ == "object" or isinstance(typ, list) and "object" in typ:
                    self.assertIs(node.get("additionalProperties"), False)
                    self.assertEqual(set(node.get("required", [])), set(node.get("properties", {})))
                for child in node.values():
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)
        visit(RESULT_SCHEMA)

    def test_manifest_json_string_supervisor_validation(self):
        envelope = {"job_id": 1, "revision_seq": 1, "inputs": []}
        good = result(envelope)
        good["manifest_proposal"] = json.dumps({"title": "Notes", "mode": "private-preview", "base": "/", "pages": [{"path": "wiki/index.md"}]})
        self.assertIsInstance(validate_result(good, envelope)["manifest_proposal"], dict)
        bad = result(envelope)
        bad["manifest_proposal"] = '{"mode":"private-preview","pages":[],"execute":"publish"}'
        with self.assertRaises(Blocked):
            validate_result(bad, envelope)

    def test_actual_finite_cli_wrappers_require_event_and_content_success(self):
        envelope = {"job_id": 1, "revision_seq": None, "inputs": []}
        response = result(envelope)
        response_file = self.root / "response.json"
        atomic_json(response_file, response)
        script = self.root / "fake-provider.py"
        script.write_text("import json,sys\nfrom pathlib import Path\nresult=json.loads(Path(sys.argv[1]).read_text())\nrole=sys.argv[2]\nif role=='codex':\n Path(sys.argv[3]).write_text(json.dumps(result))\n print(json.dumps({'type':'turn.completed'}))\nelse:\n print(json.dumps({'type':'result','subtype':'success','is_error':False,'modelUsage':{'claude-opus-5-5':{}},'structured_output':result}))\n")
        lock_file = self.root / "run.lock"
        uv_lock = self.root / "uv.lock"
        uv_lock.write_text("verified offline test runtime\n")
        config = {"python": sys.executable, "uv_lock": str(uv_lock)}
        for role, model in (("codex", "gpt-6.1-sol"), ("claude", "claude-opus-5-5")):
            argv = [sys.executable, str(script), str(response_file), role, "{result}"]
            proof_path = self.root / (role + "-proof.json")
            atomic_json(proof_path, {**{k: True for k in CHECKS}, "model": model, "effort": "high", "argv_hash": digest(argv), "python": sys.executable, "uv_lock_sha256": file_hash(uv_lock), "role_sha256":Agent({role:{'model':model,'effort':'high'}},self.state,None,Window()).role_settings(role)['role_sha256']})
            config[role] = {"model": model, "effort": "high", "argv": argv, "evidence": str(proof_path), "timeout": 2}
        with RunLock(lock_file) as lock:
            agent = Agent(config, self.state, lock, Window())
            job_id = self.state.enqueue("ingest", "student", "adapter-test", {})
            job = self.state.job(job_id)
            envelope["job_id"] = job_id
            response = result(envelope)
            atomic_json(response_file, response)
            self.assertEqual("complete", agent.call(job, "classify", envelope, self.root, self.root / "jobs", "synthetic test")[0]["status"])
            self.assertEqual("complete", agent.call(job, "review", envelope, self.root, self.root / "jobs", "synthetic test")[0]["status"])
            script.write_text("import json\nprint(json.dumps({'type':'result','subtype':'success','is_error':False}))\n")
            with self.assertRaises(Blocked):
                agent.call(job, "review", envelope, self.root, self.root / "jobs", "malformed content")

    def test_strict_hash_bound_content_and_no_false_wrapper_success(self):
        envelope = {"job_id": 1, "revision_seq": 2, "inputs": []}
        good = result(envelope)
        self.assertEqual(good, validate_result(good, envelope))
        for changed in (dict(good, input_hash="b" * 64), dict(good, job_id=9), dict(good, coverage={}), dict(good, extra="x")):
            with self.assertRaises(Blocked):
                validate_result(changed, envelope)

    def test_incomplete_runtime_proof_prevents_any_agent_call(self):
        proof = self.root / "proof.json"
        atomic_json(proof, {"model": "gpt-6.1-sol", "effort": "high", "requested_model_only": True})
        adapter = Agent({"codex": {"model": "gpt-6.1-sol", "effort": "high", "evidence": str(proof)}}, self.state, None, Window())
        with self.assertRaises(Blocked):
            adapter._gate("codex")
        adapter.config["codex"]["model"] = "gpt-6-sol"
        with self.assertRaises(Blocked):
            adapter._gate("codex")

    def test_process_stdin_closed_and_timeout_kills_child_group(self):
        output = run([sys.executable, "-c", "import sys; print(len(sys.stdin.read()))"], self.root)
        self.assertEqual("0", output.strip())
        pidfile = self.root / "child.pid"
        code = "import subprocess,time; from pathlib import Path; p=subprocess.Popen(['sleep','30']); Path(" + repr(str(pidfile)) + ").write_text(str(p.pid)); time.sleep(30)"
        with self.assertRaises(TimedOut):
            run([sys.executable, "-c", code], self.root, timeout=0.2)
        pid = int(pidfile.read_text())
        status = Path(f"/proc/{pid}/stat")
        self.assertTrue(not status.exists() or status.read_text().split()[2] == "Z")

    def test_lock_survives_parent_close_until_inherited_child_exits(self):
        lock_path = self.root / "run.lock"
        with RunLock(lock_path) as lock:
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(.5)"], pass_fds=(lock.fd,))
        try:
            with self.assertRaises(Busy):
                with RunLock(lock_path):
                    pass
        finally:
            child.wait()
        with RunLock(lock_path):
            pass

    def test_every_pdf_page_hash_required_in_review(self):
        envelope = {"inputs": [{"path": "page-1", "sha256": "1"}, {"path": "page-2", "sha256": "2"}], "job_id": 1, "revision_seq": 1}
        reviewed = result(envelope)
        review_gate(reviewed, envelope)
        reviewed["coverage"].pop()
        with self.assertRaises(Blocked):
            review_gate(reviewed, envelope)

    def test_change_only_pdf_reports(self):
        status = {"generated": "time1", "jobs": [], "effects": [], "questions": [], "observations": []}
        one = report(status, self.root / "reports")
        status["generated"] = "time2"
        self.assertEqual(one, report(status, self.root / "reports"))
        self.assertTrue(one.read_bytes().startswith(b"%PDF-"))
        status["effects"] = [{"stable_key": "status-pdf:student:hash", "kind": "drive-upload", "state": "verified"}]
        self.assertEqual(one, report(status, self.root / "reports"))
        status["jobs"] = [{"id": 1, "learner": "student", "kind": "ingest", "state": "blocked", "phase": "classify", "error": "question"}]
        self.assertNotEqual(one, report(status, self.root / "reports"))


class FakeAgents:
    def __init__(self, state, lock):
        self.state, self.lock, self.calls = state, lock, []
        self.contexts = []

    def call(self, job, phase, envelope, cwd, directory, instructions):
        self.calls.append(phase)
        response = result(envelope)
        if phase == "classify":
            response["classification"] = [{"id": f["id"], "sha256": f["sha256"], "source_class": "notebook", "uncertain": False} for f in envelope["inputs"] if f["kind"] == "source"]
            catch_up = any("Catch-up" in f["description"] for f in envelope["private_metadata"]["descriptions"])
            response["source_context"] = {"subject_slug": "math", "educational_context": "Catch-up from another notebook" if catch_up else "Notebook",
                                          "source_author": "other" if catch_up else "unknown", "purpose": "catch_up" if catch_up else "learn"}
        if phase == "candidate":
            self.contexts.append(envelope)
            root = Path(cwd)
            (root / "wiki/math/lesson.md").write_text("# Lesson\n\n" + envelope["context"]["educational_context"] + "\n")
            (root / "wiki/math/source.md").write_text("# Source summary\ncontent_sha256: " + envelope["inputs"][0]["sha256"] + "\n")
            (root / "wiki/log.md").write_text("# Log\nrevision " + str(job["revision_seq"]) + "\n")
            changes = Git(root, self.lock).changes(job["payload"]["base"],sources=job["payload"].get("git_sources",[]))
            response["file_changes"] = [{"path": n, "sha256": sha} for n, sha in changes.items() if not n.startswith("sources/")]
            response['manifest_proposal']=json.loads((root/'publication/pilot.json').read_text())
            if not any(p['path']=='wiki/math/lesson.md' for p in response['manifest_proposal']['pages']):
                response['manifest_proposal']['pages'].append({'path':'wiki/math/lesson.md'})
        attempt = private_dir(Path(directory) / ("fake-" + str(len(self.calls))))
        path = attempt / "result.json"
        atomic_json(path, response)
        return response, path


class FakeRenderer:
    def __init__(self, config, lock, window):
        pass

    def build(self, repo, manifest, directory):
        directory = private_dir(directory)
        build = private_dir(directory / "build")
        private_dir(build / "site/pdf")
        (build / "site/pdf/math.pdf").write_bytes(b"%PDF-pilot")
        (build / "site/index.html").write_text("<h1>Lesson</h1>")
        page = directory / "page-1.png"
        page.write_bytes(PNG)
        return build, [{"path": str(page), "sha256": file_hash(page), "kind": "pdf-page"}]

    artifacts = staticmethod(Renderer.artifacts)


class PilotTests(Base):
    def test_versioned_status_upload_is_change_only(self):
        from school_notes.cli import main
        self.config["drive_tool"] = "unused"
        self.config["learners"]["student"]["status_id"] = "status"
        self.config["learners"]["student"].update(drive_config_dir=str(self.root), drive_evidence="unused")
        with patch("school_notes.cli.load", return_value=self.config), patch("school_notes.cli.DriveAPI", return_value=self.drive), patch.object(Supervisor, "run_once", lambda s, **kwargs: s.status()), patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(0, main(["--config", "unused", "run-once"]))
            writes = len(self.drive.writes)
            self.assertEqual(1, writes)
            self.assertEqual(0, main(["--config", "unused", "run-once"]))
            self.assertEqual(writes, len(self.drive.writes))

    def test_partial_renderer_crash_preserved_then_fresh_bounded_attempt(self):
        class CrashingRenderer(FakeRenderer):
            count = 0
            def build(self, repo, manifest, directory):
                self.__class__.count += 1
                if self.__class__.count == 1:
                    partial = private_dir(Path(directory) / "build")
                    (partial / "partial.txt").write_text("retained partial render")
                    raise Blocked("synthetic renderer crash")
                return super().build(repo, manifest, directory)
        with RunLock(self.config["lock_file"]) as lock, patch("school_notes.pipeline.Renderer", CrashingRenderer):
            supervisor = Supervisor(self.config, self.state, lock, lambda learner: self.drive)
            supervisor.agents = FakeAgents(self.state, lock)
            supervisor.run_once()
            job = self.state.job(self.state.rows("SELECT * FROM jobs")[0]["id"])
            self.assertEqual(("blocked", "render"), (job["state"], job["phase"]))
            old = supervisor.job_dir(job) / "render-0-0/build/partial.txt"
            self.state.update_job(job["id"], "queued")
            supervisor.run_once()
            job = self.state.job(job["id"])
            self.assertEqual("complete", job["state"], job["error"])
            self.assertEqual(1, job["payload"]["render_attempt"])
            self.assertEqual("retained partial render", old.read_text())
    def setUp(self):
        Base.setUp(self)
        self.repo = self.root / "repo"
        self.remote = self.root / "remote.git"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.repo)], check=True, capture_output=True)
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True).strip()
        self.git = git
        git("config", "user.name", "Test owner")
        git("config", "user.email", "owner@example.test")
        for directory in ("wiki/math", "sources", "publication", "tools"):
            (self.repo / directory).mkdir(parents=True, exist_ok=True)
        (self.repo / "wiki/math/index.md").write_text("# Math\n")
        (self.repo / "wiki/log.md").write_text("# Log\n")
        (self.repo / "tools/subjects.json").write_text("{}\n")
        (self.repo / "publication/pilot.json").write_text(json.dumps({"title": "Notes", "mode": "private-preview", "base": "/", "pages": [{"path": "wiki/math/index.md", "sha256": file_hash(self.repo / "wiki/math/index.md")}]}))
        git("add", ".")
        git("commit", "-m", "Baseline")
        git("remote", "add", "origin", str(self.remote))
        git("push", "-u", "origin", "main")
        head = git("rev-parse", "HEAD")
        with self.state.db:
            self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=?,state='complete'", (head, head))
        self.drive = FakeDrive()
        self.drive.add("package", "ready", "Math notebook")
        from PIL import Image
        image = io.BytesIO()
        Image.new("RGB", (8, 8), "white").save(image, format="PNG")
        self.drive.add("file", "package", "01.png", image.getvalue())
        self.config = {"learners": {"student": {"repo": str(self.repo), "inputs": [{"ready_id": "ready", "subject_slug": "math", "source_role": "notebook"}], "archive_id": "archive", "output_id": "output"}},
                       "state_db": str(self.root / "state.sqlite"), "lock_file": str(self.root / "run.lock"), "captures_dir": str(self.root / "captures"),
                       "jobs_dir": str(self.root / "jobs"), "reports_dir": str(self.root / "reports"), "reserve_bytes": 0, "worktree_estimate_bytes": 0,
                       "agents": {"python": sys.executable}, "prepare_photo": str(REPO / "tools/prepare_photo.py"), "renderer": {},
                       "git_identity": {"name": "Test owner", "email": "owner@example.test"}}
        self.state.meta("drive-baseline:student", "complete")

    def test_private_pilot_unchanged_and_metadata_context_update(self):
        with RunLock(self.config["lock_file"]) as lock, patch("school_notes.pipeline.Renderer", FakeRenderer):
            supervisor = Supervisor(self.config, self.state, lock, lambda learner: self.drive)
            agents = FakeAgents(self.state, lock)
            supervisor.agents = agents
            supervisor.run_once()
            jobs = self.state.rows("SELECT * FROM jobs")
            self.assertEqual("complete", jobs[0]["state"], jobs[0].get("error"))
            self.assertEqual("done", jobs[0]["phase"])
            self.assertEqual("not_requested", self.state.job(jobs[0]["id"])["payload"]["public_state"])
            first_calls = len(agents.calls)
            original_writes = len([e for e in self.state.rows("SELECT * FROM effects") if e["kind"] == "drive-upload" and e["stable_key"].startswith("archive-file:")])
            downloads = len(self.drive.downloads)
            supervisor.run_once()
            self.assertEqual(first_calls, len(agents.calls))
            self.assertEqual(downloads, len(self.drive.downloads))
            self.drive.items["package"]["description"] = "Catch-up notebook from another learner"
            self.drive.items["package"]["version"] = "2"
            supervisor.run_once()
            jobs = self.state.rows("SELECT * FROM jobs ORDER BY id")
            self.assertEqual(["ingest", "metadata_update"], [j["kind"] for j in jobs])
            self.assertEqual("complete", jobs[-1]["state"], jobs[-1].get("error"))
            self.assertEqual("other", agents.contexts[-1]["context"]["source_author"])
            self.assertEqual("catch_up", agents.contexts[-1]["context"]["purpose"])
            self.assertEqual("unknown", agents.contexts[-1]["previous_context"]["source_author"])
            self.assertNotIn("private_metadata", agents.contexts[-1])
            self.assertEqual(original_writes, len([e for e in self.state.rows("SELECT * FROM effects") if e["kind"] == "drive-upload" and e["stable_key"].startswith("archive-file:")]))
            self.assertEqual(1, len(list((self.repo / "sources").rglob("*.png"))))
            self.assertEqual(downloads, len(self.drive.downloads))

    def test_source_pdf_pages_staged_inside_job_and_missing_page_blocks_classification(self):
        self.drive.data["file"] = pdf_bytes(["source page " + str(i) for i in range(100)])
        import hashlib
        self.drive.items["file"].update(name="01.pdf", mimeType="application/pdf", size=str(len(self.drive.data["file"])), md5Checksum=hashlib.md5(self.drive.data["file"]).hexdigest())
        self.config["renderer"] = {"pdfinfo": "/usr/bin/pdfinfo", "pdftoppm": "/usr/bin/pdftoppm"}
        with RunLock(self.config["lock_file"]) as lock:
            supervisor = Supervisor(self.config, self.state, lock, lambda learner: self.drive)
            supervisor.observe_drive("student")
            job = self.state.job(self.state.rows("SELECT * FROM jobs")[0]["id"])
            supervisor.prepare(job)
            job = self.state.job(job["id"])
            inputs = supervisor.source_inputs(job["payload"]["manifest"])
            pages = [f for f in inputs if f["kind"] == "source-pdf-page"]
            self.assertEqual(3, len(pages))
            self.assertTrue(all(Path(f["path"]).is_relative_to(supervisor.job_dir(job)) for f in inputs))
            self.assertTrue(all(file_hash(f["path"]) == f["sha256"] for f in inputs))
            fake = FakeAgents(self.state, lock)
            original_call = fake.call
            def missing_page(*args, **kwargs):
                response, path = original_call(*args, **kwargs)
                response["coverage"].pop()
                return response, path
            fake.call = missing_page
            supervisor.agents = fake
            self.state.update_job(job["id"], "running", "classify")
            supervisor.process(job["id"])
            self.assertEqual("question_wait", self.state.job(job["id"])["state"])
            self.assertEqual([], self.drive.writes)

    def test_commit_receipt_crash_recovers_without_duplicate_commit(self):
        with RunLock(self.config["lock_file"]) as lock, patch("school_notes.pipeline.Renderer", FakeRenderer):
            supervisor = Supervisor(self.config, self.state, lock, lambda learner: self.drive)
            supervisor.agents = FakeAgents(self.state, lock)
            original = self.state.effect_state
            crashed = False
            def crash_receipt(key, state, receipt=None, external_id=None):
                nonlocal crashed
                if key.startswith("private-commit:") and state == "verified" and not crashed:
                    crashed = True
                    raise OSError("synthetic crash after git commit before receipt")
                return original(key, state, receipt, external_id)
            with patch.object(self.state, "effect_state", crash_receipt):
                supervisor.run_once()
            job = self.state.job(self.state.rows("SELECT * FROM jobs")[0]["id"])
            self.assertEqual(("blocked", "commit"), (job["state"], job["phase"]))
            commit_before = Git(job["payload"]["worktree"]).head()
            self.state.update_job(job["id"], "queued")
            supervisor.run_once()
            job = self.state.job(job["id"])
            self.assertEqual("complete", job["state"], job["error"])
            self.assertEqual(commit_before, job["payload"]["commit"])

    def test_push_receipt_crash_reconciles_exact_remote_commit(self):
        with RunLock(self.config["lock_file"]) as lock, patch("school_notes.pipeline.Renderer", FakeRenderer):
            supervisor = Supervisor(self.config, self.state, lock, lambda learner: self.drive)
            supervisor.agents = FakeAgents(self.state, lock)
            original = Git.git
            crashed = False
            def crash_after_push(git, *args, **kwargs):
                nonlocal crashed
                output = original(git, *args, **kwargs)
                if args and args[0] == "push" and not crashed:
                    crashed = True
                    raise OSError("synthetic crash after successful push")
                return output
            with patch.object(Git, "git", crash_after_push):
                supervisor.run_once()
            job = self.state.job(self.state.rows("SELECT * FROM jobs")[0]["id"])
            self.assertEqual(("blocked", "push"), (job["state"], job["phase"]))
            self.state.update_job(job["id"], "queued")
            supervisor.run_once()
            job = self.state.job(job["id"])
            self.assertEqual("complete", job["state"], job["error"])
            self.assertTrue(job["payload"]["push_receipt"]["verified"])

    def test_dirty_and_divergent_checkout_preserved(self):
        git = Git(self.repo)
        (self.repo / "local.txt").write_text("unsaved work")
        with self.assertRaises(Blocked):
            git.inspect()
        self.assertEqual("unsaved work", (self.repo / "local.txt").read_text())
        (self.repo / "local.txt").unlink()
        (self.repo / "wiki/log.md").write_text("Local commit\n")
        self.git("add", ".")
        self.git("commit", "-m", "Local change")
        head = self.git("rev-parse", "HEAD")
        with self.assertRaises(Blocked):
            git.inspect()
        self.assertEqual(head, self.git("rev-parse", "HEAD"))

    def test_concurrent_protected_change_blocks_candidate(self):
        candidate = Git(self.repo)
        base = candidate.head()
        (self.repo / "PROFILE.md").write_text("Agent modified profile")
        with self.assertRaises(Blocked):
            candidate.changes(base)


if __name__ == "__main__":
    unittest.main()
