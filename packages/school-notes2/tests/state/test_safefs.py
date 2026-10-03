"""T7: symlink-safe access to container-controlled trees."""

import os

import pytest

from school_notes2.state import safefs
from school_notes2.state.safefs import UnsafePath


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "work"
    (root / "wiki").mkdir(parents=True)
    (root / "wiki/a.md").write_text("a\n")
    canary = tmp_path / "outside"
    canary.mkdir()
    (canary / "secret").write_text("SECRET\n")
    return root, canary


def test_read_write_roundtrip(tree):
    root, _ = tree
    safefs.write_text(root, "x/y/z.txt", "hello")
    assert safefs.read_text(root, "x/y/z.txt") == "hello"
    assert safefs.is_file(root, "x/y/z.txt") and safefs.is_dir(root, "x/y")
    assert not safefs.exists(root, "nope")
    assert safefs.walk_files(root) == ["wiki/a.md", "x/y/z.txt"]
    assert safefs.glob(root, "", "*/*.md") == ["wiki/a.md"]
    assert safefs.glob(root, "", "**/*.txt") == ["x/y/z.txt"]
    safefs.rmtree(root, "x")
    assert not safefs.exists(root, "x")


def test_symlinked_file_is_neither_read_nor_written(tree):
    root, canary = tree
    os.symlink(canary / "secret", root / "wiki/link.md")
    with pytest.raises(UnsafePath):
        safefs.read_bytes(root, "wiki/link.md")
    with pytest.raises(UnsafePath):
        safefs.exists(root, "wiki/link.md")
    safefs.write_text(root, "wiki/link.md", "replaced")      # replaces the link itself
    assert (canary / "secret").read_text() == "SECRET\n"
    assert not (root / "wiki/link.md").is_symlink()


def test_dangling_link_does_not_create_the_target(tree):
    root, canary = tree
    os.symlink(canary / "created", root / "wiki/dangling.md")
    safefs.write_text(root, "wiki/dangling.md", "x")
    assert not (canary / "created").exists()


def test_symlinked_parent_directory_is_refused(tree):
    root, canary = tree
    os.symlink(canary, root / "evil")
    with pytest.raises(UnsafePath):
        safefs.write_text(root, "evil/new.txt", "x")
    with pytest.raises(UnsafePath):
        safefs.read_text(root, "evil/secret")
    with pytest.raises(UnsafePath):
        safefs.rmtree(root, "evil/sub")
    assert sorted(os.listdir(canary)) == ["secret"]
    assert "evil/secret" not in safefs.walk_files(root)


def test_escape_and_absolute_paths_are_refused(tree):
    root, _ = tree
    for rel in ("../outside/secret", "/etc/passwd", "wiki/../../outside/secret"):
        with pytest.raises(UnsafePath):
            safefs.read_bytes(root, rel)


def test_fallback_walk_without_openat2(tree, monkeypatch):
    root, canary = tree
    monkeypatch.setattr(safefs, "_HAVE_OPENAT2", False)
    os.symlink(canary, root / "evil")
    with pytest.raises(UnsafePath):
        safefs.read_text(root, "evil/secret")
    assert safefs.read_text(root, "wiki/a.md") == "a\n"
