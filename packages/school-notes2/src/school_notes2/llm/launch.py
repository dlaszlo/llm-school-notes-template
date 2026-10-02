"""Launching an LLM role in the agent container (plan 5.3, 5.6/4, 7.4, 8.1).

The tool never parses the harness's event stream to decide success: success is exit code 0
plus a schema-valid output (file or stdout mode). Metrics are best effort.
"""

import hashlib
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Callable

from ..config import Harness, Role
from ..log import Log
from ..state.errors import BadWork, NeedsOwner, Prerequisite, Transient
from . import metrics as metrics_mod
from .output import extract_stdout, read_file

PROVIDER_DOMAINS = ("api.anthropic.com", "api.openai.com", "auth.openai.com", "chatgpt.com")
# The owner's one-off harness login inside the container also needs the login sites.
LOGIN_DOMAINS = PROVIDER_DOMAINS + ("claude.ai", "platform.claude.com", "console.anthropic.com")
EXIT_PREFLIGHT, EXIT_API, EXIT_FIREWALL = 10, 11, 12
PODMAN_FAILED = 125            # podman itself could not create or start the container
NOT_EXECUTABLE = (126, 127)    # the template's command is missing in the image
PLACEHOLDER = re.compile(r"\{(model|effort)\}")
OUTPUT_INSTRUCTION = {
    "file": ("A választ a `/out/review.json` fájlba írd egyetlen JSON-objektumként: "
             "`verdict` (ok | changes), `findings` [{id: R1…, file, line, problem, suggestion}], "
             "`figures` [{file, page, verdict, checks, observed, description}], "
             "`family_questions` [szöveg]."),
    "stdout": ("A válaszod végén írd ki a review-t egyetlen JSON-objektumként: "
               "`verdict` (ok | changes), `findings` [{id: R1…, file, line, problem, suggestion}], "
               "`figures` [{file, page, verdict, checks, observed, description}], "
               "`family_questions` [szöveg]."),
}


def container_name(learner: str, suffix: str = "") -> str:
    return f"school-notes-{learner}{suffix}"


def home_volume(learner: str) -> str:
    """Per-learner volume: the harness keeps session history in its home (plan 7.4)."""
    return f"sn-agent-home-{learner}"


def prompt(role_name: str, output_mode: str = "file") -> str:
    """The fixed prompt of a role, byte-identical on every call (K12)."""
    name = "writer" if role_name == "writer" else "reviewer"
    text = resources.files(__package__).joinpath("prompts", f"{name}.txt").read_text("utf-8")
    return text.replace("{output_instruction}", OUTPUT_INSTRUCTION[output_mode])


def expand(template: list[str], role: Role) -> list[str]:
    """Fill {model} and {effort}; every other brace (JSON in an argument) stays as it is."""
    values = {"model": role.model, "effort": role.effort}
    return [PLACEHOLDER.sub(lambda m: values[m.group(1)], part) for part in template]


@dataclass(frozen=True)
class Mounts:
    work: Path | None = None
    work_readonly: bool = False
    sessdir: Path | None = None      # holds mcp.sock; absent for the reviewer
    in_dir: Path | None = None
    out_dir: Path | None = None
    home: bool = True                # the learner's harness-home volume


def podman_argv(*, learner: str, image: str, run_id: str, mounts: Mounts, name: str,
                interactive: bool = False, network: bool = True,
                allowed_domains: tuple[str, ...] = PROVIDER_DOMAINS,
                podman: str = "podman") -> list[str]:
    """The fixed `podman run` argv of plan 7.4, without the harness command."""
    argv = [podman, "run", "--rm", "--name", name, "--userns=keep-id", "--user", "0",
            "--security-opt", "no-new-privileges", "--ulimit", "core=0", "--tmpfs", "/tmp"]
    argv += ["--cap-add=NET_ADMIN,NET_RAW"] if network else ["--network", "none"]
    if mounts.work:
        argv += ["-v", f"{mounts.work}:/work:{'ro' if mounts.work_readonly else 'rw'}"]
    if mounts.in_dir:
        argv += ["-v", f"{mounts.in_dir}:/in:ro"]
    if mounts.out_dir:
        argv += ["-v", f"{mounts.out_dir}:/out:rw"]
    if mounts.home:
        argv += ["-v", f"{home_volume(learner)}:/home/agent"]
    if mounts.sessdir:
        argv += ["-v", f"{mounts.sessdir}:/run/sn"]
    argv += ["-e", f"SN_RUN_ID={run_id}"]
    if network:
        argv += ["-e", f"SN_ALLOWED_DOMAINS={','.join(allowed_domains)}",
                 "-e", f"SN_MODEL_PROBE=https://{allowed_domains[0]}/"]
    else:
        argv += ["-e", "SN_NO_NETWORK=1"]
    argv += ["-it"] if interactive else ["-i"]
    return argv + [image]


