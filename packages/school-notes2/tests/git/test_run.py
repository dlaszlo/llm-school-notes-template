import subprocess

import pytest

from school_notes2.git.run import GitFailed, Remote, classify, with_retries
from school_notes2.state.errors import NeedsOwner, Race, Transient


def test_fixed_environment_ignores_user_config(tmp_path, git_factory, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".gitconfig").write_text("[core]\n\tautocrlf = true\n[alias]\n\tst = status\n")
    repo = tmp_path / "r.git"
    subprocess.run(["git", "init", "-q", "--bare", str(repo)], check=True)
    git = git_factory(repo)
    assert git.out("config", "--get", "core.autocrlf").strip() == "false"
    assert git.env()["GIT_CONFIG_GLOBAL"] == "/dev/null"
    assert "core.hooksPath=/dev/null" in git.argv(["status"])
    assert "gc.auto=0" in git.argv(["status"])
    assert "gc.auto=0" not in git.argv(["gc"], gc=True)


def test_ssh_command_is_fixed(tmp_path):
    remote = Remote(tmp_path / "key", tmp_path / "known", "ssh.github.com", 443)
    cmd = remote.ssh_command()
    assert "-F /dev/null" in cmd and "BatchMode=yes" in cmd and "IdentitiesOnly=yes" in cmd
    assert "HostName=ssh.github.com" in cmd and cmd.endswith("-p 443")


@pytest.mark.parametrize("command,stderr,cls", [
    ("push", " ! [rejected] main -> main (fetch first)", Race),
    ("push", "ERROR: Permission denied (publickey).", NeedsOwner),
    ("fetch", "ssh: Could not resolve hostname github.com", Transient),
    ("fetch", " ! [rejected] main -> origin/main (non-fast-forward)", NeedsOwner),
    ("ls-remote", "something odd", Transient),
    ("rebase", "CONFLICT (content)", GitFailed),
])
def test_classify(command, stderr, cls):
    assert isinstance(classify(command, stderr, 1), cls)


def test_with_retries_retries_transient_only():
    calls = []

    def step():
        calls.append(1)
        if len(calls) < 3:
            raise Transient("net")
        return "done"

    assert with_retries(step, sleep=lambda s: None) == "done"
    assert len(calls) == 3
    with pytest.raises(Transient):
        with_retries(lambda: (_ for _ in ()).throw(Transient("x")), sleep=lambda s: None)
