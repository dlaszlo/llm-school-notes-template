"""Discarding a notes run (plan 6.11, 8.3): bundle first, never lose unpushed work."""

from pathlib import Path

from . import repos
from .run import Git
from .workbranch import branch_name


def discard(wt: Git, run_id: str, archive_dir: Path) -> Path | None:
    """Abort a rebase, commit leftovers locally, bundle the branch, reset the worktree.

    Returns the bundle path, or None when the branch held nothing beyond origin/main."""
    if (wt.git_dir / "rebase-merge").exists() or (wt.git_dir / "rebase-apply").exists():
        wt.run("rebase", "--abort")
    branch = branch_name(run_id)
    on_branch = wt.out("symbolic-ref", "--quiet", "--short", "HEAD", check=False).strip() == branch
    if on_branch and wt.out("status", "--porcelain=v1", "-z", "--untracked-files=all"):
        wt.run("add", "-A", "--", ".")
        if not wt.ok("diff", "--cached", "--quiet"):
            wt.run("commit", "--no-verify", "-m", f"discarded run {run_id} (local only)")
    bundle = None
    if repos.has_ref(wt, f"refs/heads/{branch}"):
        count = wt.out("rev-list", "--count", f"refs/remotes/origin/main..refs/heads/{branch}")
        if int(count.strip() or 0) > 0:
            archive_dir.mkdir(parents=True, exist_ok=True)
            bundle = archive_dir / f"{run_id}.bundle"
            wt.run("bundle", "create", str(bundle), f"refs/remotes/origin/main..refs/heads/{branch}")
            wt.run("bundle", "verify", str(bundle))
    wt.run("switch", "--detach", "--discard-changes", "refs/remotes/origin/main")
    wt.run("clean", "-fd", "--", ".")
    if repos.has_ref(wt, f"refs/heads/{branch}"):
        wt.run("branch", "-D", branch)
    return bundle
