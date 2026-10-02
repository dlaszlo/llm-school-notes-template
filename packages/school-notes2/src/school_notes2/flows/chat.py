"""`school-notes chat <learner> [codex|claude]` (plan 5.8): the owner's session.

The launcher runs on the host: it takes the lock (waiting if needed), lets the owner settle
a stopped run in the terminal, prepares a run, and starts the same container and MCP as
cron with the interactive template. The LLM starts `fetch`/`finish` itself through MCP."""

import sys

from ..llm import launch
from ..state import phase
from ..state.errors import NeedsOwner, SnError, Transient
from . import clear, fetch as fetch_flow
from . import finish as finish_flow
from . import handlers, run as run_flow, setup, steps, writer
from .context import Ctx
from .session import mcp


def chat(ctx: Ctx, harness_name: str | None, ask=input, say=print) -> int:
    lock = ctx.lock()
    lock.acquire("chat", on_wait=lambda h: say(f"A zárat {h.get('kind')} tartja "
                                               f"{h.get('since')} óta; várok… (Ctrl-C: kilépés)"))
    try:
        setup.ensure(ctx)
        task = phase.open_task(ctx.task_root(), ctx.name, "notes")
        if task is not None and not _settle(ctx, task, ask, say):
            return 0
        task = phase.open_task(ctx.task_root(), ctx.name, "notes")
        if task is None:
            task = interactive_fetch(ctx)
        _launch(ctx, task, harness_name)
        return 0
    finally:
        lock.release()


def _settle(ctx: Ctx, task: phase.Task, ask, say) -> bool:
    """A stopped or cron run: the owner decides here, outside the container (5.8)."""
    stop = task.data.get("needs_owner")
    if stop:
        say(f"A futás ({task.run_id}) áll: {stop['reason']}\nTeendő: {stop['todo']}")
        if task.get("conflict_files"):
            say("Ütköző fájlok: " + ", ".join(task.get("conflict_files")))
        choice = ask("[f]olytatás, [e]ldobás vagy [k]ilépés? ").strip().lower()
        if choice.startswith("e"):
            clear.discard(ctx, task)
            return True
        if not choice.startswith("f"):
            return False
        task.clear_needs_owner()
    if task.mode == "cron":
        if not ask(f"Nyitott automatikus futás ({task.run_id}, {task.phase}). Átveszed? [i/n] "
                   ).strip().lower().startswith("i"):
            return False
        task.data["mode"] = "interactive"
        task.save()
    return True


def interactive_fetch(ctx: Ctx) -> phase.Task:
    """A run for the session: ready packages, or none (repairs and free editing, 5.2)."""
    try:
        drive = fetch_flow.drive_client(ctx)
    except SnError as exc:
        ctx.log.event("drive.client", "offline", message=str(exc)[:200])
        drive = None
    task = fetch_flow.start(ctx, "interactive", drive, allow_image_only=True)
    run_flow.ctx_bind(ctx, task)
    if task.phase == "downloading":
        if drive is not None and task.get("candidates"):
            fetch_flow.download(ctx, task, drive)
            fetch_flow.move(ctx, task, drive)
        else:
            task.set_phase("moved", selected=[])
    fetch_flow.prepare(ctx, task, new_subject_index=run_flow.new_subject)
    return task


def _launch(ctx: Ctx, task: phase.Task, harness_name: str | None) -> None:
    role, harness = _role_for(ctx, harness_name)
    k = task.get("writing_k", 1)
    if task.phase == "prepared":
        task.set_phase("writing", writing_k=k)
    writer.write_inputs(ctx, task, min(k, len(task.get("ranges"))))
    h = handlers.build(ctx, None, fetch=lambda: _mcp_fetch(ctx), finish=lambda: _mcp_finish(ctx))
    print(f"Munkamappa: {ctx.notes_path}  (futás: {task.run_id})", file=sys.stderr)
    with mcp(ctx, task.dir, "interactive", h, lambda: _current_run(ctx)) as sessdir:
        launch.run_interactive(learner=ctx.name, run_id=task.run_id, role=role, harness=harness,
                               image=ctx.image_tag(),
                               mounts=launch.Mounts(work=ctx.notes_path, sessdir=sessdir),
                               log=ctx.log)


def _role_for(ctx: Ctx, harness_name: str | None):
    """The writer's role, or – for the other harness – the model of the role that already
    uses that harness family (Claude Code in a session runs the reviewer's model)."""
    role, harness = ctx.cfg.role("writer")
    if not harness_name or harness_name == harness.name:
        return role, harness
    for other in ctx.cfg.roles.values():
        if other.harness.split("-")[0] == harness_name:
            return other, ctx.cfg.harnesses[harness_name]
    raise NeedsOwner(f"no role uses the {harness_name} harness", todo="see config.toml [roles]")


def _current_run(ctx: Ctx) -> str:
    task = phase.open_task(ctx.task_root(), ctx.name, "notes")
    return task.run_id if task else ""


def _mcp_fetch(ctx: Ctx) -> dict:
    """MCP `fetch` in a session: a new run on the same worktree (5.8)."""
    task = phase.open_task(ctx.task_root(), ctx.name, "notes")
    if task is None:
        task = interactive_fetch(ctx)
        writer.write_inputs(ctx, task, 1)
    return {"run_id": task.run_id, "phase": task.phase, "pages": len(task.get("pages", [])),
            "open_review_items": len(task.get("open_review_items", []))}


def _mcp_finish(ctx: Ctx) -> dict:
    """MCP `finish`: the same function as cron; problems go back to the session."""
    task = phase.open_task(ctx.task_root(), ctx.name, "notes")
    if task is None:
        raise NeedsOwner("there is no open run to finish", todo="call fetch first")
    try:
        state = finish_flow.finish(ctx, task, notify_owner_items=lambda items: run_flow.owner_items(
            ctx, task, items))
    except steps.CheckFailed as exc:
        steps.write_check_items(ctx, exc.items)
        task.set_phase("writing")
        return {"state": "check_failed", "problems": exc.items[:50]}
    except finish_flow.git_finish.EditedDuringFinish:
        return {"state": "edited", "message": "files changed during finish; call finish again"}
    except Transient as exc:
        task.record_error("transient", str(exc))
        return {"state": "transient_error", "message": str(exc)}
    return {"state": state, "run_id": task.run_id, "published": task.get("published")}
