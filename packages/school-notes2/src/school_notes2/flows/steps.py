"""`finish` steps 1–6 (plan 5.4): guard, results, machine fields, closures, evidence,
check, generation. Steps 5–6 also run after a rebase (G4) and for the MCP `check`."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from ..evidence import records
from ..git import workbranch
from ..log import now_iso
from ..review import files as review_files
from ..review import index as review_index
from ..schemas import validate
from ..state.errors import BadWork, NeedsOwner
from ..state.files import read_json, write_json
from ..state.phase import Task
from ..wiki import check as wiki_check
from ..wiki import frontmatter, generate, guard, machine, markers, public
from ..wiki.check_result import check_result
from . import fetch as fetch_flow
from . import writer
from .context import Ctx

TOOL_WHOLE_FILES = ("tools/subjects.json", "publication/public.json", "docs/review/index.md")


class CheckFailed(BadWork):
    """The writer must fix check.json items (back to the writer, 8.2)."""

    def __init__(self, items: list[dict]):
        super().__init__(f"check found {len(items)} problem(s)", details={"items": items})
        self.items = items


@dataclass
class Prepared:
    result: dict
    question: bool
    new_owner: list[dict] = field(default_factory=list)


def guard_step(ctx: Ctx, task: Task) -> None:
    """Step 1: the path guard. Owner-class violations stop the run; others go back."""
    wt = ctx.worktree("notes")
    base = task.get("base")
    changes = [guard.Change(c["path"], c["status"])
               for c in workbranch.changed_files(wt, base)]

    def base_content(path: str) -> bytes | None:
        proc = wt.run("show", f"{base}:{path}", check=False)
        return proc.stdout if proc.returncode == 0 else None

    found = guard.run(guard.GuardInput(
        worktree=ctx.notes_path, changes=changes, base_content=base_content,
        tool_files=task.get("tool_writes", {}), tool_parts=task.get("tool_parts", {}),
        interactive=task.mode == "interactive",
        conflict_files=frozenset(task.get("conflict_files", [])),
        git_file=task.get("dot_git", "").encode("utf-8") or None))
    owner = [v for v in found if v.owner]
    if owner:
        raise NeedsOwner("path guard: " + "; ".join(f"{v.path}: {v.message}" for v in owner[:5]),
                         todo="inspect the worktree in `school-notes chat`")
    if found:
        raise CheckFailed([wiki_check.item(v.path, None, v.message) for v in found])


def merged_result(ctx: Ctx, task: Task) -> dict:
    """Step 2: the saved result-<k>.json files; an interactive session's own result.json."""
    if task.mode == "interactive":
        own = read_json(ctx.notes_path / workbranch.WORKDIR / "result.json")
        if own is not None:
            validate("result", own)
            n = len(task.get("ranges"))
            write_json(task.dir / f"result-{n}.json", own)
    if task.get("skip_writer"):
        return {"status": "done"}
    try:
        return writer.merge(writer.results(task))
    except BadWork:
        if task.mode == "interactive" and not any(not p["duplicate_of"]
                                                  for p in task.get("pages", [])):
            return {"status": "done"}     # free editing in a session needs no result.json
        raise


def content_steps(ctx: Ctx, task: Task) -> Prepared:
    """Steps 1–6. Raises CheckFailed (back to the writer) or NeedsOwner."""
    guard_step(ctx, task)
    result = merged_result(ctx, task)
    repo = ctx.notes_path
    fetch = fetch_flow.fetch_json(task, len(task.get("ranges")))
    listed = fetch["open_review_items"]
    problems = check_result(repo, result, fetch, {(i["file"], i["item_id"]) for i in listed},
                            ctx.cfg.limits.review_closures_per_run)
    if wiki_check.errors(problems):
        raise CheckFailed(problems)
    by, at = _writer_label(ctx), now_iso()
    parts = machine.write_lesson_notes(repo, result.get("notes", []), fetch,
                                       ctx.student.grade, by, at)
    changed = [c["path"] for c in workbranch.changed_files(ctx.worktree("notes"), task.get("base"))]
    parts += machine.stamp_generated(repo, changed, by, at)
    machine.add_subjects(repo, result.get("new_subjects", []), _drive_names(task))
    outcome = review_files.apply_closure(repo, task.run_id, result.get("review_closure", []),
                                         listed, ctx.cfg.limits.owner_after_open)
    evidence = records.append(repo, records.from_writer(result.get("checks", [])),
                              run_id=task.run_id, checker=by, at=at, fetch_pages=fetch["pages"])
    _record_writes(task, repo, whole=outcome.written + evidence, parts=parts)
    regenerate(ctx, task)
    return Prepared(result, result["status"] == "question", outcome.new_owner)


