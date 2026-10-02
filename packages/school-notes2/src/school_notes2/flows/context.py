"""Builds the per-learner objects every flow needs from the configuration."""

from dataclasses import dataclass
from decimal import Decimal
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

    @property
    def notes_path(self) -> Path:
        return self.cfg.worktree(self.name, "notes")

    def release(self) -> Path:
        """The installed release (template copy) this process runs from."""
        return self.cfg.release_dir.resolve()

    def image_tag(self) -> str:
        """The container image belongs to the release: same tag (plan 10.1)."""
        return f"localhost/school-notes-agent:{self.release().name}"

    def tools_dir(self) -> Path:
        return self.release() / "tools"

    def image_settings(self):
        from ..images.settings import ImageSettings
        state, limits = self.cfg.state_dir, self.cfg.limits
        return ImageSettings(
            learner=self.name, worktree=self.notes_path,
            script=self.tools_dir() / "learning_image.py",
            state_root=state / "images", plans_root=state / "image-plans",
            lock_path=state / "images.lock", key_file=self.cfg.secrets_dir / "openrouter.key",
            max_total_usd=Decimal(str(limits.image_year_total_usd)),
            learner_max_usd=Decimal(str(limits.image_year_learner_usd)),
            daily_usd=Decimal(str(limits.image_daily_usd)),
            reservation_usd=Decimal(str(limits.image_reservation_usd)),
            timeout_s=self.cfg.timeouts.image_generate_s)


def make(cfg: Config, student: str, console: bool = True) -> Ctx:
    s = cfg.student(student)
    log = Log(cfg.log_path, student=student, console=console)
    mailer = Mailer(cfg.secrets_dir / "msmtprc", cfg.email_to, cfg.state_dir / "notify.json",
                    log, cfg.timeouts.msmtp_s)
    return Ctx(cfg, s, log, mailer)
