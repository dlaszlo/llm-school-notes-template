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


JOB = "benedek-termeles-banner"
RECEIPTS = f"docs/evidence/media/{JOB}"


def test_round2_b1_links_in_the_receipt_folder_are_never_followed(make_settings, fake_api, log,
                                                                  tmp_path):
    """Verification review 2.1: learning_image.py writes job.json via job.json.tmp, prompt-N
    and receipt-N into the receipt folder – planted links there must not reach the host."""
    s = make_settings()
    assert gen.generate(s, "termeles-banner", log=log, sleep=lambda x: None)["state"] == "generated"
    folder = s.worktree / RECEIPTS
    folder.mkdir(parents=True)
    canaries = {name: tmp_path / f"canary-{name}" for name in
                ("job.json.tmp", "prompt-1.txt", "receipt-1.json")}
    for name, canary in canaries.items():
        os.symlink(canary, folder / name)
    answer = accept(s, log)
    assert answer["state"] == "accepted", answer
    assert not any(c.exists() for c in canaries.values())
    assert not (folder / "prompt-1.txt").is_symlink()         # replaced, never followed
    assert not (folder / "receipt-1.json").is_symlink()


def test_round2_b1_linked_receipt_folder_is_refused(make_settings, fake_api, log, tmp_path):
    s = make_settings()
    gen.generate(s, "termeles-banner", log=log, sleep=lambda x: None)
    outside = tmp_path / "receipts-outside"
    outside.mkdir()
    (s.worktree / "docs/evidence/media").mkdir(parents=True, exist_ok=True)
    os.symlink(outside, s.worktree / RECEIPTS)
    try:
        answer = accept(s, log)
    except UnsafePath:
        answer = {"state": "error"}
    assert answer["state"] != "accepted"
    assert list(outside.iterdir()) == []


def test_learning_image_works_on_a_staging_copy_only(tmp_path):
    """copy_back takes only the job's receipt folder and its asset from the staging copy."""
    from school_notes2.images.executor import ExecutorError, copy_back
    work, stage = tmp_path / "work", tmp_path / "stage"
    (work / "wiki").mkdir(parents=True)
    (stage / "wiki").mkdir(parents=True)
    (stage / "wiki/index.md").write_text("rewritten by the tool?\n")
    with pytest.raises(ExecutorError, match="unexpected file"):
        copy_back(work, stage, {"id": JOB}, {})
    (stage / "wiki/index.md").unlink()
    (stage / RECEIPTS).mkdir(parents=True)
    (stage / f"{RECEIPTS}/receipt-1.json").write_text("{}")
    (stage / "wiki/assets/banner").mkdir(parents=True)
    (stage / f"wiki/assets/banner/{JOB}.webp").write_bytes(b"new")
    (work / "wiki/assets/banner").mkdir(parents=True)
    (work / f"wiki/assets/banner/{JOB}.webp").write_bytes(b"old")
    with pytest.raises(ExecutorError, match="different bytes"):
        copy_back(work, stage, {"id": JOB}, {})
    (work / f"wiki/assets/banner/{JOB}.webp").unlink()
    assert copy_back(work, stage, {"id": JOB}, {}) == [f"{RECEIPTS}/receipt-1.json",
                                                      f"wiki/assets/banner/{JOB}.webp"]


def test_asset_names_match_exactly():
    from school_notes2.images.executor import is_job_asset
    assert is_job_asset("wiki/assets/banner/benedek-x-a.webp", "benedek-x-a")
    assert is_job_asset("wiki/assets/banner/benedek-x-a-r2.webp", "benedek-x-a")
    assert not is_job_asset("wiki/assets/banner/benedek-x-ab.webp", "benedek-x-a")
    assert not is_job_asset("docs/benedek-x-a.webp", "benedek-x-a")


def test_refused_output_writes_nothing(tmp_path):
    import pytest
    from school_notes2.images.executor import ExecutorError, copy_back
    worktree, stage = tmp_path / "wt", tmp_path / "stage"
    (worktree / "wiki").mkdir(parents=True)
    receipt = stage / "docs/evidence/media/benedek-x/receipt-1.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("{}")
    (stage / "wiki").mkdir()
    (stage / "wiki/elsewhere.md").write_text("no")
    with pytest.raises(ExecutorError):
        copy_back(worktree, stage, {"id": "benedek-x"}, {})
    assert not (worktree / "docs").exists()
