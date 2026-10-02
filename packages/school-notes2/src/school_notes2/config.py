"""The tool's configuration (plan 3.4): one TOML file, no secrets."""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PATH = Path("~/.config/school-notes/config.toml").expanduser()


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Student:
    name: str
    repo: str            # SSH address of the private learner repo
    repo_key: Path       # SSH key that may push it (a per-repo deploy key on the VM)
    site_repo: str       # SSH address of the public site repo (gh-pages)
    site_key: Path
    drive_root: str      # Drive folder id of `Tanulási anyagok/<Tanuló>`
    publish: bool = False


@dataclass(frozen=True)
class Harness:
    """A role template (K10): argv, MCP wiring, output mode and login check."""

    name: str
    headless: list[str]
    interactive: list[str]
    login_check: list[str]
    output: str = "file"          # file | stdout
    prompt_stdin: bool = True     # the fixed prompt goes on stdin


@dataclass(frozen=True)
class Role:
    harness: str
    model: str
    effort: str
    timeout_s: int
    nested_sandbox: bool = False


@dataclass(frozen=True)
class Timeouts:
    drive_call_s: int = 300
    download_package_s: int = 1200
    ls_remote_s: int = 60
    fetch_s: int = 600
    push_s: int = 900
    image_generate_s: int = 600
    rasterize_s: int = 120
    build_s: int = 1800
    browser_check_s: int = 900
    check_public_s: int = 300
    msmtp_s: int = 60


@dataclass(frozen=True)
class Sources:
    max_side_px: int = 2000
    jpeg_quality: int = 85
    pdf_dpi: int = 200
    pages_per_call: int = 30
    ready_after_s: int = 600


@dataclass(frozen=True)
class Limits:
    review_max_images: int = 30
    review_max_diff_kb: int = 300
    image_daily_usd: float = 1.0
    image_reservation_usd: float = 0.05
    min_free_gb: float = 5.0
    chat_lock_alert_h: float = 12.0
    review_closures_per_run: int = 20
    owner_after_open: int = 5
    mcp_wait_s: int = 50


@dataclass(frozen=True)
class Config:
    root: Path
    secrets_dir: Path
    known_hosts: Path
    email_to: str
    git_name: str
    git_email: str
    students: dict[str, Student]
    harnesses: dict[str, Harness]
    roles: dict[str, Role]
    timeouts: Timeouts = field(default_factory=Timeouts)
    sources: Sources = field(default_factory=Sources)
    limits: Limits = field(default_factory=Limits)
    ssh_hostname: str = ""        # e.g. ssh.github.com when port 22 is closed
    ssh_port: int = 22
    release_dir: Path = Path("/srv/school-notes/current")

    def student(self, name: str) -> Student:
        if name not in self.students:
            raise ConfigError(f"unknown learner {name!r}; known: {', '.join(self.students)}")
        return self.students[name]

    def role(self, name: str) -> tuple[Role, Harness]:
        role = self.roles[name]
        return role, self.harnesses[role.harness]

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def log_path(self) -> Path:
        return self.root / "logs" / "school-notes.log"

    def bare(self, student: str, site: bool = False) -> Path:
        return self.root / "git" / f"{student}{'-site' if site else ''}.git"

    def worktree(self, student: str, which: str) -> Path:
        return self.root / "work" / student / which


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _sub(cls, table: dict | None):
    table = table or {}
    known = set(cls.__dataclass_fields__)
    unknown = set(table) - known
    if unknown:
        raise ConfigError(f"[{cls.__name__.lower()}] unknown keys: {', '.join(sorted(unknown))}")
    return cls(**table)


def _student(name: str, t: dict) -> Student:
    if not re.fullmatch(r"[a-z0-9-]+", name):
        raise ConfigError(f"learner name {name!r} must be lowercase ascii")
    try:
        return Student(name=name, repo=t["repo"], repo_key=_path(t["repo_key"]),
                       site_repo=t["site_repo"], site_key=_path(t["site_key"]),
                       drive_root=t["drive_root"], publish=bool(t.get("publish", False)))
    except KeyError as exc:
        raise ConfigError(f"[students.{name}] missing {exc.args[0]}") from None


def _harness(name: str, t: dict) -> Harness:
    if t.get("output", "file") not in ("file", "stdout"):
        raise ConfigError(f"[harnesses.{name}] output must be file or stdout")
    return Harness(name=name, headless=list(t["headless"]), interactive=list(t["interactive"]),
                   login_check=list(t["login_check"]), output=t.get("output", "file"),
                   prompt_stdin=bool(t.get("prompt_stdin", True)))


def _role(name: str, t: dict, harnesses: dict) -> Role:
    if t["harness"] not in harnesses:
        raise ConfigError(f"[roles.{name}] unknown harness {t['harness']!r}")
    if t["effort"] not in ("low", "medium", "high"):
        raise ConfigError(f"[roles.{name}] effort must be at most high (owner rule)")
    return Role(harness=t["harness"], model=t["model"], effort=t["effort"],
                timeout_s=int(t["timeout_s"]), nested_sandbox=bool(t.get("nested_sandbox", False)))


def parse(data: dict) -> Config:
    harnesses = {n: _harness(n, t) for n, t in data.get("harnesses", {}).items()}
    roles = {n: _role(n, t, harnesses) for n, t in data.get("roles", {}).items()}
    for needed in ("writer", "reviewer"):
        if needed not in roles:
            raise ConfigError(f"[roles.{needed}] is required")
    git = data.get("git", {})
    return Config(
        root=_path(data.get("root", "/srv/school-notes")),
        secrets_dir=_path(data.get("secrets_dir", "~/.config/school-notes/secrets")),
        known_hosts=_path(data.get("known_hosts", "~/.config/school-notes/github_known_hosts")),
        email_to=data["email_to"],
        git_name=git["name"], git_email=git["email"],
        ssh_hostname=git.get("ssh_hostname", ""), ssh_port=int(git.get("ssh_port", 22)),
        students={n: _student(n, t) for n, t in data.get("students", {}).items()},
        harnesses=harnesses, roles=roles,
        timeouts=_sub(Timeouts, data.get("timeouts")),
        sources=_sub(Sources, data.get("sources")),
        limits=_sub(Limits, data.get("limits")),
        release_dir=_path(data.get("release_dir", "/srv/school-notes/current")),
    )


def load(path: Path | None = None) -> Config:
    path = path or DEFAULT_PATH
    try:
        with open(path, "rb") as stream:
            return parse(tomllib.load(stream))
    except FileNotFoundError:
        raise ConfigError(f"configuration missing: {path}") from None
    except (KeyError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from None
