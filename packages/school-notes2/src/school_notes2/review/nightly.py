"""Nightly review, tool side of preparation (plan 5.6/1–3, 6.9/1).

Two Git objects are passed in: `repo` is the bare clone (fetch, rev-list, diff, push) and
`wt` is the review worktree (its own linked gitdir plus --work-tree, for switch/commit).
The LLM launch is not here; the orchestrator runs the reviewer between prepare and close.
"""

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Callable

from ..git.run import Git, with_retries
from ..schemas import validate
from ..state import phase
from ..state.errors import NeedsOwner
from ..state.files import write_bytes, write_json, write_text
from . import markers

DIFF_PATHS = ("wiki", "docs/review", "docs/evidence/pages")
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}
RASTER_EXT = IMAGE_EXT - {".svg"}
MARKER_REF = "refs/remotes/origin/claude-reviewed"
MAIN_REF = "refs/remotes/origin/main"
ACTIVE = ("reviewed", "closing", "pushing")

Rasterize = Callable[[list[Path], Path], list[Path]]


@dataclass
class Range:
    base: str                 # origin/claude-reviewed
    head: str                 # H = origin/main
    end: str                  # T: the last commit taken (H, or earlier when a limit cut)
    commits: list[str]
    patch: str
    images: list[dict] = field(default_factory=list)


def fetch(repo: Git, timeout: float) -> None:
    with_retries(lambda: repo.run("fetch", "origin", timeout=timeout), log=repo.log)


