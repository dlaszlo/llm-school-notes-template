"""Private durable files, finite child processes and the cooperative runtime lock."""
from __future__ import annotations

import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time


class Blocked(Exception):
    """A preserved result requires an explicit next step."""


class Busy(Blocked):
    pass


class TimedOut(Blocked):
    pass


class QuotaBlocked(Blocked):
    pass


class Transient(Blocked):
    """Read-only temporary transport failure eligible for bounded backoff."""


class WindowExhausted(Blocked):
    """Work stays queued for the next finite run, without consuming a retry."""


class PreconditionFailed(Blocked):
    """Raised only when the effect mutation was never started."""
    pass


class EffectPending(Blocked):
    """Reconcile a possibly completed asynchronous effect; never repeat blindly."""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def private_dir(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.stat().st_mode & 0o077:
        raise Blocked(f"private directory permissions: {path}")
    return path


def atomic_json(path, value):
    path = Path(path)
    private_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(canonical(value) + b"\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dirfd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def safe_relative(name):
    p = Path(name)
    if not name or p.is_absolute() or any(x in ("", ".", "..") for x in name.split("/")) or "\\" in name or "\x00" in name or any(0xD800 <= ord(c) <= 0xDFFF for c in name):
        raise Blocked("unsafe relative source path")
    return p


def disk_gate(path, estimate=0, reserve=4 * 1024**3):
    path = Path(path)
    while not path.exists():
        path = path.parent
    free = shutil.disk_usage(path).free
    if free < reserve + estimate:
        raise Blocked(f"disk: free={free}, reserve={reserve}, next_phase={estimate}")


class RunLock:
    """Children inherit the same open-file description, including after parent death.

    Closing, rather than LOCK_UN, is intentional: an orphan child must keep the
    lock until it exits. The owner JSON is diagnostic and never breaks the lock.
    """
    def __init__(self, path):
        self.path = Path(path)
        self.fd = None

    def __enter__(self):
        private_dir(self.path.parent)
        self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(self.fd)
            self.fd = None
            raise Busy("another run or inherited child holds the cooperative lock") from None
        os.set_inheritable(self.fd, True)
        self.started = now()
        self.phase("starting")
        return self

    def phase(self, phase):
        identity = Path(f"/proc/{os.getpid()}/stat").read_text().split(") ", 1)[1].split()[19]
        atomic_json(self.path.with_suffix(".owner.json"), {"pid": os.getpid(), "start_ticks": identity, "started": self.started, "phase": phase})

    def __exit__(self, *_):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def terminate_group(pid,grace=0.05):
    """Stop descendants even when the group leader has already exited."""
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    time.sleep(grace)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    for _ in range(20):
        alive = False
        for path in Path("/proc").glob("[0-9]*/stat"):
            try:
                fields = path.read_text().split(") ", 1)[1].split()
                if int(fields[2]) == pid and fields[0] != "Z":
                    alive = True
                    break
            except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
                continue
        if not alive:
            return
        time.sleep(0.01)
    raise Blocked("child process group did not stop; finalization forbidden")


def run(argv, cwd, *, timeout=120, lock=None, log=None, env=None, read_output=True, filename_output=False):
    """No shell, no stdin; kill the entire process group on timeout.

    Command configuration is trusted admin input. Source text never builds argv.
    Large stdout goes to a durable private log, not an unbounded memory buffer.
    """
    if not argv or not all(isinstance(x, str) and "\x00" not in x for x in argv):
        raise Blocked("invalid command argument list")
    if lock and getattr(lock, "window", None):
        lock.window.require(timeout + 5)
    child_env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "XDG_CONFIG_HOME") if k in os.environ}
    child_env.update({"UV_OFFLINE": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    child_env.update(env or {})
    child_env.pop("SCHOOL_NOTES_SESSION",None) # owner provenance never enters finite workers
    pass_fds = (lock.fd,) if lock and lock.fd is not None else ()
    temporary = log is None
    if temporary:
        fd, logfile = tempfile.mkstemp(prefix="school-notes-process-")
        os.close(fd)
    else:
        logfile = str(log)
        private_dir(Path(logfile).parent)
    try:
        stderr_path = logfile + ".stderr"
        with open(logfile, "wb") as out, open(stderr_path, "wb") as err:
            os.chmod(logfile, 0o600)
            os.chmod(stderr_path, 0o600)
            deadline=time.monotonic()+timeout
            guardian = [__import__("sys").executable, str(Path(__file__).with_name("_process_guard.py")), str(os.getpid()), Path(f"/proc/{os.getpid()}/stat").read_text().split(") ",1)[1].split()[19], str(deadline), ",".join(map(str, pass_fds)), *argv]
            process = subprocess.Popen(guardian, cwd=cwd, env=child_env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True, pass_fds=pass_fds)
            def stop_guardian():
                # Its worker has a separate group. Give the independent
                # subreaper its 2-second descendant cleanup plus reserve;
                # killing the guardian immediately would orphan that worker.
                if process.poll() is not None:return
                process.terminate()
                try:process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    terminate_group(process.pid)
                    process.wait()
                    raise Blocked('worker guardian did not finish bounded cleanup; inspect surviving descendants/operation lock; no finalization') from None
            try:
                code = process.wait(timeout=max(0,deadline-time.monotonic()) + 3)
            except subprocess.TimeoutExpired:
                stop_guardian()
                raise TimedOut("child process timed out; partial output preserved") from None
            finally:
                stop_guardian()
                process.wait()
            if code == 124:
                raise TimedOut("child process timed out; partial output preserved")
            if code:
                raise Blocked(f"child process failed ({code}); inspect private stdout/stderr logs")
        if not read_output:
            return ""
        # Deliberately bounded. Agents use their durable log for full parsing.
        with open(logfile, "rb") as f:
            data = f.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise Blocked("child output exceeds finite result limit")
        return data.decode("utf-8", "surrogateescape" if filename_output else "strict")
    finally:
        if temporary:
            os.unlink(logfile)
            if os.path.exists(logfile + ".stderr"):
                os.unlink(logfile + ".stderr")


class Window:
    def __init__(self, seconds=50 * 60):
        self.deadline = time.monotonic() + seconds

    def require(self, seconds):
        if time.monotonic() + seconds > self.deadline:
            raise WindowExhausted("run window: next phase resumes in the next run")
