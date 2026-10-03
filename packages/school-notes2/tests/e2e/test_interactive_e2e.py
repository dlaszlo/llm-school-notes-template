"""The session path (plan 5.8) and a crash between commit and push (S3, T11)."""

import subprocess
import sys

from school_notes2.flows import chat, finish as finish_flow, run as run_flow
from school_notes2.state import phase
from tests.e2e.test_run_e2e import HERE, show, world  # noqa: F401 - shared fixture


def test_session_fetch_edit_finish(world):
    ctx, origin, drive, package = world
    answer = chat._mcp_fetch(ctx)
    assert answer["pages"] == 2
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    assert task.mode == "interactive"
    subprocess.run([sys.executable, str(HERE / "fake_writer.py"), str(ctx.notes_path)], check=True)
    result = chat._mcp_finish(ctx)
    assert result["state"] == "done", result
    assert f"Run-Id: {task.run_id}" in show(origin, "main")


def test_session_check_failure_is_reported_not_counted(world, monkeypatch):
    ctx, origin, drive, package = world
    chat._mcp_fetch(ctx)
    subprocess.run([sys.executable, str(HERE / "fake_writer.py"), str(ctx.notes_path), "badlink"],
                   check=True)
    result = chat._mcp_finish(ctx)
    assert result["state"] == "check_failed" and result["problems"]
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    assert task.data["llm_failures"] == 0 and task.data["needs_owner"] is None


def test_crash_after_commit_resumes_with_one_commit(world, monkeypatch):
    ctx, origin, drive, package = world
    calls = []

    def crashing_build(ctx_, task, commit):
        calls.append(commit)
        if len(calls) == 1:
            raise KeyboardInterrupt("simulated SIGKILL after the commit")
        return {"commit": commit, "output": "/nonexistent"}

    monkeypatch.setattr(finish_flow, "_build", crashing_build)
    try:
        run_flow.run(ctx)
    except KeyboardInterrupt:
        pass
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    assert task.phase == "committed"
    assert run_flow.run(ctx) == 0
    log = show(origin, "main")
    assert log.count(f"Run-Id: {task.run_id}") == 1
