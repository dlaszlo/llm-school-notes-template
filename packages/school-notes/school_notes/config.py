"""Trusted secret-free configuration; source material cannot select execution."""
import json
from pathlib import Path
import re

from .common import Blocked


def load(path):
    value = json.loads(Path(path).read_text())
    required = ("state_db", "lock_file", "jobs_dir", "captures_dir", "reports_dir", "drive_tool", "prepare_photo", "agents", "renderer", "learners", "git_identity")
    if not isinstance(value, dict) or any(k not in value for k in required):
        raise Blocked("configuration missing required fields")
    for key in required[:7]:
        if not isinstance(value[key], str) or not Path(value[key]).is_absolute():
            raise Blocked(f"configuration requires absolute path: {key}")
    if not isinstance(value["learners"], dict) or not value["learners"]:
        raise Blocked("at least one learner configuration required")
    for name, learner in value["learners"].items():
        if not re.fullmatch(r"[a-z0-9_-]+", name):
            raise Blocked("invalid learner identifier")
        for key in ("repo", "drive_config_dir", "drive_evidence"):
            if not Path(learner.get(key, "")).is_absolute():
                raise Blocked(f"learner requires explicit absolute {key}")
        for key in ("archive_id", "output_id"):
            if not re.fullmatch(r"[A-Za-z0-9_-]+", learner.get(key, "")):
                raise Blocked(f"learner requires explicit Drive {key}")
        reader=learner.get('drive_reader')
        if reader is not None and (not isinstance(reader,dict) or set(reader)!={'config_dir','scope','evidence'} or reader['scope']!='https://www.googleapis.com/auth/drive.readonly' or not Path(reader['config_dir']).is_absolute() or not Path(reader['evidence']).is_absolute()):
            raise Blocked('drive_reader requires explicit absolute config_dir/evidence and exact drive.readonly scope')
        inputs = learner.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise Blocked("learner requires explicit inputs list of ready roots, subject and source role")
        ready_ids = set()
        for source in inputs:
            if not isinstance(source, dict) or not re.fullmatch(r"[A-Za-z0-9_-]+", source.get("ready_id", "")) or source["ready_id"] in ready_ids:
                raise Blocked("invalid/duplicate ready-root ID")
            ready_ids.add(source["ready_id"])
            if source.get('source_role')=='teacher_background':
                raise Blocked('teacher_background roots are local reference material, excluded from application inputs')
            if not re.fullmatch(r"[a-z0-9_-]+", source.get("subject_slug", "")) or source.get("source_role") not in ("notebook", "teacher_learn"):
                raise Blocked("input root requires known subject_slug and source_role context")
        if not re.fullmatch(r"[a-f0-9]{40}", learner.get("observed_sha", "")):
            raise Blocked("learner requires verified initial observed_sha")
    if not 1 <= value.get("run_seconds", 3000) <= 7200 or value.get("reserve_bytes", 4 * 1024**3) < 0:
        raise Blocked("invalid run window/disk reserve")
    prefix=value.get("interactive_command")
    if prefix is not None and (not isinstance(prefix,list) or not prefix or not all(isinstance(x,str) and "\0" not in x for x in prefix) or not Path(prefix[0]).is_absolute()):
        raise Blocked("interactive_command requires a trusted absolute launcher prefix")
    if value.get("paid_images_enabled", False):
        raise Blocked("paid media disabled until cumulative ledger migration and provider proof")
    return value
