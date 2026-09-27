#!/usr/bin/env python3
"""Bounded navigation of immutable curriculum snapshots; Python standard library only.

Run from the repository root. Build writes derived indexes only, never source files.
Search previews locate evidence; they are not sufficient for interpreting table cells.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "references/curriculum"
ANCHOR = re.compile(r"^<!-- element:(\S+) kind=(\S+) page=(\d+) -->", re.M)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog():
    if ROOT != ROOT.resolve():
        raise ValueError("Refusing symlink in curriculum directory ancestry")
    return json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def checked(entry):
    if ROOT != ROOT.resolve() or not re.fullmatch(r"[a-z0-9-]+", entry["id"]):
        raise ValueError("Use a local curriculum directory and an ASCII document ID")
    if set(entry["files"]) != {"document.md", "manifest.json", "provenance.json"}:
        raise ValueError("Unexpected snapshot file set")
    folder = ROOT / entry["id"]
    if folder.is_symlink() or not folder.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Snapshot must be an in-repository ordinary directory")
    for name, expected in entry["files"].items():
        path = folder / name
        if path.is_symlink() or digest(path) != expected:
            raise ValueError(f"Source integrity mismatch: {entry['id']}/{name}")
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
    if not (manifest["source"]["sha256"] == provenance["source_sha256"] == entry["source_pdf_sha256"]):
        raise ValueError("Mismatched source identities")
    if manifest["run"]["run_id"] != provenance["run_id"]:
        raise ValueError("Mismatched conversion runs")
    blocks = elements((folder / "document.md").read_text(encoding="utf-8"))
    ids = [e["id"] for e in blocks]
    supplied = [e["id"] for e in provenance["elements"]]
    if len(set(ids)) != len(ids) or len(set(supplied)) != len(supplied) or set(ids) != set(supplied):
        raise ValueError("Missing or duplicate element identities")
    page_count = manifest["source"]["pdf_pages"]
    if page_count != provenance["page_count"] or any(not 1 <= e["page"] <= page_count for e in blocks):
        raise ValueError("Invalid page coverage")
    return folder


def elements(text):
    matches = list(ANCHOR.finditer(text))
    if not matches:
        raise ValueError("No element anchors; manual navigation is needed")
    result = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end].strip()
        result.append({"id": match[1], "kind": match[2], "page": int(match[3]),
                       "start": match.start(), "end": end,
                       "line_start": text.count("\n", 0, match.start()) + 1,
                       "line_end": text.count("\n", 0, end), "body": body})
    return result


def index_text(entry, text):
    out = [f"# {entry['title']}", "", "Generated navigation, not verified requirements or proof of applicability.", "",
           f"document.md SHA-256: `{entry['files']['document.md']}`", "",
           "Read relevant complete elements in document.md. PDF page numbers below are converter locations; preserve printed labels separately.", "",
           "| Element | PDF page | Lines | Heading or block |", "|---|---|---|---|"]
    for e in elements(text):
        numbered = e["kind"] == "paragraph" and re.match(r"^\d+(?:\.\d+){2,}\.?\s", e["body"])
        if e["kind"] not in {"section_heading", "table", "figure"} and not numbered:
            continue
        label = e["body"].splitlines()[0].lstrip("# ") if e["kind"] == "section_heading" or numbered else e["kind"]
        label = label.replace("|", "\\|")[:180]
        out.append(f"| `{e['id']}` | {e['page']} | {e['line_start']}-{e['line_end']} | {label} |")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "check", "search", "read"])
    parser.add_argument("--document", help="ID from references/curriculum/index.md")
    parser.add_argument("--query", help="Literal case-insensitive search term")
    parser.add_argument("--element", help="Exact element ID for read")
    parser.add_argument("--lines", help="Optional inclusive START:END within the selected element; explicitly partial evidence")
    parser.add_argument("--limit", type=int, default=8, help="Search results, 1-12")
    parser.add_argument("--max-chars", type=int, default=12000, help="Read bound, 1-24000 Unicode characters")
    args = parser.parse_args()
    entries = catalog()["documents"]
    if args.document:
        entries = [e for e in entries if e["id"] == args.document]
        if not entries:
            parser.error("Unknown document ID")
    if args.command in {"search", "read"} and not args.document:
        parser.error("Select one --document from the compact catalog first")
    if not 1 <= args.limit <= 12 or not 1 <= args.max_chars <= 24000:
        parser.error("Invalid output bound")
    if args.command == "search" and not args.query:
        parser.error("search needs --query")
    if args.command == "read" and not args.element:
        parser.error("read needs --element")
    if args.lines and (args.command != "read" or not re.fullmatch(r"\d+:\d+", args.lines)):
        parser.error("--lines needs read and START:END")
    for entry in entries:
        folder = checked(entry)
        text = (folder / "document.md").read_text(encoding="utf-8")
        expected = index_text(entry, text)
        index = folder / "index.md"
        if index.is_symlink():
            raise ValueError("Refusing a symlink index")
        if args.command == "build":
            index.write_text(expected, encoding="utf-8")
        elif args.command == "check":
            if not index.exists() or index.read_text(encoding="utf-8") != expected:
                raise ValueError(f"Stale index: {entry['id']}; run build")
        else:
            if not index.exists() or index.read_text(encoding="utf-8") != expected:
                raise ValueError("Stale navigation; run build before using locations")
            blocks = elements(text)
            if args.command == "search":
                hits = []
                for e in blocks:
                    body = e["body"]
                    pos = body.casefold().find(args.query.casefold())
                    if pos >= 0:
                        preview = re.sub(r"\s+", " ", body[max(0, pos - 50):pos + 180])
                        hits.append({k: e[k] for k in ["id", "kind", "page", "line_start", "line_end"]} | {"preview": preview})
                print(json.dumps({"document": entry["id"], "sha256": entry["files"]["document.md"],
                                  "total_hits": len(hits), "truncated": len(hits) > args.limit,
                                  "hits": hits[:args.limit], "warning": "Navigation only. No hit is not proof of absence. Read complete table and level headers."}, ensure_ascii=False, indent=2))
            else:
                found = [e for e in blocks if e["id"] == args.element]
                if not found:
                    raise ValueError("Unknown element")
                e = found[0]
                content = text[e["start"]:e["end"]]
                location = f"lines {e['line_start']}-{e['line_end']}"
                if args.lines:
                    first, last = map(int, args.lines.split(":"))
                    if not e["line_start"] <= first <= last <= e["line_end"]:
                        raise ValueError("Line range must stay inside the selected element")
                    content = "\n".join(text.splitlines()[first - 1:last]) + "\n"
                    location = f"PARTIAL lines {first}-{last} of element lines {e['line_start']}-{e['line_end']}. Read headers, whole row, inherited cells and continuations separately before interpreting; this fragment is not a complete-table check."
                if len(content) > args.max_chars:
                    raise ValueError(f"Element has {len(content)} characters, exceeds bound. Lines {e['line_start']}-{e['line_end']}. Use bounded line reads with table headers, full row and inherited/continued cells; never infer a level from a fragment.")
                print(f"Document {entry['id']}; SHA-256 {entry['files']['document.md']}; {location}\n{content}")
    if args.command in {"build", "check"}:
        print(f"{args.command}: {len(entries)} snapshots; sources unchanged")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit(str(exc))
