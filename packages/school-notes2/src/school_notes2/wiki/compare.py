"""T1 (plan 12): compare the regenerated indexes and public.json with today's files.

The migration script runs this on a migrated copy; the result is either "identical" or
the exact difference list the owner approves (plan 11/3).
"""

import difflib
import json
from pathlib import Path

from . import frontmatter, markers, public


def _body(text: str, keep_frontmatter: bool) -> str:
    return text if keep_frontmatter else frontmatter.split(text).body


def index_diffs(original: Path, migrated: Path) -> dict[str, str]:
    """Unified diffs of every index, marker lines and added frontmatter left out."""
    out = {}
    for path in sorted((original / "wiki").glob("**/index.md")):
        rel = path.relative_to(original).as_posix()
        if "/assets/" in rel:
            continue
        root = rel == "wiki/index.md"
        old = _body(path.read_text(encoding="utf-8"), root)
        new = markers.strip(_body((migrated / rel).read_text(encoding="utf-8"), root))
        if old != new:
            out[rel] = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                    rel, rel, n=0))
    return out


def reference_list(original: Path) -> dict:
    """Today's full release list: pilot.json (all pages) if present, else public.json."""
    pub = original / "publication"
    for name in ("pilot.json", "public.json"):
        if (pub / name).exists():
            return json.loads((pub / name).read_text(encoding="utf-8"))
    return {}


def publication_diffs(original: Path, value: dict) -> list[str]:
    ref = reference_list(original)
    out = []
    old_pages = [p["path"] for p in ref.get("pages", [])]
    new_pages = [p["path"] for p in value["pages"]]
    for path in sorted(set(old_pages) ^ set(new_pages)):
        out.append(f"page {'added' if path in new_pages else 'missing'}: {path}")
    if old_pages != new_pages and set(old_pages) == set(new_pages):
        out += [f"page order: {line.rstrip()}" for line in difflib.unified_diff(
            old_pages, new_pages, lineterm="", n=0)
            if line[:1] in "+-" and not line.startswith(("+++", "---"))]
    old_cols = {c["id"]: c for c in ref.get("collections", [])}
    new_cols = {c["id"]: c for c in value["collections"]}
    for cid in sorted(set(old_cols) | set(new_cols)):
        if old_cols.get(cid) != new_cols.get(cid):
            out.append(f"collection {cid}: {old_cols.get(cid)} -> {new_cols.get(cid)}")
    if [c["id"] for c in ref.get("collections", [])] != [c["id"] for c in value["collections"]] \
            and set(old_cols) == set(new_cols):
        out.append("collection order differs")
    old_assets = {a["path"]: a.get("rights") for a in ref.get("assets", [])}
    new_assets = {a["path"]: a.get("rights") for a in value["assets"]}
    for path in sorted(set(old_assets) | set(new_assets)):
        if old_assets.get(path) != new_assets.get(path):
            out.append(f"asset {path}: {old_assets.get(path)} -> {new_assets.get(path)}")
    return out


def report(original: Path, migrated: Path, rights: public.RightsLookup) -> dict:
    """{"indexes": {path: diff}, "publication": [lines], "unknown_assets": [paths]}."""
    existing = dict(public.read_existing(migrated))
    ref = reference_list(original)
    existing["assets"] = ref.get("assets", []) + existing.get("assets", [])
    unknown: list[str] = []
    try:
        value = public.build(migrated, rights, existing)
    except public.PublicError as exc:
        unknown = exc.paths
        value = public.build(migrated, public.either(rights, lambda rel: ("unknown", "")), existing)
    return {"indexes": index_diffs(original, migrated),
            "publication": publication_diffs(original, value), "unknown_assets": unknown}
