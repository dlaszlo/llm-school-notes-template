"""Duplicate pages (plan 4.2): a page already recorded in the wiki is not stored again.

Rule 1 compares the uploaded file's hash (for a PDF page: PDF hash + page number), rule 2 the
stored image's hash. The wiki keeps both in the machine frontmatter of the lesson-notes pages
(`original_sha256`, `content_sha256`); any value shaped like a hash counts, whatever the map
key, so v1 maps (`01.jpg: <hash>`) and v2 entries are both recognised.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..wiki import frontmatter

HASH = re.compile(r"^[0-9a-f]{64}(#p[0-9]+)?$")


def original_key(sha256: str, page: int | None) -> str:
    """How an original is recorded: the file hash, plus `#p<n>` for a PDF page."""
    return sha256 if page is None else f"{sha256}#p{page}"


@dataclass
class Known:
    content: dict[str, str] = field(default_factory=dict)   # hash -> where it was seen
    original: dict[str, str] = field(default_factory=dict)

    def match(self, original: str, content: str) -> str | None:
        return self.original.get(original) or self.content.get(content)

    def add(self, original: str, content: str, where: str) -> None:
        self.original.setdefault(original, where)
        self.content.setdefault(content, where)


def known_hashes(repo: Path) -> Known:
    known = Known()
    for page in sorted((repo / "wiki").rglob("*.md")):
        try:
            meta = frontmatter.split(page.read_text(encoding="utf-8")).meta
        except (ValueError, UnicodeDecodeError, yaml.YAMLError):  # broken pages: the check's job
            continue
        where = page.relative_to(repo).as_posix()
        for value in _hashes(meta.get("content_sha256")):
            known.content.setdefault(value, where)
        for value in _hashes(meta.get("original_sha256")):
            known.original.setdefault(value, where)
    return known


def _hashes(value):
    if isinstance(value, str):
        if HASH.match(value.strip()):
            yield value.strip()
    elif isinstance(value, dict):
        for item in value.values():
            yield from _hashes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _hashes(item)
