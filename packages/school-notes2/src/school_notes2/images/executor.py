"""Calls into tools/learning_image.py of the installed release.

The OpenRouter key is read from the secrets file at call time and given only to the
child's environment, never on argv (plan 7.2).
"""

import importlib.util
import json
import subprocess
import tempfile
from functools import cache
from pathlib import Path

from .settings import ImageSettings


class ExecutorError(RuntimeError):
    """learning_image.py refused or failed; the message is its own (no secrets)."""


class ExecutorTimeout(ExecutorError):
    pass


def read_key(key_file: Path) -> str:
    """`openrouter.key` holds the bare key or an `OPENROUTER_API_KEY=...` line."""
    for line in key_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            name, value = line.split("=", 1)
            if name.strip() == "OPENROUTER_API_KEY":
                return value.strip().strip("\"'")
            continue
        return line
    raise ExecutorError("OpenRouter key missing in the secrets file")


def call(settings: ImageSettings, command: str, args: list[str], target: str,
         with_key: bool = False, files: dict[str, str] | None = None) -> dict:
    """Run one learning_image.py command; `files` are written next to the config first."""
    with tempfile.TemporaryDirectory(prefix="li-", dir=_scratch(settings)) as tmp:
        folder = Path(tmp)
        config = settings.write_executor_config(folder, target)
        for name, text in (files or {}).items():
            (folder / name).write_text(text, encoding="utf-8")
        argv = [settings.python, str(settings.script), "--config", str(config), command,
                *[a.replace("{tmp}", tmp) for a in args]]
        env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C.UTF-8", "HOME": tmp}
        if with_key:
            env["OPENROUTER_API_KEY"] = read_key(settings.key_file)
        try:
            proc = subprocess.run(argv, env=env, capture_output=True, text=True,
                                  timeout=settings.timeout_s, cwd=tmp)
        except subprocess.TimeoutExpired:
            raise ExecutorTimeout(f"learning_image {command} timed out") from None
    if proc.returncode != 0:
        raise ExecutorError(_error_text(proc.stderr))
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def ensure_ledger(settings: ImageSettings, target: str) -> None:
    """Initialize this school year's ledger once (learning_image never resets one)."""
    if not (settings.state_dir / "ledger.json").is_file():
        call(settings, "init-state", [], target)


def _scratch(settings: ImageSettings) -> Path:
    settings.plans_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    return settings.plans_dir


def _error_text(stderr: str) -> str:
    for line in reversed(stderr.strip().splitlines()):
        try:
            return str(json.loads(line).get("error", ""))[:500]
        except (json.JSONDecodeError, AttributeError):
            continue
    return "learning_image failed without a structured error"


@cache
def module(script: Path):
    """learning_image.py loaded in-process for its pure encoders (no network)."""
    spec = importlib.util.spec_from_file_location("learning_image_release", script)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded
