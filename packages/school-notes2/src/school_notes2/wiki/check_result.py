"""result.json checks of plan 4.5 (part of `check`), on the merged result of a run."""

from pathlib import Path

from .check import item

RESULT = ".school-notes/result.json"


def check_result(repo: Path, result: dict, fetch: dict, open_items: set[tuple[str, str]],
                 closure_limit: int = 20, whole_run: bool = True) -> list[dict]:
    """`open_items`: {(file, item_id)} the run may close (fetch.json's list).

    `whole_run`: coverage of every page of the run (finish, merged results); False checks
    only the pages of fetch.json's `range` (the writer's MCP check of one range)."""
    out = []
    out += check_coverage(result, fetch, whole_run)
    new = {p["subject"] for p in fetch["packages"] if p.get("new_subject")}
    for s in result.get("new_subjects") or []:
        if s["subject"] not in new:
            out.append(item(RESULT, None, f"new_subjects: {s['subject']!r} is not new in this run"))
    closures = result.get("review_closure") or []
    if len([c for c in closures if c["status"] != "open"]) > closure_limit:
        out.append(item(RESULT, None, f"review_closure: at most {closure_limit} items per run"))
    for c in closures:
        if not (repo / c["file"]).is_file():
            out.append(item(RESULT, None, f"review_closure: {c['file']} does not exist"))
        elif (c["file"], c["item_id"]) not in open_items:
            out.append(item(RESULT, None, f"review_closure: {c['file']} {c['item_id']} is not open"))
    out += check_checks(repo, result, fetch)
    return out


def check_coverage(result: dict, fetch: dict, whole_run: bool = True) -> list[dict]:
    """The notes must cover every non-duplicate page (of the run, or of the range)."""
    wanted = {p["seq"] for p in fetch["pages"] if not p.get("duplicate_of")}
    if not whole_run:
        first, last = fetch["range"]["from"], fetch["range"]["to"]
        wanted = {seq for seq in wanted if first <= seq <= last}
    known = {p["seq"] for p in fetch["pages"]}
    covered: set[int] = set()
    out = []
    for note in result.get("notes") or []:
        covered |= set(note["pages"])
        unknown = sorted(set(note["pages"]) - known)
        if unknown:
            out.append(item(note["file"], None, f"notes.pages: unknown page numbers {unknown}"))
    missing = sorted(wanted - covered)
    if missing and result.get("status") == "done":
        out.append(item(RESULT, None, f"notes: pages {missing} belong to no lesson-notes page"))
    return out


def check_checks(repo: Path, result: dict, fetch: dict) -> list[dict]:
    seqs = {p["seq"] for p in fetch["pages"]}
    out = []
    for n, c in enumerate(result.get("checks") or [], start=1):
        if not (repo / c["page"]).is_file():
            out.append(item(RESULT, None, f"checks[{n}]: page {c['page']} does not exist"))
        image = c["image"]
        if isinstance(image, int) or str(image).isdigit():
            if int(image) not in seqs:
                out.append(item(RESULT, None, f"checks[{n}]: page number {image} is not in this run"))
        elif not (repo / str(image)).is_file() or str(image).startswith(("/", "../")):
            out.append(item(RESULT, None, f"checks[{n}]: image {image!r} is not a file in the repository"))
    return out
