"""Housekeeping (plan 10.5): finished task folders older than 90 days are removed.
Bundles, old releases and the image ledger are never removed automatically."""

import shutil
from datetime import datetime, timedelta

from ..log import TZ
from ..state import phase
from .context import Ctx

KEEP_DAYS = 90


def old_tasks(ctx: Ctx, now: datetime | None = None) -> list[str]:
    limit = (now or datetime.now(TZ)) - timedelta(days=KEEP_DAYS)
    removed = []
    for task in phase.all_tasks(ctx.task_root(), ctx.name):
        finished = task.phase == "done" or task.data.get("closed")
        if finished and datetime.fromisoformat(task.data["updated"]) < limit:
            shutil.rmtree(task.dir)
            removed.append(task.run_id)
    if removed:
        ctx.log.event("cleanup.tasks", target=f"{len(removed)} folder(s)")
    return removed
