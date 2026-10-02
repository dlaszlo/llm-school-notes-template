"""Generated index blocks (plan 4.10): subject indexes and the root index.

Single source of truth: the pages' frontmatter (`chapters` in the subject index,
`chapter`/`order` on pages, `lessons` on lesson-notes pages) and tools/subjects.json.
Output is a pure function of those inputs, so generation is idempotent and byte-stable.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import markers
from .pages import read_page

ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
TABLE_HEAD = "| Dátum | Óra | Jegyzet | Témakörök |\n|---|---|---|---|\n"
SUBJECT_BLOCKS = ("chapters", "lessons", "review", "notes")


@dataclass
class SubjectPage:
    file: str            # file name inside the subject folder
    meta: dict


@dataclass
class Subject:
    slug: str
    index_meta: dict
    index_title: str     # the index's first `# ` heading
    pages: list[SubjectPage] = field(default_factory=list)

    def by_type(self, kind: str) -> list[SubjectPage]:
        return [p for p in self.pages if p.meta.get("type") == kind]

    def page(self, file: str) -> SubjectPage | None:
        return next((p for p in self.pages if p.file == file), None)


def load_subject(repo: Path, slug: str) -> Subject:
    folder = repo / "wiki" / slug
    index = read_page(folder / "index.md")
    heading = next((ln[2:].strip() for ln in index.body.splitlines() if ln.startswith("# ")), slug)
    subject = Subject(slug, index.meta, heading)
    for path in sorted(folder.glob("*.md")):
        if path.name != "index.md":
            subject.pages.append(SubjectPage(path.name, read_page(path).meta))
    return subject


def chapter_pages(subject: Subject, chapter_id: str) -> list[SubjectPage]:
    inside = [p for p in subject.pages if p.meta.get("chapter") == chapter_id]
    return sorted(inside, key=lambda p: (p.meta.get("order", 0), p.file))


def list_line(page: SubjectPage) -> str:
    bolt = "⚡ " if page.meta.get("type") == "chapter-summary" else ""
    return f"* {bolt}[{page.meta.get('title', page.file)}]({page.file}) - {page.meta.get('description', '')}"


def chapters_block(subject: Subject) -> str:
    sections = []
    for chapter in subject.index_meta.get("chapters") or []:
        lines = "\n".join(list_line(p) for p in chapter_pages(subject, chapter["id"]))
        sections.append(f"# 📘 {chapter['title']}\n\n{lines}\n" if lines else f"# 📘 {chapter['title']}\n")
    return "\n<br />\n\n".join(sections)


def lesson_date(lesson: dict) -> str:
    """The table's Dátum cell: the notebook date, or `?` with the range it must fall in."""
    date, note = lesson.get("date"), lesson.get("date_note")
    if date:
        return f"{date}; {note}" if note else str(date)
    return f"? ({note})" if note else "?"


def lesson_sort_key(page: SubjectPage, index: int, lesson: dict) -> tuple:
    # Undated lessons sort by the latest date their range allows (the wiki's own rule).
    dates = ISO.findall(str(lesson.get("date") or "")) or ISO.findall(lesson.get("date_note") or "")
    return (max(dates) if dates else "", page.file[:10], index)


def lessons(subject: Subject) -> list[tuple[SubjectPage, dict]]:
    """Every lesson of the subject, newest first."""
    rows = []
    for page in subject.by_type("lesson-notes"):
        for i, lesson in enumerate(page.meta.get("lessons") or []):
            rows.append((lesson_sort_key(page, i, lesson), page, lesson))
    rows.sort(key=lambda r: r[0], reverse=True)
    return [(page, lesson) for _, page, lesson in rows]


def topic_link(subject: Subject, topic: str) -> str:
    """`[title](file.md#anchor)`; the title always comes from the page itself."""
    target = subject.page(topic.split("#", 1)[0])
    title = target.meta.get("title", topic) if target else topic
    return f"[{title}]({topic})"


