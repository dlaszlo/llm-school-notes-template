import os
import shutil
import subprocess
from importlib import resources

import pytest

DIR = resources.files("school_notes2").joinpath("container")
SCRIPTS = ("entrypoint.sh", "init-firewall.sh", "sn-preflight")


@pytest.mark.parametrize("name", SCRIPTS)
def test_scripts_parse(name):
    assert subprocess.run(["bash", "-n", str(DIR / name)]).returncode == 0


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck not installed")
@pytest.mark.parametrize("name", SCRIPTS)
def test_shellcheck(name):
    assert subprocess.run(["shellcheck", "-S", "warning", str(DIR / name)]).returncode == 0


@pytest.mark.skipif(os.getuid() == 0, reason="needs a non-root user")
def test_entrypoint_refuses_to_run_as_non_root():
    proc = subprocess.run(["bash", str(DIR / "entrypoint.sh"), "true"], capture_output=True)
    assert proc.returncode == 12


def test_firewall_without_domains_fails_with_12():
    env = {"PATH": os.environ["PATH"]}
    proc = subprocess.run(["bash", str(DIR / "init-firewall.sh")], env=env, capture_output=True)
    assert proc.returncode == 12


def test_containerfile_pins_base_and_versions():
    text = (DIR / "Containerfile").read_text()
    assert "node:24-trixie-slim@sha256:" in text
    assert "CLAUDE_CODE_VERSION=2.1.288" in text and "CODEX_VERSION=0.160.0" in text
    for tool in ("ripgrep", "socat", "iptables", "librsvg2-bin", "graphviz"):
        assert tool in text
    assert "ENTRYPOINT" in text and "UV_OFFLINE=1" in text


def test_preflight_env_allowlist_matches_launcher():
    text = (DIR / "sn-preflight").read_text()
    for key in ("SN_RUN_ID", "SN_ALLOWED_DOMAINS", "SN_MODEL_PROBE", "SN_NO_NETWORK"):
        assert f" {key} " in text
    assert "SSH_AUTH_SOCK" in text and "example.com" in text