def rev(repo: Git, ref: str) -> str:
    """The commit SHA of `ref`, or "" when the ref does not exist."""
    proc = repo.run("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return proc.stdout.decode().strip() if proc.returncode == 0 else ""


def changed(repo: Git, a: str, b: str, paths: tuple[str, ...]) -> list[tuple[str, str]]:
    """[(status, path)] between two commits, renames off (6.3)."""
    raw = repo.out("diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--name-status",
                   "-z", a, b, "--", *paths)
    parts = raw.split("\0")
    return [(parts[i][0], parts[i + 1]) for i in range(0, len(parts) - 1, 2)]


def blob(repo: Git, commit: str, path: str) -> bytes:
    return repo.run("cat-file", "blob", f"{commit}:{path}").stdout


def _text(data: bytes, path: str) -> list[str] | None:
    if PurePosixPath(path).suffix.lower() in IMAGE_EXT or b"\0" in data:
        return None
    text = data.decode("utf-8", "replace")
    return (markers.blank(text) if path.endswith(".md") else text).splitlines(keepends=True)


def build_patch(repo: Git, a: str, b: str) -> str:
    """Unified diff of the reviewed paths with generated blocks emptied (plan 5.6/3)."""
    out = []
    for status, path in changed(repo, a, b, DIFF_PATHS):
        old = blob(repo, a, path) if status != "A" else b""
        new = blob(repo, b, path) if status != "D" else b""
        old_lines, new_lines = _text(old, path), _text(new, path)
        if old_lines is None or new_lines is None:
            out.append(f"Binary file {path} ({status})\n")
            continue
        diff = list(difflib.unified_diff(old_lines, new_lines,
                                         "/dev/null" if status == "A" else f"a/{path}",
                                         "/dev/null" if status == "D" else f"b/{path}"))
        out.append("".join(line if line.endswith("\n") else line + "\n" for line in diff))
    return "".join(out)


def images(repo: Git, a: str, b: str) -> list[dict]:
    """New source images and new/changed figures, in path order (p0001 < p0002)."""
    found = []
    for status, path in changed(repo, a, b, ("sources", "wiki/assets")):
        suffix = PurePosixPath(path).suffix.lower()
        if suffix not in IMAGE_EXT or status == "D":
            continue
        if path.startswith("sources/") and status != "A":
            continue
        found.append({"path": path, "kind": "source" if path.startswith("sources/") else "figure"})
    return found


def select(repo: Git, *, max_images: int, max_diff_kb: int, max_commits: int | None,
           fetch_timeout: float) -> Range | None:
    """Fetch and choose the range; None when nothing is new (no LLM call)."""
    fetch(repo, fetch_timeout)
    base, head = rev(repo, MARKER_REF), rev(repo, MAIN_REF)
    if not base:
        raise NeedsOwner("claude-reviewed marker missing", todo="create it once (plan 6.9/4)")
    if not repo.ok("merge-base", "--is-ancestor", base, head):
        raise NeedsOwner("origin/claude-reviewed is not an ancestor of origin/main",
                         todo="check the claude-reviewed branch on GitHub")
    commits = repo.out("rev-list", "--reverse", f"{base}..{head}").split()
    if not commits:
        return None
    chosen = None
    for i, commit in enumerate(commits[:max_commits or len(commits)]):
        patch, imgs = build_patch(repo, base, commit), images(repo, base, commit)
        if i and (len(patch.encode()) > max_diff_kb * 1024 or len(imgs) > max_images):
            break
        chosen = Range(base, head, commit, commits[:i + 1], patch, imgs)
    return chosen


def write_input(repo: Git, wt: Git, rng: Range, in_dir: Path, rasterize: Rasterize) -> None:
    """Review worktree at T; diff.patch, the images and images.json into the input folder."""
    wt.run("switch", "--detach", "--discard-changes", rng.end)
    out_dir = in_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_text(in_dir / "diff.patch", rng.patch, 0o644)
    listing, svgs = [], []
    for n, img in enumerate(rng.images, start=1):
        name = f"{n:03d}-{PurePosixPath(img['path']).name}"
        if PurePosixPath(img["path"]).suffix.lower() in RASTER_EXT:
            write_bytes(out_dir / name, blob(repo, rng.end, img["path"]), 0o644)
            listing.append({**img, "file": f"images/{name}"})
        else:
            svg = in_dir / "svg" / name
            write_bytes(svg, blob(repo, rng.end, img["path"]), 0o644)
            svgs.append(svg)
            listing.append({**img, "file": f"images/{Path(name).with_suffix('.png').name}"})
    if svgs:
        rasterize(svgs, out_dir)  # network-less container (plan 5.6/3), never on the host
    write_json(in_dir / "images.json", listing, 0o644)


def prepare(root: Path, student: str, repo: Git, wt: Git, *, max_images: int, max_diff_kb: int,
            fetch_timeout: float, rasterize: Rasterize, previous: phase.Task | None = None):
    """Create the review task (phase `prepared`), or return None for an empty range."""
    rng = select(repo, max_images=max_images, max_diff_kb=max_diff_kb,
                 max_commits=next_cap(previous), fetch_timeout=fetch_timeout)
    if rng is None:
        return None
    task = phase.create(root, student, "review", "cron", "prepared")
    task.update(base=rng.base, H=rng.head, T=rng.end, commits=rng.commits,
                images=len(rng.images), diff_bytes=len(rng.patch.encode()))
    write_input(repo, wt, rng, task.dir / "in", rasterize)
    task.update(input_ready=True)
    return task


def resume_prepared(task: phase.Task, repo: Git, wt: Git, rasterize: Rasterize) -> None:
    """Rebuild a half-written input folder from the recorded H/T (crash after create)."""
    if task.get("input_ready"):
        return
    base, end = task.get("base"), task.get("T")
    rng = Range(base, task.get("H"), end, task.get("commits"), build_patch(repo, base, end),
                images(repo, base, end))
    write_input(repo, wt, rng, task.dir / "in", rasterize)
    task.update(input_ready=True)


def record_review(task: phase.Task, review: dict) -> None:
    """A valid review.json closes the LLM part; from here on no LLM call is needed."""
    validate("review", review)
    write_json(task.dir / "review.json", review)
    task.set_phase("reviewed")


def record_timeout(task: phase.Task) -> None:
    """A reviewer timeout is not an error: the next night tries half the commits."""
    task.data["closed"] = True
    task.update(timed_out=True)


def next_cap(previous: phase.Task | None) -> int | None:
    if previous is None or not previous.get("timed_out"):
        return None
    return max(1, len(previous.get("commits", [])) // 2)


def stuck_commit(previous: list[phase.Task]) -> str | None:
    """The single commit that timed out on the last two nights in a row, if any (5.6/6)."""
    last = [t for t in previous if t.kind == "review"][-2:]
    if len(last) < 2 or not all(t.get("timed_out") and len(t.get("commits", [])) == 1
                                for t in last):
        return None
    first, second = (t.get("commits")[0] for t in last)
    return first if first == second else None


def pending_close(tasks: list[phase.Task]) -> phase.Task | None:
    """An earlier review whose review.json is valid but whose closing did not finish."""
    for task in tasks:
        if task.kind == "review" and task.open and task.phase in ACTIVE:
            return task
    return None


def load_review(task: phase.Task) -> dict:
    review = json.loads((task.dir / "review.json").read_text(encoding="utf-8"))
    validate("review", review)
    return review
