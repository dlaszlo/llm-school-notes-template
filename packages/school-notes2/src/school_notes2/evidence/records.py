"""Per-page evidence records (plan 4.8): append-only, at a place computed from the page.

`wiki/<subject>/<page>.md` → `docs/evidence/pages/<subject>/<page>.md`. Each entry is the LLM's
description plus what the tool computes: image path, SHA-256, source page, time, checker, run.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from ..state.files import write_text

PAGES_DIR = PurePosixPath("docs/evidence/pages")


class RecordError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    """One check, normalised from a writer `checks` item or a reviewer `figures` item."""

    page: str
    image: str | int
    locator: str
    observed: str
    decision: str
    note: str = ""
    checks: dict | None = None


def record_path(page: str) -> PurePosixPath:
    rel = PurePosixPath(page)
    if rel.parts[:1] != ("wiki",) or rel.suffix != ".md" or ".." in rel.parts:
        raise RecordError(f"{page}: not a wiki page")
    return PAGES_DIR.joinpath(*rel.parts[1:])


def from_writer(checks: list[dict]) -> list[Entry]:
    return [Entry(c["page"], c["image"], c["locator"], c["observed"], c["decision"],
                  c.get("note", "")) for c in checks]


def from_reviewer(figures: list[dict]) -> list[Entry]:
    return [Entry(f["page"], f["file"], f["file"], f["observed"], f["verdict"],
                  f.get("description", ""), f.get("checks")) for f in figures]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(repo: Path, image, pages_by_seq: dict[int, dict]) -> tuple[str, str, str]:
    """(repo path, sha256, source note) of a check's image: a seq or a repo-internal path."""
    if isinstance(image, int) or (isinstance(image, str) and image.isdigit()):
        page = pages_by_seq.get(int(image))
        if page is None:
            raise RecordError(f"image {image}: no such page in fetch.json")
        where = page["file"] + (f", {page['page']}. oldal" if page.get("page") else "")
        rel = page["path"]
        source = f"{page['package']} / {where}"
    else:
        rel, source = str(image), ""
    pure = PurePosixPath(rel)
    target = (repo / rel).resolve()
    if pure.is_absolute() or ".." in pure.parts or not target.is_relative_to(repo.resolve()):
        raise RecordError(f"{rel}: image outside the repository")
    if not target.is_file():
        raise RecordError(f"{rel}: image does not exist")
    return rel, _sha256(target), source


def _one_line(text: str) -> str:
    return " ".join(str(text).split())


def _section(repo: Path, entries: list[Entry], heading: str,
             pages_by_seq: dict[int, dict]) -> str:
    lines = [heading, ""]
    for e in entries:
        rel, digest, source = _resolve(repo, e.image, pages_by_seq)
        lines.append(f"* Kép: `{rel}` (sha256 `{digest}`)")
        if source:
            lines.append(f"  * Forrás: {_one_line(source)}")
        lines += [f"  * Hely: {_one_line(e.locator)}", f"  * Döntés: {e.decision}",
                  f"  * Megfigyelés: {_one_line(e.observed)}"]
        if e.note:
            lines.append(f"  * Megjegyzés: {_one_line(e.note)}")
        if e.checks:
            lines.append(f"  * Ellenőrzések: `{json.dumps(e.checks, ensure_ascii=False)}`")
    return "\n".join(lines) + "\n"


def append(repo: Path, entries: list[Entry], *, run_id: str, checker: str, at: str,
           fetch_pages: list[dict] | None = None) -> list[str]:
    """Append one section per page for this run; returns the written repo paths.

    Idempotent: a page that already has this run's section is left alone (finish reruns).
    """
    pages_by_seq = {p["seq"]: p for p in fetch_pages or []}
    by_page: dict[str, list[Entry]] = {}
    for e in entries:
        by_page.setdefault(e.page, []).append(e)
    written = []
    for page, group in sorted(by_page.items()):
        rel = record_path(page)
        path = repo / rel
        marker = f"– {run_id} – {checker}"
        old = path.read_text(encoding="utf-8") if path.exists() else f"# Bizonyítékrekord: {page}\n"
        if any(line.startswith("## ") and line.endswith(marker) for line in old.splitlines()):
            continue
        section = _section(repo, group, f"## {at} {marker}", pages_by_seq)
        write_text(path, old.rstrip("\n") + "\n\n" + section, 0o644)
        written.append(rel.as_posix())
    return written