def regenerate(ctx: Ctx, task: Task) -> None:
    """Steps 5–6: check the changed files, then generate indexes and public.json."""
    repo = ctx.notes_path
    changed = [c["path"] for c in workbranch.changed_files(ctx.worktree("notes"), task.get("base"))]
    items = wiki_check.check_files(repo, changed)
    errors = wiki_check.errors(items)
    if errors:
        raise CheckFailed(errors)
    indexes = generate.write_indexes(repo)
    try:
        public.write(repo, public.either(public.render_rights(repo), generated_rights(ctx)))
    except public.PublicError as exc:
        raise CheckFailed([wiki_check.item(p, None, "image without a rights record (render.json "
                                                    "or image ledger)") for p in exc.paths])
    review_index.update(repo)
    _record_writes(task, repo, whole=list(TOOL_WHOLE_FILES), parts=indexes)
    write_json(repo / workbranch.WORKDIR / "check.json",
               [i for i in items if i.get("severity") == "warning"], mode=0o644)


def generated_rights(ctx: Ctx):
    """New generated images: the receipt the image tool wrote under docs/evidence/media/."""
    prefix = f"{ctx.name}-"

    def lookup(rel: str):
        stem = Path(rel).stem
        receipt = f"docs/evidence/media/{stem}"
        if stem.startswith(prefix) and (ctx.notes_path / receipt).is_dir():
            return ("generated", receipt)
        return None
    return lookup


def write_check_items(ctx: Ctx, items: list[dict]) -> None:
    validate("check", items)
    write_json(ctx.notes_path / workbranch.WORKDIR / "check.json", items, mode=0o644)


def _record_writes(task: Task, repo: Path, *, whole: list[str], parts: list[str]) -> None:
    files = dict(task.get("tool_writes", {}))
    for rel in whole:
        if (repo / rel).is_file():
            files[rel] = hashlib.sha256((repo / rel).read_bytes()).hexdigest()
    tool_parts = dict(task.get("tool_parts", {}))
    for rel in parts:
        if (repo / rel).is_file() and rel not in files:
            text = (repo / rel).read_text(encoding="utf-8")
            tool_parts[rel] = guard.parts_hash(text)
    task.update(tool_writes=files, tool_parts=tool_parts)


def _writer_label(ctx: Ctx) -> str:
    role, _ = ctx.cfg.role("writer")
    return f"{role.model}/{role.effort}"


def _drive_names(task: Task) -> dict[str, str]:
    return {p["subject"]: p["drive_folder"] for p in task.get("packages", [])}


def llm_snapshot(ctx: Ctx, task: Task) -> dict:
    """The writer's own changes, as hashes without the tool's parts (5.4/9 race guard).

    A file whose LLM-written part equals the base is left out, so the tool's own writes
    (machine keys, generated blocks, whole tool files) never look like an edit."""
    wt = ctx.worktree("notes")
    base = task.get("base")
    out = {}
    for c in workbranch.changed_files(wt, base):
        rel = c["path"]
        if rel in task.get("tool_writes", {}):
            continue
        path = ctx.notes_path / rel
        now = _llm_hash(rel, path.read_bytes()) if path.is_file() else None
        old = wt.run("show", f"{base}:{rel}", check=False)
        if old.returncode == 0 and now == _llm_hash(rel, old.stdout):
            continue
        out[rel] = now
    return out


def _llm_hash(rel: str, data: bytes) -> str:
    if rel.endswith(".md"):
        data = _llm_part(data.decode("utf-8", "replace")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _llm_part(text: str) -> str:
    """The text without generated blocks and machine frontmatter keys."""
    text = markers.empty_all(text)
    try:
        meta = frontmatter.split(text).meta
    except Exception:  # noqa: BLE001 - unreadable frontmatter: compare the whole text
        return text
    return frontmatter.strip_keys(text, machine.machine_keys(meta))
