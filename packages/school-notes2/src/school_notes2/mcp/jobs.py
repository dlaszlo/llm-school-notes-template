"""Background jobs of the MCP server (plan 7.5).

A job runs in a double-forked process in its own session and process group, so it outlives
the MCP server and the chat session (a `finish` keeps running and keeps the inherited
learner lock). Its state is a JSON file; `wait` polls that file.
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

START_GRACE_S = 30      # a worker that has not recorded its pid by then never started


class JobStore:
    def __init__(self, folder: Path, log: Log, close_fds: Callable[[], None] = lambda: None):
        self.folder = folder
        self.log = log
        self.close_fds = close_fds   # the child closes the server's sockets

    def path(self, job_id: str) -> Path:
        return self.folder / f"{job_id}.json"

    def get(self, job_id: str) -> dict | None:
        job = read_json(self.path(job_id))
        if job and job["state"] == "running" and not _alive(job):
            job.update(state="error", ended=now_iso(),
                       error={"code": "job_lost", "message": "the job process ended unexpectedly"})
            write_json(self.path(job_id), job)
        return job

    def all_running(self) -> list[dict]:
        if not self.folder.is_dir():
            return []
        jobs = (self.get(p.stem) for p in sorted(self.folder.glob("*.json")))
        return [j for j in jobs if j and j["state"] == "running"]

    def running(self, tools: tuple[str, ...]) -> dict | None:
        """A running job of one of `tools`, if any (the idempotent state-changing calls)."""
        return next((j for j in self.all_running() if j["tool"] in tools), None)

    def running_any(self) -> dict | None:
        return next(iter(self.all_running()), None)

    def stop_all(self, timeout_s: float = 30) -> list[str]:
        """Stop every running job: SIGTERM to its process group, SIGKILL after `timeout_s`.
        The cron run calls this when the writer's container has ended (nothing may keep
        working in the worktree while `finish` runs)."""
        jobs = [self._with_pid(j) for j in self.all_running()]
        for job in jobs:
            if job.get("pid"):
                _signal_group(job["pid"], signal.SIGTERM)
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline and any(j.get("pid") and _alive(j) for j in jobs):
            time.sleep(0.2)
        for job in jobs:
            if job.get("pid") and _alive(job):
                _signal_group(job["pid"], signal.SIGKILL)
            fresh = read_json(self.path(job["id"])) or job
            if fresh["state"] == "running":
                fresh.update(state="error", ended=now_iso(),
                             error={"code": "stopped", "message": "stopped by the run"})
                write_json(self.path(job["id"]), fresh)
        return [j["id"] for j in jobs]

    def _with_pid(self, job: dict, wait_s: float = 5) -> dict:
        """A job started a moment ago may not have recorded its pid yet: wait briefly."""
        deadline = time.monotonic() + wait_s
        while not job.get("pid") and time.monotonic() < deadline:
            time.sleep(0.05)
            job = read_json(self.path(job["id"])) or job
        return job

    def start(self, tool: str, run_id: str, fn: Callable[[], dict]) -> str:
        """Start `fn` detached; return the job id at once."""
        job_id = f"{tool.replace('_', '-')}-{secrets.token_hex(4)}"
        self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        job = {"id": job_id, "tool": tool, "run_id": run_id, "state": "running",
               "started": now_iso(), "created": time.time(), "pid": None, "pid_start": None}
        write_json(self.path(job_id), job)
        read_end, write_end = os.pipe()
        first = os.fork()
        if first == 0:
            self._intermediate(read_end, write_end, job, fn)   # never returns
        os.close(write_end)
        os.read(read_end, 32)   # the worker exists once the intermediate child reports it
        os.close(read_end)
        os.waitpid(first, 0)
        return job_id

    def _intermediate(self, read_end: int, write_end: int, job: dict, fn) -> None:
        """New session, fork the worker, exit at once – never return into the server code."""
        try:
            os.close(read_end)
            os.setsid()
            worker = os.fork()
            if worker == 0:
                os.close(write_end)
                self._work(job, fn)
            os.write(write_end, str(worker).encode())
        finally:
            os._exit(0)

    def _work(self, job: dict, fn: Callable[[], dict]) -> None:
        code = 0
        try:
            os.setpgid(0, 0)        # its own group: stop_all can stop it with its children
            _detach_stdio()
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            self.close_fds()
            if (read_json(self.path(job["id"])) or {}).get("state") == "stopped":
                os._exit(0)     # stop_all gave up waiting for the pid: never run late
            job.update(pid=os.getpid(), pid_start=_start_time(os.getpid()))
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
        finally:
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


def _detach_stdio() -> None:
    """The session's terminal may close while the job runs (5.8): never write to it."""
    null = os.open(os.devnull, os.O_RDWR)
    for fd in (0, 1, 2):
        os.dup2(null, fd)
    if null > 2:
        os.close(null)


def _start_time(pid: int) -> str | None:
    """Field 22 of /proc/<pid>/stat: tells a reused pid from the original process."""
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    return text.rsplit(")", 1)[1].split()[19]


def _alive(job: dict) -> bool:
    pid = job.get("pid")
    if not pid:
        return time.time() - job.get("created", time.time()) < START_GRACE_S
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    recorded = job.get("pid_start")
    return recorded is None or _start_time(pid) == recorded


def _signal_group(pid: int, sig: int) -> None:
    try:
        os.killpg(pid, sig)
    except (ProcessLookupError, PermissionError):
        pass
