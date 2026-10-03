from school_notes2.wiki import generate, markers


def test_subject_blocks(repo):
    text = generate.subject_index(repo, "proba")
    chapters = markers.read(text, "chapters")
    assert chapters == (
        "# 📘 9. évfolyam: Alapok\n\n"
        "* ⚡ [Összefoglaló: Alapok](osszefoglalo-alapok.md) - Rövid.\n"
        "* [Első](elso.md) - Az első téma.\n"
        "\n<br />\n\n"
        "# 📘 9. évfolyam: Haladó\n\n* [Második](masodik.md) - A második téma.\n")
    lessons = markers.read(text, "lessons").splitlines()
    assert lessons[0] == "| Dátum | Óra | Jegyzet | Témakörök |"
    assert lessons[2].startswith("| ? (legkésőbb 2026-09-10) | Folytatás |")
    assert "[Második](masodik.md#resz)" in lessons[2]
    assert lessons[3].startswith("| 2026-09-03 | Bevezetés | [jegyzet](2026-09-10-elso-jegyzet.md)")
    assert markers.read(text, "review").startswith("# 🔁 Ismétlés\n\n* [Dolgozatra]")
    assert markers.read(text, "notes") == "# 📝 Jegyzetek\n\n* [Első óra](2026-09-10-elso-jegyzet.md) - Jegyzet.\n"


def test_root_block_and_label(repo):
    text = generate.root_index(repo)
    assert markers.read(text, "subjects") == "* 🧪 [Próba](proba/index.md) - A próba tantárgy témakörei.\n"
    assert generate.subject_label(repo, "proba") == "🧪 Próba"
    assert generate.subject_sentence("Irodalom") == "Az irodalom tantárgy témakörei és jegyzetei, évfolyamonként."


def test_write_indexes_is_idempotent(repo):
    assert set(generate.write_indexes(repo)) == {"wiki/proba/index.md", "wiki/index.md"}
    assert generate.write_indexes(repo) == []


def test_undated_lesson_sorts_by_latest_possible_date(repo):
    subject = generate.load_subject(repo, "proba")
    titles = [lesson["title"] for _, lesson in generate.lessons(subject)]
    assert titles == ["Folytatás", "Bevezetés"]


def test_partly_legible_date_is_kept_as_written():
    from school_notes2.wiki.generate import lesson_date
    assert lesson_date({"date_note": "2026-09-1? (levágva: 2026-09-10 és 2026-09-19 között)"}) == \
        "2026-09-1? (levágva: 2026-09-10 és 2026-09-19 között)"
    assert lesson_date({"date_note": "legkésőbb 2026-09-25"}) == "? (legkésőbb 2026-09-25)"
