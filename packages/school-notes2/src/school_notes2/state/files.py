"""Atomic file writes: a crash never leaves a half-written state file."""

import json
import os
import tempfile
from pathlib import Path


def write_bytes(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_text(path: Path, text: str, mode: int = 0o600) -> None:
    write_bytes(path, text.encode("utf-8"), mode)


def write_json(path: Path, value, mode: int = 0o600) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", mode)


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
