"""One-time creation of the bare clones and the durable worktrees (plan 6.2, 11/1).

Idempotent: run again at every job start through `ensure`, it only recreates what is
missing and verifies the worktrees' .git files against the recorded bytes."""

import base64

from ..git import repos
from ..git.run import with_retries
from ..state.errors import NeedsOwner
from ..state.files import read_json, write_json
from .context import Ctx

WORKTREES = ("notes", "review", "site")


def _record_path(ctx: Ctx):
    return ctx.cfg.state_dir / ctx.name / "worktrees.json"


def setup(ctx: Ctx) -> dict:
    """Clone both repos bare, create the three worktrees, record their .git bytes."""
    timeout = ctx.cfg.timeouts.fetch_s
    for site, url, specs in ((False, ctx.student.repo, repos.NOTES_REFSPECS),
                             (True, ctx.student.site_repo, repos.SITE_REFSPECS)):
        bare = ctx.bare(site)
        repos.ensure_bare(bare, url, specs)
        with_retries(lambda b=bare: repos.fetch(b, timeout), log=ctx.log)
    record = {}
    for which in WORKTREES:
        bare = ctx.bare(site=which == "site")
        path = ctx.cfg.worktree(ctx.name, which)
        dot_git = repos.ensure_worktree(bare, path, "refs/remotes/origin/main")
        record[which] = base64.b64encode(dot_git.read_bytes()).decode("ascii")
    write_json(_record_path(ctx), record)
    ctx.log.event("setup", target=ctx.name)
    return record


def ensure(ctx: Ctx) -> None:
    """Job start: worktrees exist and their .git files are the recorded ones (7.6)."""
    record = read_json(_record_path(ctx))
    if record is None:
        raise NeedsOwner("the repositories are not set up", todo=f"school-notes setup {ctx.name}")
    for which in WORKTREES:
        path = ctx.cfg.worktree(ctx.name, which)
        recorded = base64.b64decode(record[which])
        if not (path / ".git").exists():
            bare = ctx.bare(site=which == "site")
            repos.ensure_worktree(bare, path, "refs/remotes/origin/main")
        if not repos.dot_git_ok(path, recorded):
            raise NeedsOwner(f"the .git file of the {which} worktree was replaced",
                             todo="inspect the worktree; recreate it with `school-notes setup`")
