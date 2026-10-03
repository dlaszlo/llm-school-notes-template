"""Bare clones and durable worktrees (plan 6.2). Created once, checked at every job start."""

from pathlib import Path

from .run import Git

# No `+`: a rewritten remote history makes the fetch fail instead of silently moving.
# An exact refspec fails when the remote ref is missing, so refs that may not exist yet
# (claude-reviewed before the cut-over, gh-pages before the first release) are fetched
# only by the step that needs them.
MAIN_SPEC = "refs/heads/main:refs/remotes/origin/main"
REVIEWED_SPEC = "refs/heads/claude-reviewed:refs/remotes/origin/claude-reviewed"
GH_PAGES_SPEC = "refs/heads/gh-pages:refs/remotes/origin/gh-pages"
NOTES_REFSPECS = (MAIN_SPEC,)
SITE_REFSPECS = (MAIN_SPEC,)    # gh-pages is fetched explicitly once it exists


def ensure_bare(git: Git, url: str, refspecs: tuple[str, ...], timeout: float = 600) -> None:
    """Create the bare clone with `+`-less refspecs; idempotent."""
    if not (git.git_dir / "HEAD").exists():
        git.git_dir.parent.mkdir(parents=True, exist_ok=True)
        git.run("init", "--bare", "--quiet", str(git.git_dir), cwd=git.git_dir.parent)
    existing = git.run("config", "--get", "remote.origin.url", check=False).stdout.decode().strip()
    if existing != url:
        if existing:
            git.run("remote", "set-url", "origin", url)
        else:
            git.run("remote", "add", "origin", url)
    git.run("config", "--unset-all", "remote.origin.fetch", check=False)
    for spec in refspecs:
        git.run("config", "--add", "remote.origin.fetch", spec)
    git.run("config", "core.bare", "true")
    exclude = git.git_dir / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    # The run's working files must never be committed, whatever the repo's .gitignore says.
    current = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if ".school-notes/" not in current.split("\n"):
        sep = "" if not current or current.endswith("\n") else "\n"
        exclude.write_text(current + sep + ".school-notes/\n", encoding="utf-8")


def fetch(git: Git, timeout: float, *specs: str) -> None:
    """Fetch the configured refs, or exactly `specs` when given."""
    git.run("fetch", "--no-tags", "origin", *specs, timeout=timeout)


def ensure_worktree(git: Git, path: Path, start: str) -> Path:
    """The durable worktree at `path` (detached at `start` when created); returns its .git file."""
    dot_git = path / ".git"
    if not dot_git.is_file():
        git.run("worktree", "prune", check=False)
        path.parent.mkdir(parents=True, exist_ok=True)
        git.run("worktree", "add", "--detach", "--force", str(path), start, cwd=git.git_dir,
                timeout=1800)
    expected = f"gitdir: {git.git_dir / 'worktrees' / path.name}"
    if dot_git.read_text(encoding="utf-8").strip() != expected:
        raise RuntimeError(f"{path}: worktree registered under an unexpected name; "
                           "remove the stale entry in worktrees/ and run setup again")
    return dot_git


def dot_git_ok(path: Path, recorded: bytes) -> bool:
    """The worktree's .git file must be byte-identical to the recorded one (plan 7.6)."""
    dot_git = path / ".git"
    return dot_git.is_file() and not dot_git.is_symlink() and dot_git.read_bytes() == recorded


def has_ref(git: Git, ref: str) -> bool:
    return git.ok("rev-parse", "--verify", "--quiet", ref)


def rev(git: Git, ref: str) -> str:
    return git.out("rev-parse", "--verify", ref).strip()


def is_ancestor(git: Git, a: str, b: str) -> bool:
    return git.ok("merge-base", "--is-ancestor", a, b)


def ls_remote(git: Git, ref: str, timeout: float) -> str | None:
    out = git.out("ls-remote", "origin", ref, timeout=timeout).strip()
    return out.split()[0] if out else None


def worktree_git(bare: Git, path: Path) -> Git:
    """Git bound to a linked worktree. The gitdir is computed, never read from the
    worktree's .git file, because the container could rewrite that file."""
    return Git(bare.git_dir / "worktrees" / path.name, bare.name, bare.email, bare.log,
               bare.remote, path)
