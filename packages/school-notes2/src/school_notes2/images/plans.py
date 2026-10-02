"""Image plans and markers (plan 4.6).

The LLM writes `.school-notes/images/<id>.json` and puts `<!-- image: <id> -->` where the
image belongs. The tool keeps a copy under state/image-plans/<learner>/ so a later run can
resume, and builds learning_image.py's job from it.

The job's target is the plan file itself, not the wiki page: the page keeps changing
while the LLM works, and learning_image.py refuses a job whose sources changed.
"""

import hashlib
import json
import re
import shutil
from pathlib import Path

from ..schemas import validate
from ..state.files import write_bytes, write_json
from .settings import ImageSettings

PLAN_ID = re.compile(r"^[a-z0-9-]{1,64}$")
MARKER = re.compile(r"<!-- image: ([a-z0-9-]{1,64}) -->")
IMMUTABLE_PREFIXES = ("sources/", "references/")


class PlanError(ValueError):
    pass


def check_id(plan_id: str) -> str:
    if not isinstance(plan_id, str) or not PLAN_ID.fullmatch(plan_id):
        raise PlanError("plan_id must match ^[a-z0-9-]{1,64}$")
    return plan_id


def job_id(learner: str, plan_id: str) -> str:
    """The ledger key: the ledger is shared by both learners, plan ids are per learner."""
    return f"{learner}-{check_id(plan_id)}"


def target(plan_id: str) -> str:
    return f".school-notes/images/{check_id(plan_id)}.json"


def marker(plan_id: str) -> str:
    return f"<!-- image: {check_id(plan_id)} -->"


def read_plan(path: Path) -> dict:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PlanError(f"plan file missing: {path.name}") from None
    except json.JSONDecodeError as exc:
        raise PlanError(f"plan file is not JSON: {exc.msg}") from None
    validate("image-plan", plan)
    return plan


def find_markers(worktree: Path) -> dict[str, list[str]]:
    """Plan id -> wiki pages (repo-relative) that hold its marker."""
    found: dict[str, list[str]] = {}
    for page in sorted((worktree / "wiki").rglob("*.md")):
        for plan_id in MARKER.findall(page.read_text(encoding="utf-8")):
            found.setdefault(plan_id, []).append(page.relative_to(worktree).as_posix())
    return found


def keep(settings: ImageSettings, plan_id: str) -> Path:
    """Copy the worktree plan to state/image-plans/<learner>/ (validated first)."""
    source = settings.worktree / target(plan_id)
    read_plan(source)
    kept = settings.plans_dir / f"{plan_id}.json"
    write_bytes(kept, source.read_bytes())
    return kept


def restore(settings: ImageSettings, plan_ids: list[str]) -> list[str]:
    """Put kept plans back into a fresh `.school-notes/images/`; returns restored ids."""
    restored = []
    for plan_id in plan_ids:
        kept = settings.plans_dir / f"{check_id(plan_id)}.json"
        dest = settings.worktree / target(plan_id)
        if kept.is_file() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kept, dest)
            restored.append(plan_id)
    return restored


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_job(settings: ImageSettings, plan_id: str) -> dict:
    """learning_image.py's job; the tool fills request_id, learner, target and hashes."""
    tgt = target(plan_id)
    plan = read_plan(settings.worktree / tgt)
    role = plan.pop("role")
    sources = [{"path": tgt, "sha256": _sha(settings.worktree / tgt)}]
    for claim in plan["claims"]:
        path = settings.worktree / claim["source"]
        if (claim["source"].startswith(IMMUTABLE_PREFIXES) and path.is_file()
                and all(s["path"] != claim["source"] for s in sources)):
            sources.append({"path": claim["source"], "sha256": _sha(path)})
    return {"id": job_id(settings.learner, plan_id), "request_id": settings.request_id, "learner": settings.learner,
            "target": tgt, "role": role, "sources": sources, "plan": plan}


def job_path(settings: ImageSettings, plan_id: str) -> Path:
    return settings.plans_dir / f"{check_id(plan_id)}.job.json"


def write_job(settings: ImageSettings, plan_id: str, job: dict) -> Path:
    path = job_path(settings, plan_id)
    write_json(path, job)
    return path


def kept_job(settings: ImageSettings, plan_id: str) -> dict | None:
    path = job_path(settings, plan_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
