"""publication/public.json, the public site's only release list (plan 4.10).

The public site is a 1:1 image of the wiki: every page, no filtering, no edits.
Files under sources/ and references/ never ship; links to them become citations.
"""

import json
from pathlib import Path
from typing import Callable

from . import generate
from .pages import links, read_page, resolve, sha256, wiki_pages

FIXED = ("version", "mode", "title", "base", "branding", "feedbackRepository", "license", "site")
PRIVATE_PREFIXES = ("sources/", "references/")
SUBJECT_SUFFIX = " — tanulási jegyzet"
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".avif")

# rights(asset_path) -> (rights, evidence path) for an asset the existing file does not know.
RightsLookup = Callable[[str], tuple[str, str] | None]


class PublicError(ValueError):
    """Assets with no known rights class: the `check` stops (plan 4.10, B10)."""

    def __init__(self, paths: list[str]):
        super().__init__("new images with no render.json and no image-ledger record: "
                         + ", ".join(paths))
        self.paths = paths


def page_order(repo: Path) -> list[str]:
    """B7: root index → per subject: index, chapter pages, lessons table, other lists → info pages."""
    order: list[str] = ["wiki/index.md"]
    for slug in generate.subject_order(repo):
        subject = generate.load_subject(repo, slug)
        seq = ["index.md"]
        for chapter in subject.index_meta.get("chapters") or []:
            seq += [p.file for p in generate.chapter_pages(subject, chapter["id"])]
        seq += [page.file for page, _ in generate.lessons(subject)]
        seq += [p.file for p in generate.by_date_desc(subject.by_type("review"))]
        seq += [p.file for p in generate.by_date_desc(subject.by_type("lesson-notes"))]
        seq += [p.file for p in subject.pages]
        order += [f"wiki/{slug}/{f}" for f in dict.fromkeys(seq)]
    rest = [p for p in wiki_pages(repo) if p not in order]
    return order + rest


def page_entry(repo: Path, rel: str) -> dict:
    entry = {"path": rel, "sha256": sha256(repo / rel)}
    parts = rel.split("/")
    if rel == "wiki/index.md":
        entry["navigationLabel"] = "🏠 Kezdőlap"
    elif len(parts) == 3 and parts[2] == "index.md":
        entry["navigationLabel"] = generate.subject_label(repo, parts[1])
    elif len(parts) == 2:
        entry["navigation"] = "info"     # top-level pages such as a-projektrol.md
    return entry


def collections(repo: Path) -> list[dict]:
    """One PDF per chapter page, grouped under the chapter's summary; one per subject (B6)."""
    out = []
    for slug in generate.subject_order(repo):
        subject = generate.load_subject(repo, slug)
        everything = []
        for chapter in subject.index_meta.get("chapters") or []:
            pages = generate.chapter_pages(subject, chapter["id"])
            summary = next((p for p in pages if p.meta.get("type") == "chapter-summary"), None)
            for page in pages:
                item = {"id": f"{slug}-{page.file[:-3]}", "title": page.meta.get("title", page.file),
                        "pages": [f"wiki/{slug}/{page.file}"], "pdf": True}
                if summary and page is not summary:
                    item["group"] = f"{slug}-{summary.file[:-3]}"
                out.append(item)
                everything.append(f"wiki/{slug}/{page.file}")
        if everything:
            out.append({"id": slug, "title": subject.index_title + SUBJECT_SUFFIX, "pages": everything})
    return out


def linked_targets(repo: Path, pages: list[str]) -> tuple[set[str], set[str]]:
    """(images inside wiki/, citation targets under sources/ or references/)."""
    images, citations = set(), set()
    for rel in pages:
        for link in links((repo / rel).read_text(encoding="utf-8")):
            target = resolve(rel, link.target)
            if target is None:
                continue
            if target.startswith(PRIVATE_PREFIXES):
                citations.add(target)
            elif target.startswith("wiki/") and target.lower().endswith(IMAGE_EXT):
                images.add(target)
    return images, citations


def asset_entry(repo: Path, rel: str, known: dict, rights: RightsLookup) -> dict | None:
    entry = {"path": rel, "sha256": sha256(repo / rel)}
    old = known.get(rel)
    if old and old.get("rights"):
        entry["rights"] = old["rights"]
        if old.get("rightsEvidence"):
            entry["rightsEvidence"] = old["rightsEvidence"]
        return entry
    found = rights(rel)
    if found is None:
        return None
    entry["rights"], entry["rightsEvidence"] = found
    return entry


def build(repo: Path, rights: RightsLookup, existing: dict | None = None) -> dict:
    """The full public.json value; `existing` supplies fixed fields and known asset rights."""
    existing = existing if existing is not None else read_existing(repo)
    order = page_order(repo)
    images, citations = linked_targets(repo, order)
    known = {a["path"]: a for a in existing.get("assets", [])}
    value = {k: existing[k] for k in FIXED if k in existing}
    value.setdefault("version", 1)
    value["pages"] = [page_entry(repo, rel) for rel in order]
    assets = {rel: asset_entry(repo, rel, known, rights)
              for rel in sorted(i for i in images if (repo / i).is_file())}
    unknown = [rel for rel, entry in assets.items() if entry is None]
    if unknown:
        raise PublicError(unknown)
    value["assets"] = list(assets.values())
    value["collections"] = collections(repo)
    value["citationOnlyLinks"] = sorted(citations)
    return value


def read_existing(repo: Path) -> dict:
    path = repo / "publication" / "public.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def dumps(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write(repo: Path, rights: RightsLookup) -> bool:
    """Write public.json; True if it changed."""
    path = repo / "publication" / "public.json"
    text = dumps(build(repo, rights))
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def render_rights(repo: Path) -> RightsLookup:
    """Default lookup: an image listed in a render.json `outputs` is the tool-rendered kind."""
    owners: dict[str, str] = {}
    for receipt in (repo / "wiki" / "assets").rglob("render.json"):
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        base = receipt.parent.relative_to(repo).as_posix()
        for out in data.get("outputs") or {}:
            owners[f"{base}/{out}"] = receipt.relative_to(repo).as_posix()

    def lookup(rel: str):
        return ("authored", owners[rel]) if rel in owners else None
    return lookup


def either(*lookups: RightsLookup) -> RightsLookup:
    def lookup(rel: str):
        return next((r for r in (f(rel) for f in lookups) if r), None)
    return lookup
