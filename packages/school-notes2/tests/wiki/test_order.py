from school_notes2.wiki.order import problems

INDEX = "---\nchapters:\n  - {{id: a, title: A}}\n  - {{id: b, title: B}}{extra}\n---\n# X\n"


def test_new_chapter_may_be_added_anywhere_but_old_ones_keep_their_order():
    old = INDEX.format(extra="")
    assert problems("i", old, INDEX.format(extra="\n  - {id: c, title: C}")) == []
    swapped = "---\nchapters:\n  - {id: b, title: B}\n  - {id: a, title: A}\n---\n# X\n"
    assert problems("i", old, swapped)


def test_lessons_topics_and_order_are_stable():
    old = ("---\norder: 10\nlessons:\n  - {date: '2026-09-01', title: E, topics: [a.md, b.md]}\n"
           "  - {date: '2026-09-08', title: K, topics: [c.md]}\n---\n")
    same_plus = old.replace("topics: [c.md]}", "topics: [c.md, d.md]}")
    assert problems("p", old, same_plus) == []
    assert problems("p", old, old.replace("[a.md, b.md]", "[b.md, a.md]"))
    assert problems("p", old, old.replace("order: 10", "order: 20"))
    flipped = ("---\norder: 10\nlessons:\n  - {date: '2026-09-08', title: K, topics: [c.md]}\n"
               "  - {date: '2026-09-01', title: E, topics: [a.md, b.md]}\n---\n")
    assert problems("p", old, flipped)
