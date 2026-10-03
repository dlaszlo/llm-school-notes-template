"""The run's work branch in the durable notes worktree (plan 6.5) and changes.json (4.4)."""

import shutil
from pathlib import Path

from ..state.errors import NeedsOwner
from .run import Git, GitFailed

WORKDIR = ".school-notes"


def branch_name(run_id: str) -> str:
    return f"notes/{run_id}"


def start(wt: Git, run_id: str, base: str, interactive: bool) -> None:
    """`switch -C notes/<run> <base>`; idempotent when the branch already sits on base.

    Interactive runs carry uncommitted edits over; if they clash with the newer base, the
    switch refuses and the session is told which files clash."""
    branch = branch_name(run_id)
    current = wt.out("symbolic-ref", "--quiet", "--short", "HEAD", check=False).strip()
    if current == branch and wt.out("merge-base", "HEAD", base).strip() == base:
        return
    if not interactive:
        # Cron started from a clean worktree (5.1/1): anything here now is an interrupted
        # preparation of this run, so it is reset rather than reported as stray edits.
        wt.run("switch", "--discard-changes", "-C", branch, base, timeout=600)
        wt.run("clean", "-fdq", "--", ".", timeout=600)
        return
    try:
        wt.run("switch", "-C", branch, base, timeout=600)
    except GitFailed as exc:
        files = [ln.strip() for ln in exc.stderr.splitlines() if ln.startswith(("\t", "    "))]
        raise NeedsOwner("uncommitted edits in the worktree clash with origin/main",
                         todo="decide in `school-notes chat` which version to keep",
                         details={"files": files}) from None


def reset_workdir(worktree: Path) -> Path:
    """Delete and recreate .school-notes/ (never trusted across runs)."""
    workdir = worktree / WORKDIR
    if workdir.is_symlink() or workdir.is_file():
        workdir.unlink()
    elif workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir()
    return workdir


def changed_files(wt: Git, base: str) -> list[dict]:
    """Files that differ between `base` and the working tree, untracked files included."""
    out = wt.out("diff", "--no-ext-diff", "--no-textconv", "--name-status", "-z", base, "--")
    parts = [p for p in out.split("\0") if p]
    status_map = {"A": "added", "M": "modified", "D": "deleted", "T": "modified"}
    changed = {}
    for code, path in zip(parts[0::2], parts[1::2]):
        changed[path] = status_map.get(code[0], "modified")
    untracked = wt.out("ls-files", "--others", "--exclude-standard", "-z")
    for path in filter(None, untracked.split("\0")):
        changed[path] = "added"
    return [{"path": p, "status": s} for p, s in sorted(changed.items())]


def worktree_dirty(wt: Git) -> bool:
    return bool(wt.out("status", "--porcelain=v1", "-z", "--untracked-files=all"))
