"""Builds the per-learner objects every flow needs from the configuration."""

from dataclasses import dataclass
from pathlib import Path

from ..config import Config, Student
from ..git import repos
from ..git.run import Git, Remote
from ..log import Log
from ..notify import Mailer
from ..state.lock import StudentLock


@dataclass
class Ctx:
    cfg: Config
    student: Student
    log: Log
    mailer: Mailer

    @property
    def name(self) -> str:
        return self.student.name

    def remote(self, site: bool = False) -> Remote:
        key = self.student.site_key if site else self.student.repo_key
        return Remote(key, self.cfg.known_hosts, self.cfg.ssh_hostname, self.cfg.ssh_port)

    def bare(self, site: bool = False) -> Git:
        return Git(self.cfg.bare(self.name, site), self.cfg.git_name, self.cfg.git_email,
                   self.log, self.remote(site))

    def worktree(self, which: str) -> Git:
        """`notes` and `review` belong to the private repo, `site` to the site repo."""
        bare = self.bare(site=which == "site")
        return repos.worktree_git(bare, self.cfg.worktree(self.name, which))

    def lock(self) -> StudentLock:
        return StudentLock(self.cfg.state_dir, self.name)

    def task_root(self) -> Path:
        return self.cfg.root


def make(cfg: Config, student: str, console: bool = True) -> Ctx:
    s = cfg.student(student)
    log = Log(cfg.log_path, student=student, console=console)
    mailer = Mailer(cfg.secrets_dir / "msmtprc", cfg.email_to, cfg.state_dir / "notify.json",
                    log, cfg.timeouts.msmtp_s)
    return Ctx(cfg, s, log, mailer)
