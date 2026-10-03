"""Stable order of what the writer keeps in frontmatter: a cron run may add
items, but the relative order of existing ones may not change between runs. Deliberate
re-ordering happens only in an interactive session, under the owner's direction."""

from . import frontmatter


def _relative(old: list, new: list) -> bool:
    """Do the items present in both lists keep their relative order?"""
    common = [x for x in new if x in old]
    return common == [x for x in old if x in common]


def _lesson_key(lesson) -> tuple:
    if not isinstance(lesson, dict):
        return (repr(lesson),)
    return (str(lesson.get("date") or lesson.get("date_note") or ""), str(lesson.get("title", "")))


def problems(rel: str, old_text: str, new_text: str) -> list[str]:
    """Messages for every reordering of existing items between two versions of a page."""
    try:
        old, new = frontmatter.split(old_text).meta, frontmatter.split(new_text).meta
    except Exception:  # noqa: BLE001 - unreadable frontmatter is the check's own error
        return []
    out = []
    old_ch = [c.get("id") for c in old.get("chapters") or [] if isinstance(c, dict)]
    new_ch = [c.get("id") for c in new.get("chapters") or [] if isinstance(c, dict)]
    if not _relative(old_ch, new_ch):
        out.append("the order of existing chapters changed; add new chapters without moving "
                   "the old ones")
    old_ls, new_ls = old.get("lessons") or [], new.get("lessons") or []
    if not _relative([_lesson_key(x) for x in old_ls], [_lesson_key(x) for x in new_ls]):
        out.append("the order of existing lessons changed")
    old_by = {_lesson_key(x): x for x in old_ls if isinstance(x, dict)}
    for lesson in new_ls:
        before = old_by.get(_lesson_key(lesson))
        if before and isinstance(lesson, dict) and not _relative(
                list(before.get("topics") or []), list(lesson.get("topics") or [])):
            out.append(f"the order of the topics of lesson {lesson.get('title')!r} changed")
    if "order" in old and "order" in new and old["order"] != new["order"]:
        out.append(f"`order` of an existing page changed ({old['order']} → {new['order']})")
    return out
