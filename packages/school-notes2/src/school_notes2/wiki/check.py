"""The mechanical `check` of plan 5.4/5 on markdown files.

Fixes what is unambiguous (line endings, final newline) and returns the rest as
check.json items `{file, line, message, severity}`; errors send the run back to the
writer, warnings do not.
"""

import json
import re
from pathlib import Path

from . import frontmatter, markers
from .pages import CODE_FENCE, links, resolve, sha256

SIZE_WARN = 40 * 1024
TYPES_WITH_CHAPTER = ("topic", "chapter-summary")
KNOWN_TYPES = ("topic", "chapter-summary", "lesson-notes", "review", "source-summary",
               "concept", "entity", "question")
# Secrets and machine paths only (4.10): footnotes naming photos ship 1:1 now.
SECRET_PATTERNS = (
    r"/home/", r"file://", r"OPENROUTER_API_KEY", r"client_secret_", r"Claude-Session:",
    r"\bsk-or-v1-[0-9a-f]{16,}", r"\bsk-ant-[A-Za-z0-9_-]{16,}", r"\bsk-[A-Za-z0-9]{32,}",
    r"\bghp_[A-Za-z0-9]{30,}", r"\bgithub_pat_[A-Za-z0-9_]{20,}", r"\bAIza[0-9A-Za-z_-]{35}",
    r"\bya29\.[0-9A-Za-z_-]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\b1//0[0-9A-Za-z_-]{20,}",
)
CONFLICT = re.compile(r"^(<<<<<<<|>>>>>>>)( |$)", re.M)
TAG = re.compile(r"^(?=.*[a-z])[a-z0-9-]+(/[a-z0-9-]+)*$")
FILE_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TYPOGRAPHY = re.compile("[–—“”‘’]")


def item(file: str, line: int | None, message: str, severity: str = "error") -> dict:
    return {"file": file, "line": line, "message": message, "severity": severity}


def autofix(path: Path) -> bool:
    """CRLF to LF and a final newline: unambiguous, so the tool fixes them itself."""
    data = path.read_bytes()
    fixed = data.replace(b"\r\n", b"\n")
    if fixed and not fixed.endswith(b"\n"):
        fixed += b"\n"
    if fixed != data:
        path.write_bytes(fixed)
        return True
    return False


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def check_text(rel: str, text: str) -> list[dict]:
    """Content-independent rules: conflict markers, block markers, secrets, size, formulas."""
    out = []
    for m in CONFLICT.finditer(text):
        out.append(item(rel, line_of(text, m.start()), "unresolved conflict marker"))
    try:
        markers.check(text)
    except markers.MarkerError as exc:
        out.append(item(rel, None, str(exc)))
    for pattern in SECRET_PATTERNS:
        m = re.search(pattern, text, re.I)
        if m:
            out.append(item(rel, line_of(text, m.start()),
                            f"forbidden secret or machine-path pattern {pattern!r}"))
    if len(text.encode()) > SIZE_WARN:
        out.append(item(rel, None, "page is over 40 KB; consider splitting it", "warning"))
    out += check_formulas(rel, text)
    if TYPOGRAPHY.search(CODE_FENCE.sub("", _body(text))):
        out.append(item(rel, None, "typographic dash or quote; the wiki uses ASCII punctuation "
                                   "outside verbatim quotes", "warning"))
    return out


def _body(text: str) -> str:
    try:
        return frontmatter.split(text).body
    except Exception:
        return text


def check_formulas(rel: str, text: str) -> list[dict]:
    """Display-math delimiters must pair up; the build compiles the formulas themselves."""
    body = CODE_FENCE.sub("", text)
    body = re.sub(r"`[^`\n]*`", "", body)
    if body.count("$$") % 2:
        return [item(rel, None, "unbalanced $$ display-math delimiter")]
    if body.count("\\[") != body.count("\\]") or body.count("\\(") != body.count("\\)"):
        return [item(rel, None, "unbalanced \\[ \\] or \\( \\) math delimiter")]
    return []


def check_links(repo: Path, rel: str, text: str) -> list[dict]:
    out = []
    for link in links(text):
        target = link.target
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("/") or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
            out.append(item(rel, link.line, f"absolute or non-relative link {target!r}"))
            continue
        resolved = resolve(rel, target)
        if resolved is None:
            out.append(item(rel, link.line, f"link leaves the repository: {target!r}"))
        elif link.image and resolved.startswith("sources/"):
            out.append(item(rel, link.line, "a source image may not be embedded; link it instead"))
        elif target.endswith("/") or (repo / resolved).is_dir():
            out.append(item(rel, link.line, f"link to a directory {target!r}; link its index.md"))
        elif not (repo / resolved).is_file():
            out.append(item(rel, link.line, f"link target does not exist: {target!r}"))
    return out


def chapter_ids(repo: Path, rel: str) -> set[str] | None:
    index = repo / Path(rel).parent / "index.md"
    if not index.is_file():
        return None
    chapters = frontmatter.split(index.read_text(encoding="utf-8")).meta.get("chapters") or []
    return {c.get("id") for c in chapters if isinstance(c, dict)}


