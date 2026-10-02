"""Background jobs of the MCP server (plan 7.5).

A job runs in a double-forked, session-leader process, so it outlives the MCP server and
the chat session (a `finish` keeps running and keeps the inherited learner lock). Its state
is a JSON file; `wait` polls that file.
"""

import os
import secrets
import signal
import time
import traceback
from pathlib import Path
from typing import Callable

from ..log import Log, now_iso
from ..state.errors import SnError
from ..state.files import read_json, write_json


class JobStore:
    def __init__(self, folder: Path, log: Log, close_fds: Callable[[], None] = lambda: None):
        self.folder = folder
        self.log = log
        self.close_fds = close_fds   # the child closes the server's sockets

    def path(self, job_id: str) -> Path:
        return self.folder / f"{job_id}.json"

    def get(self, job_id: str) -> dict | None:
        job = read_json(self.path(job_id))
        if job and job["state"] == "running" and not _alive(job.get("pid")):
            job.update(state="error", ended=now_iso(),
                       error={"code": "job_lost", "message": "the job process ended unexpectedly"})
            write_json(self.path(job_id), job)
        return job

    def running(self, tools: tuple[str, ...]) -> dict | None:
        """A running job of one of `tools`, if any (the idempotent state-changing calls)."""
        if not self.folder.is_dir():
            return None
        for path in sorted(self.folder.glob("*.json")):
            job = self.get(path.stem)
            if job and job["tool"] in tools and job["state"] == "running":
                return job
        return None

    def start(self, tool: str, run_id: str, fn: Callable[[], dict]) -> str:
        """Start `fn` detached; return the job id at once."""
        job_id = f"{tool.replace('_', '-')}-{secrets.token_hex(4)}"
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        job = {"id": job_id, "tool": tool, "run_id": run_id, "state": "running",
               "started": now_iso(), "pid": None}
        write_json(self.path(job_id), job)
        read_end, write_end = os.pipe()
        first = os.fork()
        if first == 0:  # intermediate child: new session, fork the worker, exit at once
            os.close(read_end)
            os.setsid()
            worker = os.fork()
            if worker == 0:
                os.close(write_end)
                self._work(job, fn)
            os.write(write_end, str(worker).encode())
            os._exit(0)
        os.close(write_end)
        os.read(read_end, 32)   # the worker exists once the intermediate child reports it
        os.close(read_end)
        os.waitpid(first, 0)
        return job_id

    def _work(self, job: dict, fn: Callable[[], dict]) -> None:
        code = 0
        try:
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            self.close_fds()
            job["pid"] = os.getpid()
            write_json(self.path(job["id"]), job)
            result = fn()
            job.update(state="done", result=result if isinstance(result, dict) else {"value": result})
        except SnError as exc:
            job.update(state="error", error={"code": exc.kind, "message": exc.message,
                                             "todo": exc.todo, **exc.details})
            self.log.bind(run_id=job["run_id"]).error(f"mcp.job {job['tool']}", exc)
        except BaseException as exc:  # noqa: BLE001 - a job must always leave a final state
            job.update(state="error", error={"code": "internal_error",
                                             "message": "internal error; see the host log"})
            self.log.bind(run_id=job["run_id"]).event(
                f"mcp.job {job['tool']}", "error", level="error", error_class="program",
                message=str(exc)[:300], traceback=traceback.format_exc()[-4000:])
            code = 1
        job["ended"] = now_iso()
        write_json(self.path(job["id"]), job)
        os._exit(code)

    def wait(self, job_id: str, limit_s: float, poll_s: float = 0.2) -> dict | None:
        deadline = time.monotonic() + limit_s
        while True:
            job = self.get(job_id)
            if job is None or job["state"] != "running" or time.monotonic() >= deadline:
                return job
            time.sleep(poll_s)


def _alive(pid) -> bool:
    if not pid:
        return True   # just started; the worker has not recorded its pid yet
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
