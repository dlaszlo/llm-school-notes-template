"""A blocking question (5.3) and a run of two ranges (5.2/2) end to end."""

import subprocess
import sys

from school_notes2.flows import chat, run as run_flow
from school_notes2.state import phase
from tests.e2e.test_run_e2e import HERE, jpeg, show, world  # noqa: F401 - shared fixture


def calls(ctx):
    log = ctx.notes_path.parent / "notes-writer-calls.log"
    return log.read_text().split() if log.exists() else []


def test_question_stops_cron_and_a_session_answers_it(world, monkeypatch):
    ctx, origin, drive, package = world
    monkeypatch.setenv("FAKE_WRITER", "question")
    assert run_flow.run(ctx) == 1
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    assert task.data["needs_owner"] and task.get("question")
    assert run_flow.run(ctx) == 0 and calls(ctx) == ["1/1"]       # cron keeps away
    answers = iter(["f"])
    assert chat._settle(ctx, task, ask=lambda _: next(answers), say=lambda _: None)
    task = phase.load(task.dir)
    assert task.mode == "cron" and task.data["needs_owner"] is None
    subprocess.run([sys.executable, str(HERE / "fake_writer.py"), str(ctx.notes_path)], check=True)
    assert chat.session_finish(ctx)["state"] == "done"       # last range: the session finishes
    assert phase.load(task.dir).phase == "done"
    assert f"Run-Id: {task.run_id}" in show(origin, "main")
    assert calls(ctx) == ["1/1", "1/1"]   # cron + the session; cron did not call again


def test_question_in_the_first_of_two_ranges_is_saved_once(world, monkeypatch):
    ctx, origin, drive, package = world
    for n in range(3, 32):
        drive.file(f"{n}.jpg", package, jpeg((n * 5 % 255, 20, 30)))
    monkeypatch.setenv("FAKE_WRITER", "question")
    assert run_flow.run(ctx) == 1
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    answers = iter(["f"])
    assert chat._settle(ctx, task, ask=lambda _: next(answers), say=lambda _: None)
    subprocess.run([sys.executable, str(HERE / "fake_writer.py"), str(ctx.notes_path)], check=True)
    assert chat.session_finish(ctx)["state"] == "saved"
    assert not chat.save_session_result(ctx, phase.load(task.dir))   # end of session: no 2nd
    task = phase.load(task.dir)
    assert task.mode == "cron" and task.get("writing_k") == 2
    assert not (task.dir / "result-2.json").exists()
    monkeypatch.setenv("FAKE_WRITER", "good")
    assert run_flow.run(ctx) == 0, ctx.cfg.log_path.read_text()[-2000:]
    assert phase.load(task.dir).phase == "done"
    assert calls(ctx)[-1] == "2/2"


def test_thirty_one_pages_run_as_two_ranges(world):
    ctx, origin, drive, package = world
    for n in range(3, 32):
        drive.file(f"{n}.jpg", package, jpeg((n * 7 % 255, 10, 20)))
    assert run_flow.run(ctx) == 0, ctx.cfg.log_path.read_text()[-2000:]
    assert calls(ctx) == ["1/2", "2/2"]
    task = phase.all_tasks(ctx.task_root(), "benedek")[-1]
    assert task.phase == "done" and len(task.get("pages")) == 31
