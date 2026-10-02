import subprocess
from pathlib import Path

import pytest

from school_notes2.git.run import Git
from school_notes2.log import Log


@pytest.fixture
def log(tmp_path):
    return Log(tmp_path / "logs" / "main.log", run_id="t-run", student="tester", console=False)


def make_origin(tmp_path: Path, files: dict[str, str]) -> Path:
    """A bare 'origin' with one commit on main holding `files`."""
    seed = tmp_path / "seed"
    seed.mkdir()
    env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin",
           "GIT_AUTHOR_NAME": "Seed", "GIT_AUTHOR_EMAIL": "seed@example.com",
           "GIT_COMMITTER_NAME": "Seed", "GIT_COMMITTER_EMAIL": "seed@example.com"}
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True, env=env)
    for rel, text in files.items():
        path = seed / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(seed), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(seed), "commit", "-q", "-m", "seed"], check=True, env=env)
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(seed), str(origin)], check=True, env=env)
    return origin


@pytest.fixture
def git_factory(log):
    def factory(git_dir: Path, work_tree: Path | None = None) -> Git:
        return Git(git_dir, "Test Owner", "owner@example.com", log, None, work_tree)
    return factory
