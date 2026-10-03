"""`docs/review/index.md` (plan 4.7): a generated block at the top, hand-written text kept below."""

from pathlib import Path

from ..state import safefs
from ..wiki import frontmatter as fm
from ..wiki import markers
from .files import OPEN, OWNER, REVIEW_DIR, review_files

BLOCK = "review-index"


def _entry(repo: Path, path: Path, items: dict, states: tuple[str, ...]) -> str:
    rel = path.relative_to(repo / REVIEW_DIR).as_posix()
    picked = sorted((i for i, s in items.items() if s in states), key=lambda i: int(i[1:]))
    suffix = f" – {', '.join(picked)}" if picked else ""
    return f"* [{path.stem}]({rel}){suffix}"


def render(repo: Path) -> str:
    """The block content: Nyitott / Tulajdonosra vár / Lezárt, newest file first."""
    lists: dict[str, list[str]] = {"Nyitott": [], "Tulajdonosra vár": [], "Lezárt": []}
    for path in reversed(review_files(repo)):
        meta = fm.split(safefs.read_text(repo, safefs.rel_of(repo, path))).meta
        items = meta.get("items")
        if not isinstance(items, dict):
            continue
        if OPEN in items.values():
            lists["Nyitott"].append(_entry(repo, path, items, (OPEN,)))
        if OWNER in items.values():
            lists["Tulajdonosra vár"].append(_entry(repo, path, items, (OWNER,)))
        if meta.get("status") == "closed":
            lists["Lezárt"].append(_entry(repo, path, items, ()))
    out = []
    for title, entries in lists.items():
        out += [f"## {title}", ""] + (entries or ["* nincs"]) + [""]
    return "\n".join(out)


def update(repo: Path) -> Path:
    """Rewrite only the generated block; insert it at the top when the file has none."""
    rel = f"{REVIEW_DIR}/index.md"
    path = repo / rel
    old = safefs.read_text(repo, rel) if safefs.exists(repo, rel) else ""
    content = render(repo)
    if BLOCK in markers.names(old):
        new = markers.replace(old, BLOCK, content)
    else:
        new = markers.wrap(BLOCK, content) + ("\n" + old if old else "")
    if new != old:
        safefs.write_text(repo, rel, new)
    return path