def lessons_block(subject: Subject) -> str:
    rows = []
    for page, lesson in lessons(subject):
        topics = ", ".join(topic_link(subject, t) for t in lesson.get("topics") or [])
        rows.append(f"| {lesson_date(lesson)} | {lesson.get('title', '')} | "
                    f"[jegyzet]({page.file}) | {topics} |")
    return TABLE_HEAD + "".join(r + "\n" for r in rows)


def by_date_desc(pages: list[SubjectPage]) -> list[SubjectPage]:
    ordered = sorted(pages, key=lambda p: p.file)
    return sorted(ordered, key=lambda p: p.file[:10], reverse=True)


def review_block(subject: Subject) -> str:
    pages = by_date_desc(subject.by_type("review"))
    if not pages:
        return ""
    lines = "\n".join(list_line(p) for p in pages)
    return f"# 🔁 Ismétlés\n\n{lines}\n\n<br />\n\n"


def notes_block(subject: Subject) -> str:
    pages = by_date_desc(subject.by_type("lesson-notes"))
    if not pages:
        return ""
    return "# 📝 Jegyzetek\n\n" + "\n".join(list_line(p) for p in pages) + "\n"


def subject_index(repo: Path, slug: str) -> str:
    """The subject index text with every generated block refreshed."""
    path = repo / "wiki" / slug / "index.md"
    text = path.read_text(encoding="utf-8")
    subject = load_subject(repo, slug)
    bodies = {"chapters": chapters_block(subject), "lessons": lessons_block(subject),
              "review": review_block(subject), "notes": notes_block(subject)}
    for name in markers.names(text):
        if name in bodies:
            text = markers.replace(text, name, bodies[name])
    return text


def subject_order(repo: Path) -> list[str]:
    """subjects.json order (new subjects are appended), then any other subject folder."""
    known = list(load_subjects_json(repo).get("subjects", {}))
    folders = {p.parent.name for p in (repo / "wiki").glob("*/index.md")} - {"assets"}
    return [s for s in known if s in folders] + sorted(folders - set(known))


def load_subjects_json(repo: Path) -> dict:
    path = repo / "tools" / "subjects.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"subjects": {}}


def subject_sentence(name: str) -> str:
    article = "Az" if name[:1].lower() in "aáeéiíoóöőuúüű" else "A"
    return f"{article} {name.lower()} tantárgy témakörei és jegyzetei, évfolyamonként."


def subject_label(repo: Path, slug: str) -> str:
    entry = load_subjects_json(repo).get("subjects", {}).get(slug, {})
    name = entry.get("name", slug)
    return f"{entry['emoji']} {name}" if entry.get("emoji") else name


def root_block(repo: Path) -> str:
    lines = []
    subjects = load_subjects_json(repo).get("subjects", {})
    for slug in subject_order(repo):
        entry = subjects.get(slug, {})
        name = entry.get("name", slug)
        emoji = f"{entry['emoji']} " if entry.get("emoji") else ""
        meta = read_page(repo / "wiki" / slug / "index.md").meta
        lines.append(f"* {emoji}[{name}]({slug}/index.md) - "
                     f"{meta.get('description') or subject_sentence(name)}")
    return "".join(ln + "\n" for ln in lines)


def root_index(repo: Path) -> str:
    text = (repo / "wiki" / "index.md").read_text(encoding="utf-8")
    if "subjects" in markers.names(text):
        text = markers.replace(text, "subjects", root_block(repo))
    return text


def write_indexes(repo: Path) -> list[str]:
    """Refresh every index; returns the repo-relative paths that changed."""
    changed = []
    targets = [(f"wiki/{s}/index.md", lambda s=s: subject_index(repo, s)) for s in subject_order(repo)]
    targets.append(("wiki/index.md", lambda: root_index(repo)))
    for rel, build in targets:
        path = repo / rel
        old = path.read_text(encoding="utf-8")
        new = build()
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed.append(rel)
    return changed
