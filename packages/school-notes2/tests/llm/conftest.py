from pathlib import Path

import pytest

from school_notes2.config import Harness, Role

@pytest.fixture
def fake(tmp_path, monkeypatch):
    work = tmp_path / "work"
    (work / ".school-notes").mkdir(parents=True)
    files = {"FAKE_LOG": tmp_path / "podman.log", "FAKE_ARGV": tmp_path / "argv.txt",
             "FAKE_STDIN": tmp_path / "stdin.txt", "FAKE_PIDFILE": tmp_path / "pid",
             "FAKE_OUT": work / ".school-notes" / "result.json", "FAKE_WORK": work}
    for key, value in files.items():
        monkeypatch.setenv(key, str(value))
    return files


@pytest.fixture
def harness():
    return Harness(name="codex", headless=["codex", "-m", "{model}", "exec", "-"],
                   interactive=["codex", "-m", "{model}"], login_check=["codex", "login", "status"])


@pytest.fixture
def role():
    return Role(harness="codex", model="gpt-6-astra", effort="high", timeout_s=20)
