"""T7: every converted host entry point refuses planted symlinks in the worktree."""

import json
import os
import subprocess

import pytest

from school_notes2.evidence import records
from school_notes2.git import workbranch
from school_notes2.llm import output
from school_notes2.review import files as review_files
from school_notes2.sources.duplicates import Known
from school_notes2.sources.place import Downloaded, place_package
from school_notes2.state.safefs import UnsafePath
from school_notes2.wiki import check, generate, guard, machine


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "wiki/proba").mkdir(parents=True)
    (r / "wiki/proba/a.md").write_text("---\ntitle: A\n---\n# A\n")
    canary = tmp_path / "canary"
    canary.mkdir()
    (canary / "secret.md").write_text("SECRET\n")
    return r, canary


def test_workdir_link_is_removed_never_followed(repo):
    r, canary = repo
    os.symlink(canary, r / ".school-notes")
    workbranch.reset_workdir(r)
    assert (r / ".school-notes").is_dir() and not (r / ".school-notes").is_symlink()
    assert sorted(os.listdir(canary)) == ["secret.md"]


def test_machine_write_into_a_linked_page_is_refused(repo):
    r, canary = repo
    os.symlink(canary / "secret.md", r / "wiki/proba/2026-10-01-x-jegyzet.md")
    with pytest.raises(UnsafePath):
        machine.stamp_generated(r, ["wiki/proba/2026-10-01-x-jegyzet.md"], "w", "t")
    assert (canary / "secret.md").read_text() == "SECRET\n"


def test_check_does_not_read_or_fix_through_a_link(repo):
    r, canary = repo
    (canary / "secret.md").write_bytes(b"SECRET\r\n")
    os.symlink(canary / "secret.md", r / "wiki/proba/b.md")
    with pytest.raises(UnsafePath):
        check.check_files(r, ["wiki/proba/b.md"])
    assert (canary / "secret.md").read_bytes() == b"SECRET\r\n"


def test_linked_subject_folder_is_not_indexed(repo):
    r, canary = repo
    os.symlink(canary, r / "wiki/evil")
    assert "evil" not in generate.subject_order(r)


def test_guard_flags_a_symlinked_parent(repo):
    r, canary = repo
    os.symlink(canary, r / "wiki/evil")
    found = guard.run(guard.GuardInput(worktree=r, changes=[guard.Change("wiki/evil/secret.md",
                                                                        "added")],
                                       base_content=lambda p: None))
    assert found and found[0].owner


def test_evidence_record_never_written_through_a_link(repo):
    r, canary = repo
    (r / "docs/evidence").mkdir(parents=True)
    os.symlink(canary, r / "docs/evidence/pages")
    (r / "wiki/assets").mkdir()
    (r / "wiki/assets/k.png").write_bytes(b"png")
    entry = records.Entry("wiki/proba/a.md", "wiki/assets/k.png", "1", "seen", "confirmed")
    with pytest.raises(UnsafePath):
        records.append(r, [entry], run_id="r1", checker="w", at="t")
    assert sorted(os.listdir(canary)) == ["secret.md"]


def test_review_files_behind_a_link_are_ignored(repo):
    r, canary = repo
    (r / "docs").mkdir()
    (canary / "2026-10-01-review.md").write_text("---\nitems: {R1: open}\n---\n")
    os.symlink(canary, r / "docs/review")
    assert review_files.open_items(r, "interactive") == []


def test_sources_never_placed_through_a_linked_subject(repo, tmp_path):
    r, canary = repo
    os.symlink(canary, r / "sources")
    download = tmp_path / "dl.md"
    download.write_text("# doc\n")
    pkg = Downloaded("Csomag", "proba", "tanari", "", False, True,
                     [{"rel": "document.md", "path": str(download), "sha256": "0" * 64}])
    with pytest.raises(UnsafePath):
        place_package(r, pkg, 1, Known())
    assert sorted(os.listdir(canary)) == ["secret.md"]


def test_role_output_is_not_read_through_a_link(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    secret = tmp_path / "auth.json"
    secret.write_text(json.dumps({"verdict": "ok", "findings": []}))
    os.symlink(secret, out / "review.json")
    value, problems = output.read_file(out / "review.json", "review", out)
    assert value is None and problems
