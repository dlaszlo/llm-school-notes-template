"""T7 for the image flow: planted symlinks never lead host writes outside the worktree."""

import os

import pytest

from school_notes2.images import accept as accept_mod
from school_notes2.images import generate as gen
from school_notes2.images import plans
from school_notes2.state.safefs import UnsafePath

from image_fakes import verdict

PLAN = ".school-notes/images/termeles-banner.json"


def accept(settings, log):
    return accept_mod.accept(settings, "termeles-banner", verdict(), verifier="w/high",
                             append_evidence=lambda page, entry: None, log=log)


def test_review3_b1_dangling_plan_link_does_not_create_a_host_file(make_settings, fake_api, log,
                                                                    tmp_path):
    """generate keeps the plan, the LLM swaps it for a dangling link to ~/.bash_aliases,
    image_accept would restore it: the canary must not appear."""
    s = make_settings()
    assert gen.generate(s, "termeles-banner", log=log, sleep=lambda x: None)["state"] == "generated"
    canary = tmp_path / "bash_aliases"
    (s.worktree / PLAN).unlink()
    os.symlink(canary, s.worktree / PLAN)
    try:
        accept(s, log)
    except UnsafePath:
        pass
    with pytest.raises(UnsafePath):
        plans.restore(s, ["termeles-banner"])
    assert not canary.exists()


def test_plan_read_through_a_link_is_refused(make_settings, log, tmp_path):
    s = make_settings()
    secret = tmp_path / "secret.json"
    secret.write_text('{"x": 1}')
    (s.worktree / PLAN).unlink()
    os.symlink(secret, s.worktree / PLAN)
    with pytest.raises(UnsafePath):
        plans.keep(s, "termeles-banner")
    assert not (s.plans_dir / "termeles-banner.json").exists()


def test_preview_copy_does_not_follow_a_linked_images_folder(make_settings, fake_api, log,
                                                             tmp_path):
    s = make_settings()
    gen.generate(s, "termeles-banner", log=log, sleep=lambda x: None)   # plan kept
    outside = tmp_path / "outside"
    outside.mkdir()
    images = s.worktree / ".school-notes/images"
    for f in images.iterdir():
        f.unlink()
    images.rmdir()
    os.symlink(outside, images)
    try:
        gen.generate(s, "termeles-banner", log=log, sleep=lambda x: None)
    except UnsafePath:
        pass
    assert list(outside.iterdir()) == []


def test_linked_assets_folder_stops_learning_image(make_settings, fake_api, log, tmp_path):
    s = make_settings()
    gen.generate(s, "termeles-banner", log=log, sleep=lambda x: None)
    outside = tmp_path / "assets-outside"
    outside.mkdir()
    assets = s.worktree / "wiki/assets"
    if assets.exists():
        os.rename(assets, tmp_path / "assets-moved")
    os.symlink(outside, assets)
    with pytest.raises(UnsafePath):
        accept(s, log)
    assert list(outside.iterdir()) == []


def test_markers_behind_a_linked_folder_are_not_seen(make_settings, tmp_path):
    s = make_settings()
    outside = tmp_path / "pages"
    outside.mkdir()
    (outside / "x.md").write_text("<!-- image: stolen -->\n")
    os.symlink(outside, s.worktree / "wiki/evil")
    assert "stolen" not in plans.find_markers(s.worktree)