def tree_fingerprint(root: Path, exclude: tuple[str, ...] = (".school-notes",)) -> str:
    """A cheap fingerprint of a tree (paths, sizes, mtimes) to tell whether the LLM worked."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir() or (rel.parts and rel.parts[0] in exclude):
            continue
        st = path.lstat()
        digest.update(f"{rel}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    return digest.hexdigest()


@dataclass(frozen=True)
class RoleRun:
    """Everything one headless role call needs."""

    learner: str
    run_id: str
    role_name: str               # writer | reviewer
    role: Role
    harness: Harness
    image: str
    mounts: Mounts
    output_host: Path            # where the output file appears on the host (file mode)
    schema: str                  # result | review
    task_dir: Path
    label: str = "1"             # range k, or attempt; part of the transcript name
    allowed_domains: tuple[str, ...] = PROVIDER_DOMAINS


@dataclass
class Outcome:
    rc: int
    timed_out: bool
    duration_s: float
    output: dict | None
    problems: list[str]
    changed: bool
    transcript: Path
    metrics: dict = field(default_factory=dict)


def _open_private(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)
    return os.fdopen(fd, "wb")


def remove_stale(name: str, podman: str = "podman") -> None:
    """Whoever holds the learner lock owns the container name; a leftover one is stale."""
    subprocess.run([podman, "rm", "-f", "--ignore", name], capture_output=True, timeout=60)


def _wait(proc: subprocess.Popen, name: str, timeout: float, podman: str) -> bool:
    """Wait for the harness; on timeout `podman stop -t 10`. True when it timed out."""
    try:
        proc.wait(timeout=timeout)
        return False
    except subprocess.TimeoutExpired:
        subprocess.run([podman, "stop", "-t", "10", name], capture_output=True, timeout=60)
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        return True


def _read_output(run: RoleRun, transcript: Path) -> tuple[dict | None, list[str], bool]:
    """(output, problems, produced): `produced` means the role wrote something at all."""
    if run.harness.output == "stdout":
        text = transcript.read_text(encoding="utf-8", errors="replace")
        value, problems = extract_stdout(text, run.schema)
        return value, problems, value is not None
    value, problems = read_file(run.output_host, run.schema)
    return value, problems, run.output_host.exists()


def classify(rc: int, timed_out: bool, changed: bool, produced: bool,
             output: dict | None, problems: list[str]) -> Exception | None:
    """Map one role call to the 8.1 classes; None means success."""
    if rc == EXIT_PREFLIGHT:
        return NeedsOwner("the container preflight security check failed",
                          todo="read the run log; the container saw something it must not")
    if rc == EXIT_FIREWALL:
        return NeedsOwner("the container firewall could not be loaded",
                          todo="check Podman and iptables on the VM")
    if rc == EXIT_API:
        return Transient("the model API is unreachable from the container")
    if rc == PODMAN_FAILED:
        return Prerequisite("Podman could not start the agent container",
                            todo="check `podman info` and XDG_RUNTIME_DIR for the cron user")
    if rc in NOT_EXECUTABLE:
        return NeedsOwner(f"the harness command is missing in the image (exit {rc})",
                          todo="check the role template and the installed image")
    if timed_out:
        return BadWork("the LLM ran out of time")
    if rc == 0 and output is not None:
        return None
    if rc == 0:
        return BadWork("output missing or invalid: " + "; ".join(problems[:5]))
    if not changed and not produced:
        return Transient(f"the LLM did not work (exit {rc}, nothing changed)")
    return BadWork(f"the LLM exited with {rc} after changing files: " + "; ".join(problems[:3]))


def run_headless(run: RoleRun, *, log: Log, snapshot: Callable[[], object],
                 podman: str = "podman") -> Outcome:
    """Start the role, feed the fixed prompt on stdin, wait, read and classify the output.

    Raises the 8.1 error class on failure; returns the Outcome on success.
    """
    name = container_name(run.learner)
    remove_stale(name, podman)
    run.output_host.unlink(missing_ok=True)
    before = snapshot()
    argv = podman_argv(learner=run.learner, image=run.image, run_id=run.run_id,
                       mounts=run.mounts, name=name, allowed_domains=run.allowed_domains,
                       podman=podman) + expand(run.harness.headless, run.role)
    transcript = run.task_dir / f"transcript-{run.role_name}-{run.label}.log"
    text = prompt(run.role_name, run.harness.output).encode("utf-8")
    start = time.monotonic()
    with _open_private(transcript) as out:
        proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT)
        try:
            proc.stdin.write(text)
        except BrokenPipeError:
            pass
        proc.stdin.close()
        timed_out = _wait(proc, name, run.role.timeout_s, podman)
    duration = time.monotonic() - start
    changed = snapshot() != before
    output, problems, produced = _read_output(run, transcript)
    outcome = Outcome(proc.returncode, timed_out, duration, output, problems, changed,
                      transcript, metrics_mod.from_transcript(transcript))
    error = classify(outcome.rc, timed_out, changed, produced, output, problems)
    log.event(f"llm.launch role={run.role_name}", "ok" if error is None else "error",
              step=run.label, duration_s=duration, rc=outcome.rc, timed_out=timed_out,
              changed=changed, model=run.role.model, effort=run.role.effort,
              harness=run.harness.name, prompt_sha256=hashlib.sha256(text).hexdigest()[:16],
              prompt_bytes=len(text), error_class=getattr(error, "kind", ""),
              **{f"m_{k}": v for k, v in outcome.metrics.items()})
    if error is not None:
        raise error
    return outcome


def run_interactive(*, learner: str, run_id: str, role: Role, harness: Harness, image: str,
                    mounts: Mounts, log: Log, podman: str = "podman") -> int:
    """The owner's `chat` session: same image, same MCP, interactive template, no timeout."""
    name = container_name(learner)
    remove_stale(name, podman)
    argv = podman_argv(learner=learner, image=image, run_id=run_id, mounts=mounts, name=name,
                       interactive=True, podman=podman) + expand(harness.interactive, role)
    start = time.monotonic()
    rc = subprocess.call(argv)
    log.event("llm.launch role=interactive", "ok", duration_s=time.monotonic() - start, rc=rc,
              harness=harness.name, model=role.model)
    if rc in (EXIT_PREFLIGHT, EXIT_FIREWALL, EXIT_API, PODMAN_FAILED):
        raise classify(rc, False, False, False, None, [])
    return rc


