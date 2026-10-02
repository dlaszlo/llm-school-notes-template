"""T1 on copies of today's learner repos (skipped where the checkouts are absent).

Migrates a copy, regenerates, and compares with today's indexes and release lists.
The expected result is "identical" or the known, owner-approvable difference list.
"""

import shutil
from pathlib import Path

import pytest

from school_notes2.wiki import check, compare, generate, migrate, pages, public

def checkout(name: str) -> Path | None:
    """The learner checkout next to the template repo (or one of its worktrees)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / name / "wiki").is_dir():
            return parent / name
    return None


def migrated_copy(name: str, tmp_path: Path) -> tuple[Path, Path, migrate.Migration]:
    original = checkout(name)
    if original is None:
        pytest.skip(f"{name} checkout not present")
    copy = tmp_path / name
    shutil.copytree(original, copy, ignore=shutil.ignore_patterns(".git", "node_modules"))
    mig = migrate.migrate(copy)
    generate.write_indexes(copy)
    return original, copy, mig


def test_benedek(tmp_path):
    original, copy, mig = migrated_copy("school-notes-benedek-active", tmp_path)
    assert mig.warnings == []
    assert generate.write_indexes(copy) == []                       # idempotent
    assert check.errors(check.check_files(copy, pages.wiki_pages(copy) + ["wiki/log.md"])) == []
    result = compare.report(original, copy, public.render_rights(copy))
    assert result["unknown_assets"] == []
    # Collections and assets are identical (B6, B9, B10); the page set is identical (B7)
    # and only the order of lesson-notes pages differs, through the known lesson-order rule.
    assert all(line.startswith("page order:") for line in result["publication"]), result["publication"]
    moved = {line.split(" ", 3)[-1][1:] for line in result["publication"]}
    assert all(p.endswith("-jegyzet.md") for p in moved)
    assert set(result["indexes"]) <= {f"wiki/{s}/index.md" for s in pages.subjects(copy)}


def test_barna(tmp_path):
    original, copy, mig = migrated_copy("school-notes-barna-active", tmp_path)
    assert generate.write_indexes(copy) == []
    assert check.errors(check.check_files(copy, pages.wiki_pages(copy) + ["wiki/log.md"])) == []
    result = compare.report(original, copy, public.render_rights(copy))
    # Barna's pilot.json predates the shared format: listed for the owner, not asserted equal.
    assert result["unknown_assets"] == [
        "wiki/assets/banner/epito-2026-09-29-anyagtulajdonsagok-jegyzet-banner-20260930.webp"]