def check_meta(repo: Path, rel: str, meta: dict) -> list[dict]:
    """Frontmatter rules by page type (plan 4.9; wiki-structure)."""
    name = Path(rel).name
    if name == "index.md":
        return check_index_meta(rel, meta)
    if rel == "wiki/log.md" or rel.startswith("wiki/assets/"):
        return []
    if rel.count("/") < 2:
        return []        # top-level info pages (a-projektrol.md) are free-form
    out = [item(rel, None, f"frontmatter {key!r} missing") for key in ("type", "title", "description")
           if not isinstance(meta.get(key), str) or not meta.get(key).strip()]
    if not FILE_NAME.match(name):
        out.append(item(rel, None, "file names are accent-free lowercase kebab-case"))
    kind = meta.get("type")
    if kind and kind not in KNOWN_TYPES:
        out.append(item(rel, None, f"unknown page type {kind!r}", "warning"))
    for tag in meta.get("tags") or []:
        if not isinstance(tag, str) or not TAG.match(tag):
            out.append(item(rel, None, f"tag {tag!r} must be lowercase kebab-case, not numeric"))
    if kind in TYPES_WITH_CHAPTER:
        out += check_chapter(repo, rel, meta)
    if kind == "lesson-notes":
        out += check_lessons(repo, rel, meta)
    return out


def check_index_meta(rel: str, meta: dict) -> list[dict]:
    if rel == "wiki/index.md":
        return []
    chapters = meta.get("chapters")
    if not isinstance(chapters, list):
        return [item(rel, None, "subject index needs a `chapters` list")]
    out, seen = [], set()
    for c in chapters:
        if not isinstance(c, dict) or not re.fullmatch(r"[a-z0-9-]+", str(c.get("id", ""))) \
                or not str(c.get("title", "")).strip():
            out.append(item(rel, None, f"chapter entry {c!r} needs an `id` (kebab-case) and a `title`"))
        elif c["id"] in seen:
            out.append(item(rel, None, f"chapter id {c['id']!r} appears twice"))
        else:
            seen.add(c["id"])
    return out


def check_chapter(repo: Path, rel: str, meta: dict) -> list[dict]:
    out = []
    ids = chapter_ids(repo, rel)
    if meta.get("chapter") is None:
        out.append(item(rel, None, "`chapter` missing (an id from the subject index `chapters`)"))
    elif ids is not None and meta["chapter"] not in ids:
        out.append(item(rel, None, f"chapter {meta['chapter']!r} is not in the subject index"))
    if not isinstance(meta.get("order"), int) or isinstance(meta.get("order"), bool):
        out.append(item(rel, None, "`order` missing or not an integer (10, 20, ...)"))
    return out


def check_lessons(repo: Path, rel: str, meta: dict) -> list[dict]:
    lessons = meta.get("lessons")
    if not isinstance(lessons, list):
        return [item(rel, None, "`lessons` list missing")]
    out = []
    folder = repo / Path(rel).parent
    for n, lesson in enumerate(lessons, start=1):
        if not isinstance(lesson, dict) or not str(lesson.get("title", "")).strip():
            out.append(item(rel, None, f"lesson {n}: `title` missing"))
            continue
        if lesson.get("date") and not ISO.match(str(lesson["date"])):
            out.append(item(rel, None, f"lesson {n}: `date` must be YYYY-MM-DD"))
        for topic in lesson.get("topics") or []:
            if not (folder / str(topic).split("#", 1)[0]).is_file():
                out.append(item(rel, None, f"lesson {n}: topic page {topic!r} does not exist"))
    return out


def check_renders(repo: Path) -> list[dict]:
    """render.json must still describe its source and outputs (no re-rendering here)."""
    out = []
    for receipt in sorted((repo / "wiki" / "assets").rglob("render.json")):
        rel = receipt.relative_to(repo).as_posix()
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
        except ValueError:
            out.append(item(rel, None, "render.json is not valid JSON"))
            continue
        source = repo / str(data.get("source", ""))
        if not source.is_file() or sha256(source) != data.get("source_sha256"):
            out.append(item(rel, None, "the figure source changed after rendering; render again"))
        for name, info in (data.get("outputs") or {}).items():
            output = receipt.parent / name
            if not output.is_file() or sha256(output) != (info or {}).get("sha256"):
                out.append(item(rel, None, f"rendered output {name!r} differs from render.json"))
    return out


def check_files(repo: Path, paths: list[str]) -> list[dict]:
    """Check the given repo-relative markdown files (the run's changes) and every render.json."""
    out = []
    for rel in sorted(set(paths)):
        path = repo / rel
        if not rel.endswith(".md") or not path.is_file():
            continue
        autofix(path)
        text = path.read_text(encoding="utf-8")
        out += check_text(rel, text)
        try:
            page = frontmatter.split(text)
        except Exception as exc:
            out.append(item(rel, 1, f"frontmatter is not valid YAML: {exc}"))
            continue
        if rel.startswith("wiki/"):
            out += check_meta(repo, rel, page.meta)
        out += check_links(repo, rel, text)
    return out + check_renders(repo)


def errors(items: list[dict]) -> list[dict]:
    return [i for i in items if i.get("severity", "error") == "error"]
