"""A content conflict settled by the owner (6.7) and a stuck nightly review (D85)."""

import subprocess

from school_notes2.flows import chat, clear, finish as finish_flow, nightly as nightly_flow
from school_notes2.flows import run as run_flow
from school_notes2.state import phase
from tests.e2e.test_nightly_e2e import ENV
from tests.e2e.test_run_e2e import show, world  # noqa: F401 - shared fixture


def laptop(tmp_path, origin, edits: dict[str, str]):
    clone = tmp_path / f"laptop-{len(list(tmp_path.glob('laptop-*')))}"
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, env=ENV)
    for rel, change in edits.items():
        path = clone / rel
        path.write_text(change(path.read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run(["git", "-C", str(clone), "commit", "-qam", "laptop"], check=True, env=ENV)
    subprocess.run(["git", "-C", str(clone), "push", "-q", "origin", "main"], check=True, env=ENV)


def test_owner_settles_a_content_conflict(world, tmp_path, monkeypatch):
    ctx, origin, drive, package = world
    pushed = []

    def build(ctx_, task, commit):
        if not pushed:
            pushed.append(1)
            laptop(tmp_path, origin, {
                "wiki/log.md": lambda t: t + "\n## 2026-10-03\n\n* **Update**: laptop.\n",
                "wiki/proba/index.md": lambda t: t.replace("# Próba", "# Próba tantárgy", 1)})
        return {"commit": commit, "output": "/nonexistent"}

    monkeypatch.setattr(finish_flow, "_build", build)
    assert run_flow.run(ctx) == 1
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    assert task.get("rebase") == "conflict" and task.get("conflict_files") == ["wiki/log.md"]
    answers = iter(["f", "i"])
    assert chat._settle(ctx, task, ask=lambda _: next(answers), say=lambda _: None)
    log = ctx.notes_path / "wiki/log.md"
    text = log.read_text(encoding="utf-8")
    kept = [ln for ln in text.splitlines() if not ln.startswith(("<<<<<<<", "=======", ">>>>>>>"))]
    log.write_text("\n".join(kept) + "\n", encoding="utf-8")
    result = chat.session_finish(ctx)
    assert result["state"] == "done", result
    merged = show(origin, "main:wiki/log.md")
    assert "laptop." in merged and "Teszt óra feldolgozva." in merged
    assert "# Próba tantárgy" in show(origin, "main:wiki/proba/index.md")


def test_stuck_review_opens_one_marker_and_continue_closes_it(world, monkeypatch):
    ctx, origin, drive, package = world
    for _ in range(2):
        old = phase.create(ctx.task_root(), "benedek", "review", "cron", "prepared")
        old.update(commits=["c0ffee" * 6 + "abcd"], timed_out=True)
        old.data["closed"] = True
        old.save()
    monkeypatch.setattr("school_notes2.flows.setup.ensure", lambda ctx: None)
    assert nightly_flow.nightly(ctx) == 0
    assert nightly_flow.nightly(ctx) == 0
    open_reviews = [t for t in phase.all_tasks(ctx.task_root(), "benedek")
                    if t.kind == "review" and t.open and not t.data.get("closed")]
    assert len(open_reviews) == 1 and open_reviews[0].data["needs_owner"]
    assert "emelt" in clear.clear(ctx, "review", "continue")
    assert phase.open_task(ctx.task_root(), "benedek", "review") is None
