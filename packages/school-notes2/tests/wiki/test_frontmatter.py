from school_notes2.wiki import frontmatter as fm

PAGE = """---
type: lesson-notes
title: "Óra: termelés"
description: Hosszú leírás - kötőjellel.
lessons:
  - { date: 2026-09-25, title: Termelés }
generated: { by: codex, at: "2026-09-29T02:14:59+02:00" }
---

# Cím
"""


def test_split_reads_meta_and_body():
    page = fm.split(PAGE)
    assert page.meta["title"] == "Óra: termelés"
    assert page.body == "\n# Cím\n"


def test_set_keys_keeps_other_blocks_byte_identical():
    out = fm.set_keys(PAGE, {"generated": {"by": "school-notes", "at": "2026-10-03T10:00:00+02:00"},
                             "drive_folder": "Óra 1"})
    assert '  - { date: 2026-09-25, title: Termelés }' in out
    assert 'title: "Óra: termelés"' in out
    assert "drive_folder: Óra 1" in out
    assert fm.split(out).meta["generated"]["by"] == "school-notes"
    assert out.endswith("---\n\n# Cím\n")


def test_strip_keys_removes_machine_keys():
    out = fm.strip_keys(PAGE, ("generated", "type"))
    assert "generated" not in out and "type:" not in out and "lessons:" in out


def test_page_without_frontmatter():
    assert fm.set_keys("# x\n", {"a": 1}) == "---\na: 1\n---\n# x\n"