def login_ok(*, learner: str, run_id: str, harness: Harness, image: str, log: Log,
             podman: str = "podman", timeout: float = 120) -> bool:
    """Run the template's login check in the image with the learner's home volume."""
    name = container_name(learner, "-login")
    remove_stale(name, podman)
    argv = podman_argv(learner=learner, image=image, run_id=run_id, mounts=Mounts(home=True),
                       name=name, podman=podman) + list(harness.login_check)
    try:
        proc = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.run([podman, "rm", "-f", "--ignore", name], capture_output=True, timeout=60)
        raise Transient("the harness login check timed out") from None
    log.event("llm.login_check", "ok" if proc.returncode == 0 else "error",
              harness=harness.name, rc=proc.returncode)
    if proc.returncode in (0, 1):
        return proc.returncode == 0
    raise classify(proc.returncode, False, False, False, None, []) or Transient("login check")


def run_offline(*, learner: str, run_id: str, image: str, in_dir: Path, out_dir: Path,
                command: list[str], log: Log, timeout: float, podman: str = "podman") -> int:
    """A networkless helper container (SVG rasterising for the reviewer, plan 5.6/3)."""
    name = container_name(learner, "-raster")
    remove_stale(name, podman)
    argv = podman_argv(learner=learner, image=image, run_id=run_id, name=name, network=False,
                       mounts=Mounts(in_dir=in_dir, out_dir=out_dir, home=False),
                       podman=podman) + command
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    timed_out = _wait(proc, name, timeout, podman)
    log.event("llm.offline", "error" if timed_out or proc.returncode else "ok",
              rc=proc.returncode, timed_out=timed_out)
    if timed_out:
        raise Transient("the offline helper container timed out")
    return proc.returncode
