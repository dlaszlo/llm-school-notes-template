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
