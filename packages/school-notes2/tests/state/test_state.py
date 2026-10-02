import os
import subprocess
import sys

import pytest

from school_notes2.schemas import SchemaError
from school_notes2.state import phase
from school_notes2.state.lock import StudentLock


def test_task_roundtrip_and_open(tmp_path):
    task = phase.create(tmp_path, "benedek", "notes", "cron", "downloading")
    task.set_phase("downloaded", packages=["a"])
    again = phase.load(task.dir)
    assert again.phase == "downloaded" and again.get("packages") == ["a"]
    assert phase.open_task(tmp_path, "benedek", "notes").run_id == task.run_id
    task.set_phase("done")
    assert phase.open_task(tmp_path, "benedek", "notes") is None


def test_phase_schema_rejects_unknown_phase(tmp_path):
    task = phase.create(tmp_path, "barna", "notes", "cron", "prepared")
    task.data["phase"] = "bogus"
    with pytest.raises(SchemaError):
        task.save()


def test_newer_schema_is_refused(tmp_path):
    task = phase.create(tmp_path, "barna", "review", "cron", "prepared")
    task.data["schema"] = 99
    (task.dir / "phase.json").write_text(__import__("json").dumps(task.data))
    with pytest.raises(RuntimeError):
        phase.load(task.dir)


def test_lock_excludes_second_holder(tmp_path):
    first = StudentLock(tmp_path, "benedek")
    assert first.try_acquire("run")
    code = ("import sys; from pathlib import Path; from school_notes2.state.lock import StudentLock;"
            f"sys.exit(0 if StudentLock(Path({str(tmp_path)!r}), 'benedek').try_acquire('chat') else 3)")
    assert subprocess.run([sys.executable, "-c", code]).returncode == 3
    assert first.holder()["kind"] == "run"
    first.release()
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_lock_is_inherited_by_children(tmp_path):
    lock = StudentLock(tmp_path, "barna")
    assert lock.try_acquire("finish")
    assert os.get_inheritable(lock.fd)
    lock.release()
