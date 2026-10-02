"""Prerequisites checked before any run (plan 8.1 first row). Failing ones raise
Prerequisite: nothing starts, a daily e-mail tells the owner what to do."""

import os
import shutil
import subprocess
from pathlib import Path

from ..state.errors import Prerequisite


def disk(path: Path, min_free_gb: float) -> None:
    free = shutil.disk_usage(path).free / 1e9
    if free < min_free_gb:
        raise Prerequisite(f"only {free:.1f} GB free under {path}",
                           todo=f"free disk space (at least {min_free_gb:g} GB)")


def podman() -> None:
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    if not runtime or not Path(runtime).is_dir():
        raise Prerequisite("XDG_RUNTIME_DIR is missing (rootless Podman from cron)",
                           todo="set XDG_RUNTIME_DIR=/run/user/<uid> in the crontab; "
                                "check `loginctl enable-linger`")
    try:
        proc = subprocess.run(["podman", "info", "--format", "{{.Host.Security.Rootless}}"],
                              capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        proc = None
    if proc is None or proc.returncode != 0 or proc.stdout.strip() != b"true":
        raise Prerequisite("rootless Podman does not start", todo="check `podman info`")


def secret_file(path: Path, what: str) -> None:
    if not path.is_file():
        raise Prerequisite(f"{what} is missing: {path}", todo=f"put the {what} in place")
    if path.stat().st_mode & 0o077:
        raise Prerequisite(f"{what} is readable by others: {path}", todo=f"chmod 600 {path}")
