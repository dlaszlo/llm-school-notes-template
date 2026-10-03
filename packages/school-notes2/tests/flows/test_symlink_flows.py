"""T7 / review 3 M1: `.school-notes` swapped for a symlink during a session."""

import os
import shutil

import pytest

from school_notes2.flows import chat, handlers, writer
from school_notes2.state import phase
from school_notes2.state.errors import NeedsOwner
from tests.e2e.test_run_e2e import world  # noqa: F401 - shared fixture


def test_linked_workdir_receives_nothing(world, tmp_path):
    ctx, origin, drive, package = world
    chat.session_fetch(ctx)
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    canary = tmp_path / "canary"
    canary.mkdir()
    shutil.rmtree(ctx.notes_path / ".school-notes")
    os.symlink(canary, ctx.notes_path / ".school-notes")
    with pytest.raises(NeedsOwner):            # UnsafePath is a NeedsOwner
        writer.write_inputs(ctx, task, 1)
    with pytest.raises(NeedsOwner):
        handlers.check(ctx, task)
    assert list(canary.iterdir()) == []


def test_writer_check_reports_an_image_without_rights(world):
    """The writer's own check reports what finish's public.json step would refuse."""
    ctx, origin, drive, package = world
    chat.session_fetch(ctx)
    task = phase.open_task(ctx.task_root(), "benedek", "notes")
    (ctx.notes_path / "wiki/assets/proba").mkdir(parents=True)
    (ctx.notes_path / "wiki/assets/proba/abra.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>\n')
    index = ctx.notes_path / "wiki/index.md"
    index.write_text(index.read_text() + "\n![Ábra](assets/proba/abra.svg)\n")
    found = handlers.check(ctx, task)
    assert any(p["file"] == "wiki/assets/proba/abra.svg" and "render.json" in p["message"]
               for p in found["problems"]), found
