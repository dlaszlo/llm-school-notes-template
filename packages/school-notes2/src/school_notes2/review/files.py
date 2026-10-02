"""Review files `docs/review/<date>-review.md` (plan 4.7): the tool writes every one of them.

The frontmatter (`reviewer`, `range`, `items`, `status`) is machine-only. The body is written
once from review.json and never rewritten; closures are appended as `## Végrehajtva (<run>)`.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..state.files import write_text
from ..wiki import frontmatter as fm

REVIEW_DIR = Path("docs/review")
OPEN, OWNER, FIXED, DISAGREE = "open", "owner", "fixed", "disagree"
WORDS = {"fixed": "javítva", "disagree": "nem ért egyet", "open": "nyitva",
         "untouched": "nem érintett"}
DONE_HEADING = re.compile(r"^## Végrehajtva \((?P<run>[^)]+)\)$", re.M)
DONE_LINE = re.compile(r"^\* (?P<item>R\d+) – (?P<word>javítva|nem ért egyet|nyitva|nem érintett)",
                       re.M)
ITEM_NUM = re.compile(r"R(\d+)")


class ClosureError(ValueError):
    """A closure names a file or item that does not exist or is not open."""


@dataclass
class ClosureOutcome:
    written: list[str] = field(default_factory=list)       # repo paths the tool changed
    new_owner: list[dict] = field(default_factory=list)    # [{file, item_id}] e-mail once


def compute_status(items: dict) -> str:
    return "open" if any(v in (OPEN, OWNER) for v in items.values()) else "closed"


def next_path(repo: Path, date: str) -> Path:
    """`<date>-review.md`, then `-2`, `-3` for further reviews on the same day."""
    base = repo / REVIEW_DIR
    candidate, n = base / f"{date}-review.md", 2
    while candidate.exists():
        candidate, n = base / f"{date}-review-{n}.md", n + 1
    return candidate


def _location(finding: dict) -> str:
    line = finding.get("line")
    return f"{finding['file']}:{line}" if line else finding["file"]


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def render_body(date: str, review: dict, frm: str, to: str) -> str:
    verdict = "rendben" if review["verdict"] == "ok" else "javítást kér"
    out = [f"# Review – {date}", "",
           f"Tartomány: `{frm[:12]}..{to[:12]}`. Értékelés: {verdict}.", ""]
    if review["findings"]:
        out += ["## Megállapítások", ""]
    for f in review["findings"]:
        out += [f"### {f['id']} – {_location(f)}", "", f"**Probléma:** {f['problem']}", ""]
        if f.get("suggestion"):
            out += [f"**Javaslat:** {f['suggestion']}", ""]
    if review.get("figures"):
        out += ["## Ábrák", ""]
    for fig in review.get("figures", []):
        out += [f"### {fig['file']} ({fig['page']})", "", f"**Ítélet:** {fig['verdict']}", "",
                f"**Megfigyelés:** {fig['observed']}", ""]
        if fig.get("description"):
            out += [f"**Leírás:** {fig['description']}", ""]
    if review.get("family_questions"):
        out += ["## Családi kérdések", ""] + [f"* {q}" for q in review["family_questions"]] + [""]
    return "\n".join(out)


def _with_frontmatter(body: str, reviewer: str, frm: str, to: str, items: dict) -> str:
    values = {"reviewer": reviewer, "range": {"from": frm, "to": to}, "items": items,
              "status": compute_status(items)}
    return fm.set_keys("\n" + body, values)


def write_review(repo: Path, date: str, review: dict, reviewer: str, frm: str, to: str) -> Path:
    """A new review file from a validated review.json; returns its path."""
    ids = [f["id"] for f in review["findings"]]
    if len(set(ids)) != len(ids):
        raise ValueError("review.json: duplicate finding ids")
    path = next_path(repo, date)
    items = {i: OPEN for i in sorted(ids, key=_num)}
    write_text(path, _with_frontmatter(render_body(date, review, frm, to), reviewer, frm, to,
                                       items), 0o644)
    return path


def write_timeout_report(repo: Path, date: str, commit: str, parent: str, reviewer: str,
                         run_id: str) -> Path:
    """`--discard review`: the commit is closed as not reviewed (plan 5.6/6)."""
    path = next_path(repo, date)
    body = (f"# Review – {date}\n\nNem átnézve: időtúllépés. A `{commit}` commit két egymást "
            f"követő éjszakán is kifutott a review időkorlátjából; a tulajdonos eldobta "
            f"(futás: {run_id}).\n")
    write_text(path, _with_frontmatter(body, reviewer, parent, commit, {}), 0o644)
    return path


def _num(item_id: str) -> int:
    return int(ITEM_NUM.fullmatch(item_id).group(1))


def read_items(path: Path) -> dict | None:
    """The `items` map of a v2 review file; None for files without it (v1 files, index)."""
    try:
        meta = fm.split(path.read_text(encoding="utf-8")).meta
    except (ValueError, OSError):
        return None
    items = meta.get("items")
    return items if isinstance(items, dict) else None


def review_files(repo: Path) -> list[Path]:
    base = repo / REVIEW_DIR
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.md") if p.name != "index.md")


def open_items(repo: Path, mode: str) -> list[dict]:
    """fetch.json `open_review_items`: cron leaves out `owner` items, interactive keeps them."""
    wanted = (OPEN,) if mode == "cron" else (OPEN, OWNER)
    found = []
    for path in review_files(repo):
        items = read_items(path) or {}
        rel = path.relative_to(repo).as_posix()
        found += [{"file": rel, "item_id": i} for i in sorted(items, key=_num)
                  if items[i] in wanted]
    return found


def open_counts(text: str) -> dict[str, int]:
    """How many times each item stayed open or untouched across all Végrehajtva sections."""
    counts: dict[str, int] = {}
    for section in DONE_HEADING.split(text)[2::2]:
        for m in DONE_LINE.finditer(section):
            if m.group("word") in (WORDS["open"], WORDS["untouched"]):
                counts[m.group("item")] = counts.get(m.group("item"), 0) + 1
    return counts


def _done_section(run_id: str, entries: list[tuple[str, str, str]]) -> str:
    lines = [f"## Végrehajtva ({run_id})", ""]
    for item, status, note in entries:
        word = WORDS[status]
        lines.append(f"* {item} – {word}: {_one_line(note)}" if note else f"* {item} – {word}")
    return "\n".join(lines) + "\n"


def _apply_one(path: Path, run_id: str, closures: dict, listed: list[str],
               owner_after: int) -> list[str]:
    """Update one file; returns its newly-owner items. Idempotent per run id."""
    text = path.read_text(encoding="utf-8")
    if any(m.group("run") == run_id for m in DONE_HEADING.finditer(text)):
        return []
    page = fm.split(text)
    items = dict(page.meta["items"])
    for item_id, c in closures.items():
        if item_id not in items:
            raise ClosureError(f"{path.name}: no item {item_id}")
        if items[item_id] not in (OPEN, OWNER):
            raise ClosureError(f"{path.name}: {item_id} is not open ({items[item_id]})")
    entries = []
    for item_id in sorted(set(closures) | set(listed), key=_num):
        c = closures.get(item_id)
        status = c["status"] if c else "untouched"
        entries.append((item_id, status, c.get("note", "") if c else ""))
        if status in (FIXED, DISAGREE):
            items[item_id] = status
    body = page.body.rstrip("\n") + "\n\n" + _done_section(run_id, entries)
    counts = open_counts(body)
    new_owner = [i for i, s in items.items() if s == OPEN and counts.get(i, 0) >= owner_after]
    for item_id in new_owner:
        items[item_id] = OWNER
    new_text = fm.set_keys(f"---\n{page.raw_meta}\n---\n{body}",
                           {"items": items, "status": compute_status(items)})
    write_text(path, new_text, 0o644)
    return new_owner


def apply_closure(repo: Path, run_id: str, closures: list[dict], listed: list[dict],
                  owner_after: int = 5) -> ClosureOutcome:
    """Apply the merged `review_closure` and the fetch.json item list (plan 4.7, 5.7)."""
    by_file: dict[str, dict] = {}
    for c in closures:
        by_file.setdefault(c["file"], {})[c["item_id"]] = c
    listed_by_file: dict[str, list[str]] = {}
    for item in listed:
        listed_by_file.setdefault(item["file"], []).append(item["item_id"])
    outcome = ClosureOutcome()
    for rel in sorted(set(by_file) | set(listed_by_file)):
        path = repo / rel
        if not rel.startswith("docs/review/") or not path.is_file() or read_items(path) is None:
            raise ClosureError(f"{rel}: not a review file with items")
        owners = _apply_one(path, run_id, by_file.get(rel, {}), listed_by_file.get(rel, []),
                            owner_after)
        outcome.written.append(rel)
        outcome.new_owner += [{"file": rel, "item_id": i} for i in owners]
    return outcome
