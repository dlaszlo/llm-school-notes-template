"""Discarding a notes run (plan 6.11, 8.3): bundle first, never lose unpushed work."""

from pathlib import Path

from . import repos
from .run import Git
from .workbranch import branch_name

TIMEOUT_S = 600


def discard(wt: Git, run_id: str, archive_dir: Path) -> Path | None:
    """Abort a rebase, commit leftovers, bundle every unpushed commit, reset the worktree.

    Uncommitted edits are committed even when HEAD is detached (an interrupted fetch leaves
    no branch), on `notes/<run>` or, if that branch exists elsewhere, `notes/<run>-leftover`.
    The worktree is reset only after `bundle verify` succeeded. Returns the bundle path, or
    None when nothing was unpushed."""
    if (wt.git_dir / "rebase-merge").exists() or (wt.git_dir / "rebase-apply").exists():
        wt.run("rebase", "--abort", timeout=TIMEOUT_S)
    branches = [branch_name(run_id), f"{branch_name(run_id)}-leftover"]
    _commit_leftovers(wt, run_id, branches)
    unpushed = [b for b in branches if repos.has_ref(wt, f"refs/heads/{b}") and int(
        wt.out("rev-list", "--count", f"refs/remotes/origin/main..refs/heads/{b}").strip() or 0)]
    bundle = None
    if unpushed:
        archive_dir.mkdir(parents=True, exist_ok=True)
        bundle = archive_dir / f"{run_id}.bundle"
        wt.run("bundle", "create", str(bundle), *[f"refs/heads/{b}" for b in unpushed],
               "^refs/remotes/origin/main", timeout=TIMEOUT_S)
        wt.run("bundle", "verify", str(bundle), timeout=TIMEOUT_S)
    wt.run("switch", "--detach", "--discard-changes", "refs/remotes/origin/main", timeout=TIMEOUT_S)
    wt.run("clean", "-fd", "--", ".", timeout=TIMEOUT_S)
    for b in branches:
        if repos.has_ref(wt, f"refs/heads/{b}"):
            wt.run("branch", "-D", b)
    return bundle


def _commit_leftovers(wt: Git, run_id: str, branches: list[str]) -> None:
    if not wt.out("status", "--porcelain=v1", "-z", "--untracked-files=all"):
        return
    current = wt.out("symbolic-ref", "--quiet", "--short", "HEAD", check=False).strip()
    if current not in branches:
        target = branches[0] if not repos.has_ref(wt, f"refs/heads/{branches[0]}") else branches[1]
        wt.run("switch", "-C", target, timeout=TIMEOUT_S)         # carries the edits along
    wt.run("add", "-A", "--", ".", timeout=TIMEOUT_S)
    if not wt.ok("diff", "--cached", "--quiet"):
        wt.run("commit", "--no-verify", "-m", f"discarded run {run_id} (local only)",
               timeout=TIMEOUT_S)
