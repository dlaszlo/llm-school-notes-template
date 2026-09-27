#!/usr/bin/env python3
"""Generate the navigation map (index.md) of a converted reference book.

Usage: uv run tools/book_index.py references/<subject>/<book-id> [--offset N] [--readme]

Use --readme or <!-- book-index: readme --> for a checked README table.
Reader-facing labels come from the local tools/book-index.json.

The map lets an agent open only the lines of document.md it needs instead of
the whole book. It is built from two things that are always there:

* the page anchors in document.md ("element:p013-e002 kind=... page=13", PDF page),
* the lesson / part tables of the book's README.md (first column: name,
  last column: printed start page or printed page range).

Printed page = PDF page - offset. The offset is read from the README
("printed-page offset: N" in the README, or "one less" / "eggyel kisebb" = 1) or given with --offset. The output is regenerated from
scratch every time; never edit index.md by hand.
"""
import json
import re
import sys
from pathlib import Path

ANCHOR = re.compile(r"^<!-- element:p\d+-e\d+ kind=\S+ page=(\d+)")
TABLE = re.compile(r"<table>.*?</table>", re.S)
ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
CELL = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)
SPECIAL = re.compile(
    r"^#{1,4}\s+\**(tartalom|tartalomjegyz[ée]k|t[áa]rgymutat[óo]|sz[óo]jegyz[ée]k|"
    r"fogalomt[áa]r|n[ée]vmutat[óo]|kislexikon|a feladatok v[ée]geredm[ée]nyei|"
    r"megold[áa]sok|irodalomjegyz[ée]k|contents|index|glossary|answers)\b",
    re.IGNORECASE,
)


def page_lines(doc_lines):
    """First line (1-based) of every PDF page, in page order."""
    first = {}
    for n, line in enumerate(doc_lines, 1):
        m = ANCHOR.search(line)
        if m:
            first.setdefault(int(m.group(1)), n)
    return dict(sorted(first.items()))


TOC_MARK = re.compile(r"^(#{1,4}\s+|<!-- PageHeader:\s*)tartalom(jegyz[ée]k)?\b", re.IGNORECASE)


def toc_rows(doc_lines):
    """(name, start, None) rows of the book's own table of contents: the HTML tables
    on the page that carries the "Tartalom" heading and on the next page, whose rows
    are "title | printed page". Chapter rows without a page become (name, None, None)."""
    page, toc_pages, tables, buf, tpage = 0, set(), [], None, 0
    for line in doc_lines:
        m = ANCHOR.search(line)
        if m:
            page = int(m.group(1))
        if TOC_MARK.search(line):
            toc_pages |= {page, page + 1}
        if "<table>" in line and buf is None:
            buf, tpage = [], page
        if buf is not None:
            buf.append(line)
            if "</table>" in line:
                tables.append((tpage, "\n".join(buf)))
                buf = None
    rows = []
    for tp, t in tables:
        if tp not in toc_pages:
            continue
        for r in ROW.findall(t):
            cells = [re.sub(r"<[^>]+>", " ", c) for c in CELL.findall(r)]
            cells = [re.sub(r"(\s*\.){3,}\s*$|(\s*\.){3,}", " ", c) for c in cells]
            cells = [re.sub(r"\s+", " ", c).strip() for c in cells]
            if len(cells) == 2 and re.fullmatch(r"\d{1,3}", cells[1]):
                rows.append((cells[0], int(cells[1]), None))
            elif cells and cells[0] and (len(cells) == 1 or not cells[1]):
                rows.append((cells[0], None, None))
    return rows


def readme_offset(readme):
    if re.search(r"eggyel\s+kisebb|one\s+(less|lower)|printed\s*=\s*PDF\s*-\s*1", readme, re.IGNORECASE):
        return 1
    m = re.search(r"printed-page offset:\s*(\d+)", readme, re.IGNORECASE)
    return int(m.group(1)) if m else None


def readme_rows(readme):
    """(name, start, end) from README tables; end is None for start-only tables."""
    rows = []
    for line in readme.splitlines():
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", cells[-1])
        if not m:
            continue
        name = re.sub(r"\*\*", "", cells[0]).strip()
        rows.append((name, int(m.group(1)), int(m.group(2)) if m.group(2) else None))
    rows = [r for r in rows if r[1] is not None]
    return rows


def line_of_printed(pages, printed, offset):
    """First document line of a printed page (or of the next page that has one)."""
    pdf = printed + offset
    for p, n in pages.items():
        if p >= pdf:
            return n
    return None


def main():
    labels = json.loads((Path(__file__).resolve().parent / "book-index.json").read_text(encoding="utf-8"))["labels"]
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    book = Path(args[0])
    offset = None
    if "--offset" in args:
        offset = int(args[args.index("--offset") + 1])
    doc_lines = (book / "document.md").read_text(encoding="utf-8").split("\n")
    readme = (book / "README.md").read_text(encoding="utf-8")
    if offset is None:
        offset = readme_offset(readme)
    if offset is None:
        sys.exit("printed-page offset not found in README.md; pass --offset N")
    total = len(doc_lines)
    pages = page_lines(doc_lines)
    title = next((l[2:].strip() for l in readme.splitlines() if l.startswith("# ")), book.name)

    out = [
        labels["map"].format(title=title), "", labels["generated"], "",
        labels["intro"].format(total=total, offset=offset), "",
    ]

    rows = toc_rows(doc_lines)
    source = labels["toc"]
    extra = readme_rows(readme)
    if "--readme" in args or "<!-- book-index: readme -->" in readme or sum(1 for r in rows if r[1] is not None) < 5:
        rows, source = extra, labels["readme"]
    else:
        last = max(r[1] for r in rows if r[1] is not None)
        more = [r for r in extra if r[1] > last]
        if more:
            rows += more
            source += labels["completed"]
    max_printed = max(pages) - offset
    if rows:
        out += [labels["lessons"], "", labels["source"].format(source=source), "", labels["columns"], "|---|---|---|"]
        for i, (name, start, end) in enumerate(rows):
            if start is None:
                out.append(f"| **{name}** | | |")
                continue
            if end is None:
                nxt = next((r[1] for r in rows[i + 1:] if r[1] is not None and r[1] > start), None)
                end = nxt - 1 if nxt else max_printed
            a = line_of_printed(pages, start, offset)
            b = line_of_printed(pages, end + 1, offset) if end else None
            b = (b - 1) if b else total
            pages_txt = f"{start}-{end}" if end and end != start else f"{start}" if end else f"{start}-"
            out.append(f"| {name} | {pages_txt} | {a}-{b} |" if a else f"| {name} | {pages_txt} | ? |")
        out.append("")

    specials = [(n, l.lstrip("#").strip().strip("*")) for n, l in enumerate(doc_lines, 1) if SPECIAL.match(l)]
    if specials:
        out += [labels["lists"], "", labels["lists_intro"], ""]
        for n, name in specials:
            out.append(labels["line"].format(name=name, n=n))
        out.append("")

    out += [labels["pages"], "", labels["pages_intro"], ""]
    items = [f"{p - offset}: {n}" for p, n in pages.items() if p - offset >= 1]
    for i in range(0, len(items), 10):
        out.append("* " + " · ".join(items[i:i + 10]))
    out.append("")

    (book / "index.md").write_text("\n".join(out), encoding="utf-8")
    print(labels["result"].format(book=book, rows=len(rows), specials=len(specials), pages=len(items)))


if __name__ == "__main__":
    main()
