"""Fixtures for the image tests (helpers in image_fakes.py)."""

from decimal import Decimal

import pytest

from image_fakes import KEY, FakeOpenRouter, make_worktree, write_shim
from school_notes2.images.settings import ImageSettings

@pytest.fixture
def fake_api():
    fake = FakeOpenRouter()
    yield fake
    fake.server.shutdown()

@pytest.fixture
def make_settings(tmp_path, fake_api):
    shim = write_shim(tmp_path, fake_api.url)
    key = tmp_path / "secrets" / "openrouter.key"
    key.parent.mkdir()
    key.write_text(f"OPENROUTER_API_KEY={KEY}\n")

    def factory(learner="benedek", **overrides) -> ImageSettings:
        work = tmp_path / f"work-{learner}"
        if not work.exists():
            make_worktree(tmp_path, learner)
        values = dict(learner=learner, worktree=work, script=shim,
                      state_root=tmp_path / "state/images", plans_root=tmp_path / "state/image-plans",
                      lock_path=tmp_path / "state/images.lock", key_file=key,
                      max_total_usd=Decimal("5"), learner_max_usd=Decimal("3"),
                      lock_timeout_s=10, timeout_s=60)
        values.update(overrides)
        return ImageSettings(**values)

    return factory
