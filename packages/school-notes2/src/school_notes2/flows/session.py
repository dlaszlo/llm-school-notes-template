"""The MCP server for the duration of one container (plan 7.5): a private session folder
with mcp.sock, served from a thread of the launching process."""

import contextlib
import os
import shutil
import threading
from pathlib import Path

from ..mcp.server import Handlers, McpServer
from .context import Ctx


def secret_values(ctx: Ctx) -> tuple[str, ...]:
    """Values redact() must never let out: every file of the secrets folder."""
    values = []
    folder = ctx.cfg.secrets_dir
    if folder.is_dir():
        for path in folder.iterdir():
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                values += [text] + [ln.strip() for ln in text.splitlines() if len(ln.strip()) > 8]
    return tuple(v for v in values if v)


@contextlib.contextmanager
def mcp(ctx: Ctx, task_dir: Path, mode: str, handlers: Handlers, run_id):
    """Yield the session folder while the server answers on <folder>/mcp.sock."""
    sessdir = task_dir / "sess"
    shutil.rmtree(sessdir, ignore_errors=True)
    sessdir.mkdir(mode=0o700)
    os.chmod(sessdir, 0o700)
    server = McpServer(student=ctx.name, mode=mode, handlers=handlers, log=ctx.log,
                       jobs_dir=task_dir / "jobs", run_id=run_id,
                       log_path=str(ctx.cfg.log_path), secrets=secret_values(ctx),
                       wait_s=ctx.cfg.limits.mcp_wait_s)
    stop = threading.Event()
    thread = threading.Thread(target=server.serve, args=(sessdir / "mcp.sock", stop.is_set),
                              daemon=True)
    thread.start()
    try:
        yield sessdir
    finally:
        stop.set()
        thread.join(timeout=5)
