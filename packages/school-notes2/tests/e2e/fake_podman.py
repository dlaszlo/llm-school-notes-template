#!/usr/bin/env python3
"""A `podman` for the end-to-end test: login checks pass, the writer is fake_writer.py."""

import os
import subprocess
import sys
from pathlib import Path

args = sys.argv[1:]
if not args or args[0] in ("rm", "stop", "info"):
    sys.exit(0)
if args[0] != "run":
    sys.exit(0)
work = next((a.split(":")[0] for a in args if a.endswith(":/work:rw")), None)
image = next(i for i, a in enumerate(args) if a.startswith("localhost/school-notes-agent"))
command = args[image + 1:]
if command[-2:] == ["auth", "status"] or command[-2:] == ["login", "status"]:
    sys.exit(0)
sys.stdin.read()
writer = Path(__file__).with_name("fake_writer.py")
sys.exit(subprocess.call([sys.executable, str(writer), work, os.environ.get("FAKE_WRITER", "good")]))
