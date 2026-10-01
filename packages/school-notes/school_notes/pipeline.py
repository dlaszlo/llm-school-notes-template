"""Resumable single-heavy-process supervisor. All external writes are effects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid

from .agents import Agent, InvalidManifestProposal
from .common import PreconditionFailed, Blocked, EffectPending, QuotaBlocked, TimedOut, Transient, Window, WindowExhausted, atomic_json, digest, disk_gate, file_hash, now, private_dir, run, safe_relative
from .drive import Archive, FOLDER, InvalidPageToken, InventoryChanged, capture, check_classification, inventory, snapshot_signature
from .verify import Git, CandidateViolation, OwnerPolicyViolation, Renderer, manifest_with_hashes, agent_manifest, review_gate, scan


def register_external(state,git,learner,base,head,*,ready=True,provenance=None):
    """One committed range key for observer and owner-session finalization."""
    if base==head:return None
    if base not in git.git('rev-list',head).splitlines():raise Blocked('external range diverged from current acknowledgement; assess possible history rewrite and current remote; explicit owner checkout reconciliation then observer maintenance required, no automatic rebase/push')
    hashes=git.committed_changes(base,head)
    key='external-review:'+digest({'repo':str(git.repo),'base':base,'head':head,'hashes':hashes})
    existing=state.rows('SELECT id FROM jobs WHERE stable_key=?',(key,))
    payload={'base':base,'head':head,'changes':hashes,**(provenance or {}),'provisional':not ready}
    job_id=state.enqueue('external_change_review',learner,key,payload)
    retained=state.job(job_id)
    promote=ready and retained['state']=='review_wait' and retained['payload'].get('provisional') and (retained['error'] or '').startswith('retained owner changes:') and not state.rows("SELECT id FROM reviews WHERE job_id=? AND state='accepted'",(job_id,))
    if not existing or promote:
        state.update_job(job_id,'queued' if ready else 'review_wait','external_review',payload,error=None if ready else 'retained owner changes: commit and push, then run-once; receipt is provenance only')
    # Accepted/complete/review_wait jobs are never reset by another receipt.
    if ready:
        with state.db:
            state.db.execute("UPDATE jobs SET state='superseded' WHERE learner=? AND kind='external_change_review' AND id!=? AND state IN ('queued','review_wait','blocked','retry_wait') AND NOT EXISTS (SELECT 1 FROM reviews WHERE reviews.job_id=jobs.id AND reviews.state='accepted')",(learner,job_id))
    return job_id


def register_divergence(state,git,learner,base,head):
    """Observer-only manual maintenance range; never model-review authority."""
    payload={'base':base,'head':head,'merge_base':git.merge_base(base,head),'changes':git.committed_changes(base,head),'origin':'git-observer','observer_only':True}
    key='divergence-maintenance:'+digest({'repo':str(git.repo),**payload})
    existing=state.rows('SELECT id FROM jobs WHERE stable_key=?',(key,))
    job_id=state.enqueue('divergence_maintenance',learner,key,payload)
    if not existing:
        state.update_job(job_id,'maintenance_wait','maintenance',error='history divergence/retraction: exact direct-owner acknowledge-maintenance required; no model processing')
    return job_id


class Supervisor:
    def __init__(self, config, state, lock, drive_factory):
        self.config, self.state, self.lock, self.drive_factory = config, state, lock, drive_factory
        self.window = Window(config.get("run_seconds", 3000))
        if lock:
            lock.window = self.window
        self.agents = Agent(config["agents"], state, lock, self.window)
        self.drives = {}

    def drive(self, learner):
        if learner not in self.drives:
            self.drives[learner] = self.drive_factory(learner)
        return self.drives[learner]

    def input_drive(self, learner):
        api=self.drive(learner)
        return getattr(api,"input_reader",api)

    def learner(self, name):
        return self.config["learners"][name]

    def job_dir(self, job):
        return private_dir(Path(self.config["jobs_dir"]) / str(job["id"]))

    def run_once(self, *, initialize_inventory=False, learners=None, job_id=None):
        learners=list(self.config["learners"]) if learners is None else list(learners)
        if job_id is not None and self.state.job(job_id)["learner"] not in learners:raise Blocked("selected job belongs to another learner")
        eligible=[]
        for learner in learners:
            try:self.preflight_owner([learner],allow_behind=getattr(self,"actor_origin",None)!="owner-session")
            except (Blocked,OSError,ValueError,KeyError) as error:self.record_runtime_block(learner,str(error),category='git')
            else:eligible.append(learner)
        learners=eligible
        if not learners:return self.status()
        # Excluded learners retain running attempts/effects/retry jobs exactly.
        self.state.recover(learners=learners)
        for row in self.state.rows("SELECT id,learner,payload FROM jobs WHERE state='retry_wait'"):
            if row['learner'] not in learners:continue
            payload = json.loads(row["payload"])
            if payload.get("retry_at", float("inf")) <= time.time() and not payload.get("quota_block"):
                self.state.update_job(row["id"], "queued")
        for ledger in self.config.get("required_ledgers", []):
            if not Path(ledger).is_file():
                raise Blocked(f"required executor ledger missing: {ledger}; recovery required")
        self.lock.phase("observe")
        blocked_git=set()
        for learner in learners:
            category='git'
            try:
                self.observe_git(learner)
                self.clear_runtime_blocks(learner,'git')
                category='drive'
                if not initialize_inventory and self.state.meta(f"drive-baseline:{learner}") != "complete":
                    raise Blocked("initial Drive inventory unfinished; admin baseline-inventory required")
                self.observe_drive(learner, initialize_inventory)
            except WindowExhausted:
                break
            except (Blocked, OSError, ValueError, KeyError) as e:
                self.record_runtime_block(learner, str(e),category=category)
                if category=='git':blocked_git.add(learner)
        jobs = self.state.rows("SELECT id FROM jobs WHERE state='queued' ORDER BY id")
        for row in jobs:
            job = self.state.job(row["id"])
            if job["learner"] not in learners or job['learner'] in blocked_git or (job_id is not None and job["id"]!=job_id):continue
            # Baseline Git acknowledgement is an explicit gate. It cannot be
            # inferred from a clean checkout or bypassed by first ingestion.
            baseline = self.state.rows("SELECT * FROM observations WHERE id=?", (f"baseline:{job['learner']}",))
            recovering_push=job['phase'] in ('push','family_output') and self.state.rows("SELECT stable_key FROM effects WHERE job_id=? AND kind='git-push' AND state IN ('unknown','inflight','verified')",(job['id'],))
            if not recovering_push and job["kind"] in ("ingest", "metadata_update") and (not baseline or not baseline[0]["ack_sha"]):
                self.state.update_job(job["id"], "ack_wait", error="baseline Git closure/import evidence missing")
                continue
            if not recovering_push and job["kind"] in ("ingest", "metadata_update") and baseline[0]["ack_sha"] != baseline[0]["observed_sha"]:
                self.state.update_job(job["id"], "ack_wait", error="external Git range remains unacknowledged")
                continue
            if job['kind']=='divergence_maintenance':
                self.state.update_job(job['id'],'maintenance_wait','maintenance',error='observer-only divergence: exact direct-owner acknowledge-maintenance required; no model processing')
                continue
            if job["kind"] in ("runtime_block", "capture_block"):
                continue
            active = self.state.rows("SELECT id FROM jobs WHERE package_id=? AND state='running'", (job["package_id"],)) if job["package_id"] else []
            if active:
                continue
            try:
                self.window.require(30)
                self.state.update_job(job["id"], "running")
                self.process(job["id"])
            except (Blocked, OSError, ValueError, KeyError) as e:
                current = self.state.job(job["id"])
                if current["state"] == "running":
                    payload = current["payload"]
                    if isinstance(e, WindowExhausted):
                        self.state.update_job(job["id"], "queued", error=str(e))
                        break
                    elif isinstance(e, EffectPending):
                        payload["retry_at"] = time.time() + 60
                        self.state.update_job(job["id"], "retry_wait", payload=payload, error=str(e))
                    elif isinstance(e, QuotaBlocked):
                        payload["quota_block"] = True
                        self.state.update_job(job["id"], "retry_wait", payload=payload, error=str(e))
                    elif isinstance(e, (Transient, TimedOut)) and payload.get("technical_retries", 0) < 3:
                        count = payload.get("technical_retries", 0) + 1
                        attempt_phase=payload.get('active_attempt_phase',current['phase'])
                        if attempt_phase.split(':')[0]!=current['phase']:attempt_phase=current['phase']
                        timed_out = self.state.rows("SELECT id FROM attempts WHERE job_id=? AND phase=? AND state='timeout'", (job["id"], attempt_phase))
                        if len(timed_out) >= 2:
                            self.state.update_job(job["id"], "blocked", error=f"second phase timeout: {attempt_phase} ({len(timed_out)}/2); inspect-job, smaller task/manual continuation required")
                        else:
                            payload.update(technical_retries=count, retry_at=time.time() + 60 * 2**(count - 1))
                            self.state.update_job(job["id"], "retry_wait", payload=payload, error=str(e))
                    elif isinstance(e, OwnerPolicyViolation):
                        payload['owner_policy_failure']={'base':payload.get('base'),'reason':str(e),'path':e.path,'origin':'supervisor-policy-gate'}
                        self.state.update_job(job['id'],'blocked',payload=payload,error=str(e))
                    else:
                        self.state.update_job(job["id"], "blocked", error=str(e))
        self.lock.phase("report")
        return self.status()

    def preflight_owner(self,learners,*,allow_behind=False):
        for learner in learners:
            git=Git(self.learner(learner)['repo'],self.lock)
            try:
                git.clean()
                # Strict owner processing checks the current remote without moving HEAD.
                if not allow_behind and self.learner(learner).get('fetch',True):git.git('fetch','--no-tags','origin','main')
                head=git.head();remote=git.git('rev-parse','refs/remotes/origin/main')
                if head!=remote and not (allow_behind and head in git.git('rev-list',remote).splitlines()):
                    raise Blocked(git.reconciliation_message(head,remote))
            except Blocked as error:
                from .common import Busy
                prefix='owner editing pauses Git processing' if getattr(self,'actor_origin',None)=='owner-session' else 'Git processing paused for this learner'
                raise Busy(prefix+'; sync remains available: '+str(error)) from None

    def sync(self,learners):
        for ledger in self.config.get('required_ledgers',[]):
            if not Path(ledger).is_file():raise Blocked('required executor ledger missing; recovery required')
        self.lock.phase('sync')
        for learner in learners:
            try:
                # No checkout merge/normalization during observation-only sync.
                git=Git(self.learner(learner)['repo'],self.lock);git.clean()
                git.git('fetch','--no-tags','origin','main')
                remote=git.git('rev-parse','refs/remotes/origin/main');head=git.head()
                if head!=remote:
                    if head in git.git('rev-list',remote).splitlines():raise Blocked('owner checkout behind origin/main; observation-only sync does not merge; standalone run-once or explicit owner fast-forward required')
                    raise Blocked(git.reconciliation_message(head,remote))
                self.observe_git(learner,allow_fast_forward=False)
                self.clear_runtime_blocks(learner,'git')
            except (Blocked,OSError,ValueError,KeyError) as error:self.record_runtime_block(learner,str(error),category='git')
            try:
                if self.state.meta(f'drive-baseline:{learner}')!='complete':raise Blocked('initial Drive inventory unfinished; baseline-inventory required')
                self.observe_drive(learner)
            except WindowExhausted:break
            except (Blocked,OSError,ValueError,KeyError) as error:self.record_runtime_block(learner,str(error),category='drive')
        return self.status()

    @staticmethod
    def stable_reason(reason):
        if reason.startswith('disk:'):
            return 'disk-space: insufficient reserve for next phase; inspect retained diagnostics'
        return reason

    def clear_runtime_blocks(self,learner,category):
        # Legacy uncategorized blockers stay visible until an explicit owner
        # disposition; a Drive survey cannot prove their Git condition repaired.
        for row in self.state.rows("SELECT id,payload FROM jobs WHERE learner=? AND kind='runtime_block' AND state='blocked'",(learner,)):
            if json.loads(row['payload']).get('category')==category:self.state.update_job(row['id'],'complete',error=None)

    def record_runtime_block(self, learner, reason, *, category='drive'):
        if category not in ('git','drive'):raise Blocked('invalid runtime block category')
        stable=self.stable_reason(reason)
        key = f"runtime-block:{learner}:{category}:{digest(stable)}"
        job_id = self.state.enqueue("runtime_block", learner, key, {"reason": stable,'category':category})
        job=self.state.job(job_id);job['payload']['latest_diagnostic']=reason
        self.state.update_job(job_id, "blocked",payload=job['payload'], error=stable)

    def observe_git(self, learner, *, allow_fast_forward=True):
        settings = self.learner(learner)
        git = Git(settings["repo"], self.lock)
        # Reconcile a possibly successful own push before treating its remote
        # HEAD as an external change, even if Drive has a newer revision.
        for effect in self.state.rows("SELECT e.* FROM effects e JOIN jobs j ON j.id=e.job_id WHERE j.learner=? AND e.kind='git-push' AND e.state IN ('unknown','inflight')", (learner,)):
            receipt = git.push_reconcile(effect)
            if receipt and receipt.get("verified") is True:
                self.state.effect_state(effect["stable_key"], "verified", receipt, receipt["external_id"])
        head = git.inspect(fetch=settings.get("fetch", True), allow_fast_forward=allow_fast_forward and getattr(self,"actor_origin",None)!="owner-session")
        baseline = self.state.rows("SELECT * FROM observations WHERE id=?", (f"baseline:{learner}",))
        if not baseline:
            raise Blocked("learner baseline missing")
        old = baseline[0]['ack_sha'] or self.state.meta(f'baseline-initial:{learner}') or json.loads(baseline[0]['manifest']).get('observed_sha')
        if not old:raise Blocked('immutable initial Git baseline missing; no inferred external range')
        if head == baseline[0]["observed_sha"]:
            return
        known = self.state.rows("SELECT receipt FROM effects WHERE kind='git-push' AND state='verified' AND artifact_hash=?", (head,))
        if known:
            with self.state.db:
                self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=?,state='complete' WHERE id=?", (head, head, f"baseline:{learner}"))
            self.state.wake_ack_waiters(learner)
            return
        if old in git.git('rev-list',head).splitlines():register_external(self.state,git,learner,old,head)
        else:register_divergence(self.state,git,learner,old,head)
        with self.state.db:
            self.state.db.execute("UPDATE observations SET observed_sha=? WHERE id=?", (head, f"baseline:{learner}"))

    def observe_drive(self, learner, baseline=False):
        api = self.input_drive(learner)
        observation_id = str(uuid.uuid4())
        self.state.observation(observation_id, learner)
        # Token invalidation restarts one full survey. No old partial list is
        # reused as a checkpoint or mistaken for an empty input folder.
        try:
            surveys = [(source, inventory(api, source["ready_id"], self.window.require, strict_names=False)) for source in self.learner(learner)["inputs"]]
        except InvalidPageToken:
            observation_id = str(uuid.uuid4())
            self.state.observation(observation_id, learner)
            surveys = [(source, inventory(api, source["ready_id"], self.window.require, strict_names=False)) for source in self.learner(learner)["inputs"]]
        self.state.observation(observation_id, learner, [{"input": source, "inventory": complete} for source, complete in surveys], "complete")
        roots = []
        visible_sources=set()
        for source, complete in surveys:
            found = [f for f in complete if f.get("parents") == [source["ready_id"]] and not f.get("root")]
            for f in found:
                visible_sources.add(f["id"])
                if f["mimeType"] != FOLDER:
                    self.capture_block(learner, f["id"], source, baseline, None, "ready-root loose file: put it in a complete package folder", digest(f))
                else:
                    roots.append((source, f))
        for block in self.state.rows("SELECT j.id,j.payload,p.source_id FROM jobs j JOIN packages p ON p.id=j.package_id WHERE j.learner=? AND j.kind='capture_block' AND j.state='blocked'",(learner,)):
            if block['source_id'] not in visible_sources:
                payload=json.loads(block['payload'])
                payload['visibility']='absent from complete configured ready-root observation; retained, not resolved'
                self.state.update_job(block['id'],'blocked',payload=payload,error=f"source package absent from configured ready roots; capture retained; restore source or reject-package {block['id']}")
        # No capture/classification occurs until the root's whole traversal is
        # complete. Each package additionally gets before/after inventories.
        for source, root in roots:
            rows = self.state.rows("SELECT r.manifest FROM revisions r JOIN packages p ON p.id=r.package_id AND p.current_seq=r.seq WHERE p.learner=? AND p.source_id=?", (learner, root["id"]))
            previous = json.loads(rows[0]["manifest"]) if rows else None
            if previous is None:
                blocks=self.state.rows("SELECT payload FROM jobs WHERE learner=? AND kind='capture_block' AND package_id=(SELECT id FROM packages WHERE learner=? AND source_id=?) ORDER BY id DESC",(learner,learner,root['id']))
                for block in blocks:
                    staging=json.loads(block['payload']).get('staging')
                    progress=Path(staging)/'progress.json' if staging else None
                    if progress and progress.is_file():
                        saved=json.loads(progress.read_text())
                        previous={'files':saved['captured'],'snapshot_hash':snapshot_signature(saved['inventory'])}
                        break
            path = Path(self.config["captures_dir"]) / str(uuid.uuid4())
            try:
                manifest = capture(api, root["id"], path, self.config.get("reserve_bytes", 4 * 1024**3), previous, self.window.require)
            except WindowExhausted:
                raise
            except (Blocked, OSError, ValueError, KeyError) as error:
                self.capture_block(learner, root["id"], source, baseline, str(path), str(error), digest(root))
                continue
            context = {"subject_slug": source["subject_slug"], "source_role": source["source_role"]}
            manifest["input_context"] = context
            manifest["metadata_hash"] = digest({"content": manifest["metadata_hash"], "input_context": context})
            self.state.revision(learner, root["id"], manifest, baseline=baseline)
            with self.state.db:
                self.state.db.execute("UPDATE jobs SET state='complete',error=NULL WHERE kind='capture_block' AND learner=? AND package_id=(SELECT id FROM packages WHERE learner=? AND source_id=?)", (learner, learner, root["id"]))
        self.clear_runtime_blocks(learner,'drive')
        if baseline:
            self.state.meta(f"drive-baseline:{learner}", "complete")

    def capture_block(self, learner, source_id, source, baseline, staging, reason, fingerprint):
        with self.state.db:
            self.state.db.execute("INSERT OR IGNORE INTO packages(learner,source_id,state) VALUES (?,?,?)",
                                  (learner, source_id, "baseline_pending" if baseline else "detected"))
        package_id = self.state.rows("SELECT id FROM packages WHERE learner=? AND source_id=?", (learner, source_id))[0]["id"]
        staging=staging if staging and Path(staging).is_dir() else None
        stable=self.stable_reason(reason)
        key = f"capture-block:{learner}:{source_id}:{fingerprint}:{digest(stable)}"
        job_id = self.state.enqueue("capture_block", learner, key, {"source_id": source_id, "input_context": source, "staging": staging, "reason": stable}, package_id)
        saved=self.state.job(job_id)['payload']
        if staging and Path(staging).is_dir() and staging!=saved.get('staging'):
            saved.setdefault('retained_staging',[]).append(staging)
        saved['latest_diagnostic']=reason
        self.state.update_job(job_id, "blocked",payload=saved,error=stable)

    def envelope(self, job, phase, inputs, **extra):
        return {"job_id": job["id"], "revision_seq": job["revision_seq"], "phase": phase, "inputs": inputs, **extra}

    def source_inputs(self, manifest):
        result = []
        for f in manifest["files"]:
            result.append({"id": f["id"], "path": f.get("read_source", f.get("prepared", f["local"])), "sha256": f.get("prepared_sha256", f["sha256"]), "kind": "source"})
            result.extend(f.get("source_pages", []))
        return result

    def prepare(self, job):
        manifest = job["payload"]["manifest"]
        for f in manifest["files"]:
            if file_hash(f["local"]) != f["sha256"]:
                raise Blocked("captured original changed")
            originals = private_dir(self.job_dir(job) / "archive-inputs")
            original = Path(f['archive_original']) if f.get('archive_original') else originals / (digest(f["id"])[:16] + Path(f["local"]).suffix)
            if original.exists() and file_hash(original) != f["sha256"]:
                raise Blocked("staged archive original changed")
            if not original.exists():
                disk_gate(originals, f["size"], self.config.get("reserve_bytes", 4 * 1024**3))
                shutil.copyfile(f["local"], original)
                os.chmod(original, 0o400)
            f["archive_original"] = str(original)
            if f["mimeType"].startswith("image/"):
                if f.get("prepared") and Path(f["prepared"]).is_file() and file_hash(f["prepared"]) == f.get("prepared_sha256"):
                    continue
                dest = private_dir(self.job_dir(job) / f"prepared-{job['payload'].get('prepare_attempt',0)}") / safe_relative(f["path"])
                private_dir(dest.parent)
                if dest.exists():
                    raise Blocked("unbound prepared photo retained; retry-prepare preserves it and selects a fresh attempt")
                disk_gate(dest.parent, f["size"] * 2, self.config.get("reserve_bytes", 4 * 1024**3))
                temporary = dest.with_name(dest.stem + ".tmp-" + str(uuid.uuid4()) + dest.suffix)
                run([self.config["agents"]["python"], self.config["prepare_photo"], f["archive_original"], str(temporary)], self.job_dir(job), timeout=120, lock=self.lock, log=self.job_dir(job) / f"prepare-{digest(f['id'])[:12]}.log")
                sha = file_hash(temporary)
                os.chmod(temporary, 0o400)
                os.replace(temporary, dest)
                f["prepared"] = str(dest)
                f["prepared_sha256"] = sha
                self.state.update_job(job["id"], payload=job["payload"])
        # Every provider input is an immutable, bound file beneath this private
        # job. Capture paths/metadata-bearing originals are never broad read
        # permissions. PDFs additionally expose every page as an actual image.
        inputs = private_dir(self.job_dir(job) / "inputs")
        for f in manifest["files"]:
            source = Path(f.get("prepared", f["local"]))
            sha = f.get("prepared_sha256", f["sha256"])
            target = Path(f['read_source']) if f.get('read_source') else inputs / (digest(f["id"])[:16] + source.suffix.lower())
            if target.exists() and file_hash(target) != sha:
                raise Blocked("staged provider source bytes changed")
            if not target.exists():
                disk_gate(inputs, source.stat().st_size, self.config.get("reserve_bytes", 4 * 1024**3))
                shutil.copyfile(source, target)
                os.chmod(target, 0o400)
            f["read_source"] = str(target)
            if f["mimeType"] == "application/pdf":
                count_output = run([self.config["renderer"]["pdfinfo"], str(target)], inputs, lock=self.lock)
                match = re.search(r"Pages:\s+(\d+)", count_output)
                if not match or int(match[1]) < 1:
                    raise Blocked("source PDF has no verified page count")
                count = int(match[1])
                if f.get('source_pages') and len(f['source_pages'])==count and all(file_hash(page['path'])==page['sha256'] for page in f['source_pages']):
                    continue
                page_base = digest(f["id"])[:16] + "-pages"
                page_dir = private_dir(inputs / page_base)
                for attempt in range(3 + job["payload"].get("source_render_extra", 0)):
                    page_dir = private_dir(inputs / (page_base + f"-{attempt}"))
                    if (page_dir / "pages.json").exists() or not list(page_dir.glob("page-*.png")):
                        break
                else:
                    raise Blocked("source PDF partial attempts retained; retry-render source required")
                manifest_path = page_dir / "pages.json"
                if manifest_path.exists():
                    saved = json.loads(manifest_path.read_text())
                    pages = saved["pages"]
                    if saved["source_sha256"] != sha or len(pages) != count or any(file_hash(p["path"]) != p["sha256"] for p in pages):
                        raise Blocked("retained source PDF page images changed")
                else:
                    if list(page_dir.glob("page-*.png")):
                        raise Blocked("partial source PDF image render retained; explicit recovery required")
                    disk_gate(page_dir, count * 3 * 1024**2, self.config.get("reserve_bytes", 4 * 1024**3))
                    self.window.require(305)
                    run([self.config["renderer"]["pdftoppm"], "-scale-to", "1800", "-png", str(target), str(page_dir / "page")],
                        page_dir, timeout=300, lock=self.lock, log=self.job_dir(job) / f"source-pdf-{digest(f['id'])[:12]}.log")
                    images = sorted(page_dir.glob("page-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
                    if len(images) != count:
                        raise Blocked("source PDF page image coverage incomplete")
                    pages = [{"id": f"{f['id']}:page:{i}", "path": str(p), "sha256": file_hash(p), "kind": "source-pdf-page"} for i, p in enumerate(images, 1)]
                    for page in images:
                        os.chmod(page, 0o400)
                    atomic_json(manifest_path, {"source_sha256": sha, "pages": pages})
                f["source_pages"] = pages
        self.state.update_job(job["id"], payload=job["payload"])
        with self.state.db:
            self.state.db.execute("UPDATE revisions SET manifest=? WHERE package_id=? AND seq=?", (json.dumps(manifest), job["package_id"], job["revision_seq"]))

    def stable(self, job):
        if not self.state.current(job):
            raise Blocked("candidate revision is stale; reconciliation and renewed reviews required")
        live = inventory(self.input_drive(job["learner"]), job["payload"]["manifest"]["source_id"], self.window.require)
        if snapshot_signature(live) != job["payload"]["manifest"]["snapshot_hash"]:
            old=job['payload']['manifest']
            fresh=capture(self.input_drive(job['learner']),old['source_id'],private_dir(self.job_dir(job)/('location-check-'+str(uuid.uuid4()))),self.config.get('reserve_bytes',4*1024**3),old,self.window.require)
            parents=next(f.get('parents',[]) for f in fresh['inventory'] if f.get('root'))
            sources=[source for source in self.learner(job['learner'])['inputs'] if parents==[source['ready_id']]]
            if len(sources)!=1:
                raise Blocked('package left configured ready roots; no finalization')
            context={k:sources[0][k] for k in ('subject_slug','source_role')}
            fresh['input_context']=context
            fresh['metadata_hash']=digest({'content':fresh['metadata_hash'],'input_context':context})
            if fresh['metadata_hash']!=old['metadata_hash'] or sorted((f['id'],f['sha256']) for f in fresh['files'])!=sorted((f['id'],f['sha256']) for f in old['files']):
                raise Blocked('source bytes/context changed; observe new revision and reconcile before finalization')
            old.update(inventory=fresh['inventory'],snapshot_hash=fresh['snapshot_hash'])
            self.state.update_job(job['id'],payload=job['payload'])

    def process(self, job_id):
        if self.state.job(job_id)['kind']=='divergence_maintenance':raise Blocked('observer-only divergence maintenance cannot enter model processing; acknowledge-maintenance required')
        while True:
            job = self.state.job(job_id)
            phase = job["phase"]
            if job['payload'].get('quota_block'):
                self.state.update_job(job_id,'retry_wait',error='provider quota block: clear-quota requires verified reset/direct-admin evidence')
                return
            if job['kind'] in ('ingest','metadata_update') and phase in ('source_review','render','review','commit'):
                ack=self.state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
                if job['payload'].get('base')!=ack:
                    self.state.update_job(job_id,'blocked',error='candidate base is no longer current ack: rebase-candidate before further review/render')
                    return
            finishing_push=phase in ('push','family_output','public') and bool(self.state.rows("SELECT stable_key FROM effects WHERE job_id=? AND kind='git-push' AND state IN ('verified','unknown','inflight')",(job_id,)))
            if job['package_id'] and not self.state.current(job) and not finishing_push:
                self.state.update_job(job_id,'blocked',error='stale revision: reconcile-job before any further agent/render work')
                return
            self.lock.phase(f"job-{job_id}:{phase}")
            if job["kind"] == "external_change_review":
                return self.external_review(job)
            if job["kind"] == "public_release":
                return self.public(job)
            payload = job["payload"]
            directory = self.job_dir(job)
            if phase == "capture":
                self.prepare(job)
                self.state.update_job(job_id, phase="classify")
            elif phase == "classify":
                raw_context = {"input_context": payload["manifest"].get("input_context"), "descriptions": [{"id": f["id"], "description": f.get("description", "")[:8000]} for f in payload["manifest"]["inventory"]]}
                answers = self.state.rows("SELECT id,scope,answer,origin,answer_hash FROM questions WHERE job_id=? AND kind='content' AND state='answered'", (job_id,))
                matches = []
                source_hashes = {f["sha256"] for f in payload["manifest"]["files"]}
                for prior in self.state.rows("SELECT r.manifest,p.source_id,p.id FROM revisions r JOIN packages p ON r.package_id=p.id AND r.seq=p.current_seq WHERE p.learner=? AND p.id!=?", (job["learner"], job["package_id"])):
                    hashes = {f["sha256"] for f in json.loads(prior["manifest"])["files"]}
                    if source_hashes & hashes:
                        matches.append({"package_id": prior["id"], "source_id": prior["source_id"], "shared_hashes": sorted(source_hashes & hashes)})
                if matches and not any(a["scope"] == "duplicate-origin" for a in answers):
                    payload["duplicate_origin"] = matches
                    question = self.state.question(job_id, "content", "duplicate-origin", "Identical source bytes were uploaded in another package. Confirm the distinct educational context or request linking to the existing source; identical images are not automatically another lesson.")
                    self.state.update_job(job_id, "question_wait", payload=payload, error=f"question {question}: duplicate source origin")
                    return
                envelope = self.envelope(job, phase, self.source_inputs(payload["manifest"]), private_metadata=raw_context, answers=answers, duplicate_origin=matches)
                result, path = self.agents.call(job, phase, envelope, directory, directory, "Classify EACH actual source file, including every PDF page; identify book/reference material. Return sanitized source_context: educational context only, never private names/health/family/school/class/grades. Author is distinct from target learner; missing Description never proves learner authorship. Preserve classmate/catch-up meaning as author=other and purpose=catch_up without private identity. Subject/role folder is context, never proof of source class. No edits. Unknown/mixed/book-suspect means question, never partial package release.")
                payload["classification"] = result["classification"]
                payload["classification_result"] = str(path)
                try:
                    if result["status"] != "complete" or result["uncertainties"]:
                        raise Blocked("classification has unresolved uncertainty")
                    check_classification(payload["manifest"]["files"], result["classification"], payload["manifest"]["input_context"]["source_role"])
                    if set(result["coverage"]) != {f["path"] for f in envelope["inputs"]} or not result["evidence"]:
                        raise Blocked("classification lacks exact source/PDF-page coverage")
                    if result["source_context"] is None or result["source_context"]["subject_slug"] != payload["manifest"]["input_context"]["subject_slug"]:
                        raise Blocked("safe source context/subject unresolved")
                except Blocked as e:
                    q = self.state.question(job_id, "content", "source-classification", str(e))
                    self.state.update_job(job_id, "question_wait", payload=payload, error=f"question {q}: {e}")
                    return
                payload["manifest"]["source_context"] = result["source_context"]
                with self.state.db:
                    self.state.db.execute("UPDATE revisions SET manifest=? WHERE package_id=? AND seq=?", (json.dumps(payload["manifest"]), job["package_id"], job["revision_seq"]))
                self.state.update_job(job_id, phase="archive", payload=payload)
            elif phase == "archive":
                self.stable(job)
                archive = Archive(self.drive(job["learner"]), self.state, self.learner(job["learner"])["archive_id"], self.window.require)
                payload["archive_receipts"] = archive.package(job, payload["classification"])
                self.state.update_job(job_id, phase="candidate", payload=payload)
            elif phase == "candidate":
                self.candidate(job)
            elif phase == "source_review":
                self.content_review(job)
            elif phase == "render":
                renderer = Renderer(self.config["renderer"], self.lock, self.window)
                attempt = payload.get("render_attempt", 0)
                render_dir = directory / f"render-{payload.get('fix_round',0)}-{attempt}"
                if (render_dir / "build").exists() and not (render_dir / "complete.json").exists():
                    attempt += 1
                    if attempt >= 3:
                        raise Blocked("three retained partial renders: manual continuation required")
                    payload["render_attempt"] = attempt
                    self.state.update_job(job_id, payload=payload)
                    render_dir = directory / f"render-{payload.get('fix_round',0)}-{attempt}"
                build, images = renderer.build(payload["worktree"], payload["private_manifest"], render_dir)
                payload.update(build=str(build), pdf_images=images, artifacts=renderer.artifacts(build))
                self.state.update_job(job_id, phase="review", payload=payload)
            elif phase == "review":
                self.visual_review(job)
            elif phase == "commit":
                self.finalize(job)
            elif phase == "push":
                self.push(job)
            elif phase == "family_output":
                archive = Archive(self.drive(job["learner"]), self.state, self.learner(job["learner"])["output_id"], self.window.require)
                payload["pdf_receipts"] = []
                for pdf in sorted((Path(payload["build"]) / "site/pdf").glob("*.pdf")):
                    payload["pdf_receipts"].append(archive.upload(job_id, archive.root_id, pdf, "application/pdf", f"family-pdf:{job['learner']}:{file_hash(pdf)}", name=f"{pdf.stem}-{file_hash(pdf)[:16]}.pdf"))
                self.state.update_job(job_id, phase="public", payload=payload)
            elif phase == "public":
                # Public is deliberately a separate exact-hash proposal/admin
                # gate. Without a requested manifest, private job can complete.
                if not payload.get("public_manifest"):
                    payload["public_state"] = "not_requested"
                    self.state.update_job(job_id, "complete", "done", payload)
                    return
                return self.public(job)
            elif phase == "done":
                self.state.update_job(job_id, "complete")
                return
            else:
                raise Blocked(f"unsupported retained phase: {phase}")
            if self.state.job(job_id)["state"] != "running":
                return

    def candidate(self, job):
        settings = self.learner(job["learner"])
        git = Git(settings["repo"], self.lock)
        base = git.inspect(fetch=settings.get("fetch", True))
        payload = job["payload"]
        ack=self.state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))
        if not ack or base!=ack[0]['ack_sha']:
            self.state.update_job(job['id'],'ack_wait',error='new HEAD is not acknowledged; observe/review external range before candidate')
            return
        try:
            existing_manifest = json.loads((Path(settings['repo']) / settings.get('pilot_manifest', 'publication/pilot.json')).read_text())
            manifest_with_hashes(settings['repo'], existing_manifest)
        except (Blocked, OSError, ValueError) as error:
            raise Blocked('existing private manifest requires owner maintenance before candidate: '+str(error)) from None
        directory = self.job_dir(job)
        if "base" in payload and payload["base"] != base:
            raise Blocked("remote changed since candidate start; explicit rebase/review reconciliation required")
        disk_gate(directory, max(git.estimate(), self.config.get("worktree_estimate_bytes", 0)), self.config.get("reserve_bytes", 4 * 1024**3))
        candidate = git.worktree(directory / payload.get("worktree_name", "worktree"), base, payload.get("git_identity"))
        payload.update(base=base, worktree=str(candidate.repo), git_identity=candidate.identity)
        self.state.update_job(job["id"], payload=payload)
        approved=payload.get('approved_subject_config')
        approved_paths={}
        if approved:
            if approved['base']!=base:
                raise Blocked('new-subject configuration approval base changed')
            for name,value in approved['files'].items():
                target=candidate.repo/name
                target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
                approved_paths[name]=file_hash(target)
        payload['supervisor_config_paths']=approved_paths
        source_inputs = []
        for f in payload["manifest"]["files"]:
            source = Path(f["read_source"])
            sha = f.get("prepared_sha256", f["sha256"])
            if file_hash(source) != sha:
                raise Blocked("read source changed after classification")
            slug = payload["manifest"]["input_context"]["subject_slug"]
            relative = Path("sources") / f"{job['created'][:10]}-{slug}-package-{job['package_id']}" / sha[:16] / safe_relative(f["path"])
            target = candidate.repo / relative
            for existing in (candidate.repo / "sources").rglob("*"):
                if existing.is_file() and not existing.is_symlink() and existing.stat().st_size == source.stat().st_size and file_hash(existing) == sha:
                    target = existing
                    break
            if target.is_symlink() or not target.resolve().is_relative_to(candidate.repo):raise Blocked('Git source target escapes candidate')
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and file_hash(target) != sha:
                raise CandidateViolation("agent changed supervisor-bound immutable Git source path")
            if not target.exists():
                shutil.copyfile(source, target)
                os.chmod(target, 0o600)
            source_inputs.append({"path": str(target), "sha256": sha, "kind": "source", "id": f["id"]})
            payload['git_sources']=source_inputs
            self.state.update_job(job['id'],payload=payload)
            candidate.source_policy(str(target.relative_to(candidate.repo)))
            if candidate.source_is_ignored(str(target.relative_to(candidate.repo))):
                raise Blocked('ignored source cannot enter private Git; owner must maintain ignore policy and rebase candidate: '+str(target.relative_to(candidate.repo)))
        payload["git_sources"] = source_inputs
        answers = self.state.rows("SELECT id,answer,origin,answer_hash FROM questions WHERE job_id=? AND kind='content' AND state='answered'", (job["id"],))
        previous = payload.get("previous")
        previous_context = previous.get("source_context") if previous else None
        context = payload["manifest"].get("source_context")
        policies=self.trusted_policy(candidate.repo)
        all_inputs = source_inputs + [page for f in payload["manifest"]["files"] for page in f.get("source_pages", [])]
        existing_changes=candidate.changes(base,approved_paths,source_inputs)
        if payload.get('owner_policy_failure'):
            payload.setdefault('owner_policy_recoveries',[]).append({'failure':payload.pop('owner_policy_failure'),'base':base,'sources':source_inputs,'origin':'supervisor-verified-source-and-candidate-guards'})
            self.state.update_job(job['id'],payload=payload)
        envelope = self.envelope(job, "candidate", all_inputs, kind=job["kind"], attempt_phase="candidate:"+digest({"fix_round":payload.get("fix_round",0),"rebase_round":len(payload.get("candidate_history",[]))})[:16], trusted_policy=policies, context=context, previous_context=previous_context,
                                 context_diff={"old": previous_context, "new": context}, answers=answers, metadata=payload["manifest"]["metadata_hash"],
                                 fix_round=payload.get("fix_round", 0), findings=payload.get("findings"), cumulative_base=base,
                                 cumulative_existing_changes=existing_changes, reconciliation=payload.get('reconciled_from'))
        try:
            result, path = self.agents.call(job, "candidate", envelope, candidate.repo, directory,
                                           "Automatic startup instructions are disabled. Read supervisor-bound trusted-policy AGENTS/PROFILE/instructions files and apply the applicable learner rules within this finite role, without delegation or admin actions. Update EXISTING subject notes, Source summary, evidence, indexes and wiki/log.md. Metadata_update is a context/provenance correction, never a second lesson or original byte copy. Only wiki/, docs/review/, docs/evidence/ may change. sources/ acquisition is supervisor-only; never create, edit, delete or rename anything there; never delete, rename or symlink files, never write outside these paths, and never change .gitignore/.gitattributes. Write text with LF line endings. Preserve supplied source bytes. Propose ordered private manifest from existing pilot config. New subjects require admin approval; existing banners required. Supervisor already filed immutable sources at YYYY-MM-DD-title paths; never move/re-file them. file_changes MUST list the cumulative current agent diff against cumulative_base, including earlier fix rounds. No Git finalization.")
        except InvalidManifestProposal as error:
            payload.update(agent_manifest_proposal=error.raw,candidate_result=error.result_path,
                           invalid_manifest_attempt={'attempt_id':error.attempt_id,'path':error.result_path,'sha256':error.result_hash,'error':str(error),'status':error.status,'uncertainties':error.uncertainties})
            self.state.update_job(job['id'],payload=payload)
            raise CandidateViolation('invalid agent manifest proposal: '+str(error)+'; inspect-job '+str(job['id'])+' then rebase-candidate '+str(job['id'])) from None
        if result["status"] != "complete" or result["uncertainties"]:
            question = self.state.question(job["id"], "content", "candidate", "; ".join(result["uncertainties"]) or "Candidate could not complete; inspect its retained result")
            self.state.update_job(job["id"], "question_wait", payload=payload, error=f"question {question}")
            return
        changes = candidate.changes(base,approved_paths,source_inputs)
        if any(file_hash(candidate.repo/name)!=sha for name,sha in approved_paths.items()):
            raise Blocked('agent changed approved supervisor configuration')
        declared = {f["path"]: f["sha256"] for f in result["file_changes"]}
        agent_changes = {name: sha for name, sha in changes.items() if str(candidate.repo / name) not in {s["path"] for s in source_inputs} and name not in approved_paths}
        if declared != agent_changes:
            raise Blocked("actual agent changes differ from declared file hashes")
        if "wiki/log.md" not in changes or not any(name.startswith("wiki/") and name != "wiki/log.md" for name in changes):
            raise Blocked("candidate lacks learning content or operation log")
        source_summaries = [p for p in (candidate.repo / "wiki").rglob("*.md") if "content_sha256" in p.read_text()]
        for source in source_inputs:
            if not any(source["sha256"] in p.read_text() for p in source_summaries):
                raise Blocked("Source summary lacks the exact read-source content_sha256")
        # Every new top-level wiki directory needs an explicit admin operation.
        old_dirs = {p.name for p in (Path(settings["repo"]) / "wiki").iterdir() if p.is_dir()}
        new_dirs = {Path(name).parts[1] for name in changes if name.startswith("wiki/") and len(Path(name).parts) > 2 and Path(name).parts[1] not in ("assets",)} - old_dirs
        if new_dirs and not (approved and new_dirs <= set(approved['subjects'])):
            payload['new_subjects']=sorted(new_dirs)
            self.state.question(job["id"], "authorization", "new-subject", f"New subject configuration required: {', '.join(sorted(new_dirs))}", digest(sorted(new_dirs)))
            self.state.update_job(job["id"], "approval_wait", phase='candidate', payload=payload, error="new subject requires supervisor/admin configuration; no agent tools writes")
            return
        payload.update(agent_manifest_proposal=result['manifest_proposal'],candidate_result=str(path))
        self.state.update_job(job['id'],payload=payload)
        proposal = agent_manifest(candidate.repo,existing_manifest,result['manifest_proposal'])
        manifest_diff = self.job_dir(job) / "review-inputs" / f"manifest-{payload.get('fix_round',0)}.json"
        atomic_json(manifest_diff, {"before": existing_manifest, "after": proposal})
        payload["manifest_review_input"] = {"path": str(manifest_diff), "sha256": file_hash(manifest_diff), "kind": "manifest-diff"}
        if proposal.get("mode") != "private-preview":
            raise Blocked("ingest may propose only private preview configuration")
        payload.update(changes=changes, manifest_proposal=proposal, candidate_result=str(path))
        scan([candidate.repo / name for name in changes] + [path], self.config.get("max_new_bytes", 128 * 1024**2), self.config.get("max_repo_bytes", 1024**3), candidate.repo)
        self.state.update_job(job["id"], phase="source_review", payload=payload)

    def review_inputs(self, job, visual=False):
        payload = job["payload"]
        result = []
        source_pages={f['id']:f.get('source_pages',[]) for f in payload['manifest']['files']}
        for source in payload['git_sources']:
            if source_pages.get(source['id']):
                bound=self.job_dir(job)/'review-inputs'/f"source-{digest(source['id'])[:16]}.json"
                atomic_json(bound,{'source_id':source['id'],'content_sha256':source['sha256'],'pages':source_pages[source['id']]})
                result.append({'path':str(bound),'sha256':file_hash(bound),'kind':'source-index'})
            else:
                result.append(source)
        result.append(payload["manifest_review_input"])
        result.extend(page for f in payload["manifest"]["files"] for page in f.get("source_pages", []))
        result.extend({"path": str(Path(payload["worktree"]) / name), "sha256": sha, "kind": "candidate"} for name, sha in payload["changes"].items() if not name.startswith("sources/"))
        result.append({"path": payload["candidate_result"], "sha256": file_hash(payload["candidate_result"]), "kind": "agent-result"})
        if visual:
            result.extend(payload["pdf_images"])
            result.extend(self.render_review_inputs(job))
        return result

    @staticmethod
    def trusted_policy(repo):
        repo=Path(repo).resolve()
        paths=[repo/name for name in ('AGENTS.md','PROFILE.md') if (repo/name).is_file()]
        paths+=sorted((repo/'instructions').rglob('*.md'))
        result=[]
        for path in paths:
            if path.is_symlink() or not path.resolve().is_relative_to(repo):
                raise Blocked('trusted learner policy path escapes candidate')
            result.append({'path':str(path),'sha256':file_hash(path),'logical_path':str(path.relative_to(repo)),'kind':'trusted-policy'})
        return result

    def render_review_inputs(self,job):
        payload=job['payload']; build=Path(payload['build']); inputs=[]
        source=build/'payload.json'
        if source.is_file():
            document=json.loads(source.read_text())
            if not isinstance(document,dict):
                raise Blocked('renderer payload must be typed object')
            if not isinstance(document.get('pages'),list) or not document['pages'] or any(not isinstance(page,dict) or not isinstance(page.get('route'),str) or not isinstance(page.get('html'),str) for page in document['pages']) or len({p['route'] for p in document['pages']})!=len(document['pages']):
                raise Blocked('renderer payload lacks distinct typed page bodies')
            directory=private_dir(self.job_dir(job)/'render-review-inputs')
            # Exported per-page body/route/headings, never the aggregate with
            # duplicated collection chapters. Accepted unchanged pages can be
            # reused only by exact rendered bytes and route identity.
            for page in document.get('pages',[]):
                path=directory/('page-'+digest(page.get('route'))[:24]+'.json')
                atomic_json(path,page)
                inputs.append({'path':str(path),'sha256':file_hash(path),'kind':'render-page','page_key':page.get('route')})
            # Navigation is separately bounded; preserve order with explicit
            # offsets and a shared topology hash, without copied page bodies.
            pages=[{k:v for k,v in page.items() if k not in ('html','headings')} for page in document['pages']]
            collections=[{k:v for k,v in collection.items() if k!='chapters'} for collection in document.get('collections',[])]
            global_fields={k:document.get(k) for k in ('base','title','mode','license','branding')}
            topology_hash=digest({'global':global_fields,'pages':pages,'collections':collections})
            for kind,items in (('pages',pages),('collections',collections)):
                for offset in range(0,max(1,len(items)),24):
                    path=directory/f'navigation-{kind}-{offset}.json'
                    atomic_json(path,{'global':global_fields,'topology_sha256':topology_hash,'kind':kind,'offset':offset,'total':len(items),'items':items[offset:offset+24]})
                    inputs.append({'path':str(path),'sha256':file_hash(path),'kind':'render-navigation'})
        else:
            # Renderer test/legacy adapters without typed payload receive their
            # actual HTML. No absence is treated as previously reviewed.
            inputs.extend({'path':str(build/name),'sha256':sha,'kind':'artifact'} for name,sha in payload['artifacts'].items() if name.endswith('.html') and not name.startswith('public/'))
        inputs.extend({'path':str(build/name),'sha256':sha,'kind':'render-asset','page_key':name} for name,sha in payload['artifacts'].items() if name.endswith('.svg') and not name.startswith('public/'))
        return inputs

    def content_review(self, job):
        payload = job["payload"]
        paths = self.bounded_review(job, "source_review", self.review_inputs(job), "content", require_visual=False,
                                    instructions="Review bidirectional source coverage, transcription, ordering, provenance, curriculum, formulae, privacy, and exact old/new manifest ordering. No edits.")
        if paths is None:
            return
        payload["source_review"] = paths[0]
        payload["source_review_paths"] = paths
        payload["private_manifest"] = manifest_with_hashes(payload["worktree"], payload["manifest_proposal"])
        self.state.update_job(job["id"], phase="render", payload=payload)

    def visual_review(self, job):
        payload = job["payload"]
        paths = self.bounded_review(job, "review", self.review_inputs(job, True), "content,visual,all_pdf_pages",
                                    instructions="Review exact rendered content, figures, every designated PDF page, ordering, answers, formulae and privacy. No edits.", reuse_visual=True)
        if paths is None:
            return
        payload["visual_review"] = paths[0]
        payload["visual_review_paths"] = paths
        self.state.update_job(job["id"], phase="commit", payload=payload)

    @staticmethod
    def review_identity(item):
        return digest({"sha256": item["sha256"], "kind": item["kind"], "page_key": item.get("page_key")})

    def bounded_review(self, job, phase, inputs, scope, *, require_visual=True, require_public=False, instructions="", reuse_visual=False):
        # Every reused item must appear in an accepted, unchanged exact-hash
        # review closure. Unreviewed baseline PDFs are ALWAYS sent in chunks.
        inputs = list({i["path"]: i for i in inputs}.values())
        for item in inputs:
            if file_hash(item["path"]) != item["sha256"]:
                raise Blocked("review evidence changed")
        policy_repo=job['payload'].get('worktree') or job['payload'].get('external_git_identity',{}).get('repo')
        policies=self.trusted_policy(policy_repo) if policy_repo else []
        policy_hash=digest([(p['logical_path'],p['sha256']) for p in policies])
        context=[]
        if phase in ('source_review','external_review','public_review'):
            text_kinds={'source_review':{'candidate'},'external_review':{'external-content','external-dependent','external-source-summary'},'public_review':{'public-source'}}[phase]
            context=[item for item in inputs if item['kind'] in ('manifest-diff','agent-result') or (item['kind'] in text_kinds and Path(item['path']).suffix.lower() in ('.md','.txt','.json','.html','.svg','.yaml','.yml','.toml'))]
        context_hash=digest([{k:v for k,v in i.items() if k!='path'} for i in context])
        all_hash = digest({'task':{'base':job['payload'].get('base'),'fix_round':job['payload'].get('fix_round',0),'rebase_round':len(job['payload'].get('candidate_history',[]))},'comparison_context_hash':context_hash,'inputs':[{k:v for k,v in i.items() if k != "path"} for i in inputs],'policy_hash':policy_hash})
        rows = self.state.rows("SELECT r.*,j.learner FROM reviews r JOIN jobs j ON j.id=r.job_id WHERE r.state='accepted' AND j.learner=? AND (r.scope=? OR (? AND r.scope LIKE '%visual%'))", (job["learner"], scope, bool(reuse_visual and not require_public)))
        covered, paths = set(), []
        context_ids={self.review_identity(item) for item in context}
        for record in rows:
            if not record["closure"] or not Path(record["path"]).is_file() or file_hash(record["path"]) != record["sha256"]:
                continue
            saved = json.loads(record["closure"])
            same_context = record["scope"] == scope and record["job_id"] == job["id"] and saved.get("all_hash") == all_hash
            accepted = [i for i in saved.get("inputs", []) if same_context or (reuse_visual and (not context or saved.get('comparison_context_hash')==context_hash) and saved.get('policy_hash',digest([]))==policy_hash and i.get("kind") in ("pdf-page","render-page","render-asset"))]
            identities = {self.review_identity(i) for i in accepted}
            if same_context and saved.get('comparison_context_hash')==context_hash:
                identities|=context_ids
            if identities & {self.review_identity(i) for i in inputs}:
                covered |= identities
                paths.append(record["path"])
        pending = [i for i in inputs if self.review_identity(i) not in covered and self.review_identity(i) not in context_ids]
        chunks, chunk, size = [], [], 0
        maximum = self.config.get("review_chunk_bytes", 32 * 1024**2)
        count = self.config.get("review_chunk_items", 12)
        if not 1 <= count <= 24 or not 1024 <= maximum <= 64 * 1024**2:
            raise Blocked("invalid finite review chunk limits")
        context_size=sum(Path(i['path']).stat().st_size for i in context)
        if context and (len(context)>64 or context_size>=maximum):
            raise Blocked('complete changed teaching text/manifest/result context exceeds finite source-review bound; use a smaller package or manual closure')
        capacity=maximum-context_size
        for item in pending:
            amount = Path(item["path"]).stat().st_size
            if amount > capacity:
                raise Blocked("single review input exceeds bounded chunk size; render/split through supervisor")
            if chunk and (len(chunk) >= count or size + amount > capacity):
                chunks.append(chunk)
                chunk, size = [], 0
            chunk.append(item)
            size += amount
        if chunk:
            chunks.append(chunk)
        if not chunks and context and not context_ids<=covered:
            chunks.append([])
        for chunk in chunks:
            chunk_phase = phase + ":" + digest({"inputs":[self.review_identity(i) for i in chunk],"all_hash":all_hash})[:16]
            envelope = self.envelope(job, chunk_phase, chunk, all_hash=all_hash, scope=scope, complete_input_count=len(inputs), trusted_policy=policies, comparison_context=context, comparison_context_hash=context_hash)
            result, path = self.agents.call(job, chunk_phase, envelope, self.job_dir(job), self.job_dir(job), instructions + " This is a bounded review chunk; cover every supplied input. Complete-package coverage is closed only by supervisor union of exact accepted chunks. For each source/external/public review, read EVERY comparison_context teaching text/manifest/result together with this source chunk, check the actual transcription against these sources, and add evidence exactly comparison_context_sha256= followed by comparison_context_hash. Context is not separate source coverage.")
            if result["status"] == "changes_requested" and phase in ("review", "source_review"):
                self.fix(job, result)
                return None
            if context and 'comparison_context_sha256='+context_hash not in result['evidence']:
                raise Blocked('source review lacks exact source/teaching comparison-context evidence binding')
            if any(file_hash(i['path'])!=i['sha256'] for i in context):
                raise Blocked('changed teaching comparison context mutated during review')
            review_gate(result, envelope, require_visual=require_visual, require_public=require_public)
            self.save_review(job, path, envelope, scope, {"all_hash": all_hash, "inputs": chunk, "policy_hash":policy_hash,"comparison_context_hash":context_hash,"comparison_context":context})
            paths.append(str(path))
            covered |= {self.review_identity(i) for i in chunk} | context_ids
        if not paths or not {self.review_identity(i) for i in inputs} <= covered:
            raise Blocked("complete review union missing")
        return sorted(set(paths))

    def save_review(self, job, path, envelope, scope, closure=None):
        with self.state.db:
            self.state.db.execute("INSERT INTO reviews(job_id,path,sha256,inputs_hash,scope,state,closure) VALUES (?,?,?,?,?,'accepted',?)", (job["id"], str(path), file_hash(path), digest(envelope), scope, json.dumps(closure) if closure else None))

    def fix(self, job, result):
        payload = job["payload"]
        round_no = payload.get("fix_round", 0) + 1
        if round_no > 2:
            self.state.update_job(job["id"], "review_wait", error="two content fix rounds exhausted; manual review required")
            return
        payload.update(fix_round=round_no, findings=result)
        with self.state.db:
            self.state.db.execute("UPDATE reviews SET state='invalidated' WHERE job_id=?", (job["id"],))
        self.state.update_job(job["id"], phase="candidate", payload=payload)

    def finalize(self, job):
        payload = job["payload"]
        self.stable(job)
        main = Git(self.learner(job["learner"])["repo"], self.lock)
        if main.inspect(fetch=True) != payload["base"]:
            raise Blocked("remote/main moved after review: review invalidated until reconciliation")
        ack=self.state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
        if ack!=payload['base']:raise Blocked('commit base is no longer acknowledged; reconcile candidate before finalization')
        candidate = Git(payload["worktree"], self.lock, payload.get("git_identity"))
        if Renderer.artifacts(payload["build"]) != payload["artifacts"]:
            raise Blocked("rendered artifacts changed after visual review")
        open_questions = self.state.rows("SELECT id FROM questions WHERE job_id=? AND state IN ('open','reconcile_wait') AND kind='content'", (job["id"],))
        if open_questions:
            raise Blocked("unresolved content/privacy question globally blocks commit")
        paths = sorted(set(payload.get("source_review_paths", [payload["source_review"]]) + payload.get("visual_review_paths", [payload["visual_review"]]) + [payload["candidate_result"]]))
        for review in self.state.rows("SELECT * FROM reviews WHERE job_id=? AND state='accepted'", (job["id"],)):
            if file_hash(review["path"]) != review["sha256"]:
                raise Blocked("accepted review bytes changed")
        scan([candidate.repo / n for n in payload["changes"]] + paths, self.config.get("max_new_bytes", 128 * 1024**2), self.config.get("max_repo_bytes", 1024**3), candidate.repo)
        # Commit candidate first; a crash after commit is recovered by exact
        # retained HEAD/content verification rather than a duplicate commit.
        manifest_path = self.learner(job["learner"]).get("pilot_manifest", "publication/pilot.json")
        tree_hash = digest({"base": payload["base"], "changes": payload["changes"], "manifest": payload["private_manifest"], "reviews": {p: file_hash(p) for p in paths}})
        effect = self.state.effect(job["id"], "git-commit", str(candidate.repo), tree_hash, f"private-commit:{job['id']}:{tree_hash}")
        def execute(e):
            commit = candidate.commit(job, payload["changes"], paths, self.config["git_identity"], manifest_path, payload["private_manifest"])
            return {"verified": True, "external_id": commit, "commit": commit}
        receipt = self.state.perform_effect(effect, execute, lambda e: candidate.reconcile_commit(e, job, payload["changes"], paths, manifest_path, payload["private_manifest"]))
        payload["commit"] = receipt["commit"]
        self.state.update_job(job["id"], phase="push", payload=payload)

    def push(self, job):
        payload = job["payload"]
        main = Git(self.learner(job["learner"])["repo"], self.lock)
        effect = self.state.effect(job["id"], "git-push", self.learner(job["learner"])["repo"] + ":main", payload["commit"], f"private-push:{job['learner']}:{payload['commit']}")
        candidate=None
        def preflight():
            nonlocal candidate
            main.clean()
            if main.head()!=main.git("rev-parse","refs/remotes/origin/main"):
                raise Blocked("unpushed/diverged owner commit; reconcile owner Git before candidate push")
            ack=self.state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
            if ack!=payload['base']:raise Blocked('candidate push base is no longer acknowledged; rebase-candidate after absence reconciliation')
            self.stable(job)
            main.git("fetch", "--no-tags", "origin", "main")
            if main.git("rev-parse", "refs/remotes/origin/main")!=payload['base']:
                raise Blocked('remote changed before push; no force push, reconcile/rebase candidate')
            candidate=Git(payload['worktree'],self.lock,payload.get('git_identity'))
            if candidate.head()!=payload['commit']:raise Blocked('candidate commit changed before push')
        def execute(e):
            candidate.git('push','origin','HEAD:refs/heads/main')
            return main.push_reconcile(e)
        payload['push_receipt']=self.state.perform_effect(effect,execute,main.push_reconcile,preflight)
        try:
            main.clean()
            if main.head()!=payload['base']:raise Blocked('interactive checkout moved')
            main.git('merge','--ff-only',payload['commit'])
            payload['local_sync']='verified'
        except Blocked:
            payload['local_sync']='blocked_after_verified_push'
        ack=self.state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
        if ack==payload['base']:
            with self.state.db:self.state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=?,state='complete' WHERE id=?",(payload['commit'],payload['commit'],f"baseline:{job['learner']}"))
        elif ack!=payload['commit'] and payload['commit'] not in main.git('rev-list',ack).splitlines():raise Blocked('verified push cannot skip or regress current Git acknowledgement')
        self.state.wake_ack_waiters(job['learner'])
        self.state.update_job(job['id'],phase='family_output',payload=payload)

    def external_review(self, job):
        settings = self.learner(job["learner"])
        git = Git(settings["repo"], self.lock)
        if git.inspect(fetch=True) != job["payload"]["head"]:
            raise Blocked("external review head changed; reconcile range first")
        changes = job["payload"]["changes"]
        if any(sha is None for sha in changes.values()):
            raise Blocked("external deletion requires manual evidence reconciliation")
        if any(not name.startswith(("wiki/", "sources/", "docs/")) for name in changes):
            raise Blocked("external configuration/policy diff requires explicit maintenance review")
        disk_gate(self.job_dir(job), max(git.estimate(), self.config.get("worktree_estimate_bytes", 0)), self.config.get("reserve_bytes", 4 * 1024**3))
        candidate = git.worktree(self.job_dir(job) / "external-worktree", job["payload"]["head"], job["payload"].get("external_git_identity"))
        job["payload"]["external_git_identity"]=candidate.identity
        self.state.update_job(job["id"],payload=job["payload"])
        candidate.clean()
        if candidate.head() != job["payload"]["head"]:
            raise Blocked("external review worktree head differs")
        inputs = [{"path": str(candidate.repo / n), "sha256": sha, "kind": "external-content"} for n, sha in changes.items()]
        # Never promote fresh hashes before review. Render a job-private
        # proposed manifest to supply full PDF evidence for closure.
        manifest = manifest_with_hashes(candidate.repo, json.loads((candidate.repo / settings.get("pilot_manifest", "publication/pilot.json")).read_text()))
        affected_dirs = {str(Path(name).parent) for name in changes if name.startswith("wiki/")}
        for item in manifest["pages"] + manifest.get("assets", []):
            if str(Path(item["path"]).parent) not in affected_dirs and item["path"] not in changes:
                continue
            inputs.append({"path": str(candidate.repo / item["path"]), "sha256": item["sha256"], "kind": "external-dependent"})
        # Follow affected pages' explicit Source-summary resources, rather
        # than demanding every historical image in their entire subject.
        required_hashes=set()
        pending=[candidate.repo/name for name in changes if name.startswith('wiki/') and name.endswith('.md')]
        visited=set()
        while pending:
            page=pending.pop()
            if page in visited:
                continue
            visited.add(page)
            text=page.read_text()
            if len(text)>1024*1024:
                raise Blocked('external text evidence exceeds finite source navigation limit')
            inputs.append({'path':str(page),'sha256':file_hash(page),'kind':'external-source-summary'})
            block=re.search(r'(?m)^content_sha256:\s*([^\n]*(?:\n[ \t]+[^\n]*)*)',text)
            if block:
                required_hashes.update(re.findall(r'\b[a-f0-9]{64}\b',block.group(1)))
            for resource in re.findall(r'resource:\s*[\"\']?([^,\s}\"\']+)',text):
                if not resource.endswith('.md'):
                    continue
                target=(page.parent/resource).resolve()
                if target.is_relative_to((candidate.repo/'wiki').resolve()):
                    if target.is_symlink() or not target.is_file():
                        raise Blocked('affected Source summary unavailable')
                    pending.append(target)
        found_hashes=set()
        source_bytes=0
        stage=private_dir(self.job_dir(job)/'external-inputs')
        for root in (candidate.repo/'sources',Path(settings['repo'])/'sources'):
            for source in root.rglob('*'):
                if not source.is_file() or source.is_symlink():
                    continue
                sha=file_hash(source)
                if sha not in required_hashes or sha in found_hashes:
                    continue
                source_bytes+=source.stat().st_size
                if source_bytes>self.config.get('max_external_source_bytes',128*1024**2):
                    raise Blocked('affected external sources exceed finite evidence bound')
                target=stage/(sha+source.suffix.lower())
                if target.exists() and file_hash(target)!=sha:
                    raise Blocked('retained external source evidence changed')
                if not target.exists():
                    disk_gate(stage,source.stat().st_size,self.config.get('reserve_bytes',4*1024**3))
                    shutil.copyfile(source,target)
                    os.chmod(target,0o400)
                found_hashes.add(sha)
                if target.suffix.lower()=='.pdf':
                    pages_dir=private_dir(stage/(sha+'-pages'))
                    receipt=pages_dir/'complete.json'
                    if receipt.exists():
                        pages=json.loads(receipt.read_text())['images']
                        if any(file_hash(i['path'])!=i['sha256'] for i in pages):
                            raise Blocked('external PDF source images changed')
                    else:
                        output=run([self.config['renderer']['pdfinfo'],str(target)],stage,lock=self.lock)
                        match=re.search(r'Pages:\s+(\d+)',output)
                        if not match or int(match[1])<1:
                            raise Blocked('external source PDF lacks verified page count')
                        count=int(match[1])
                        render_dir=None
                        for attempt in range(3+job['payload'].get('external_render_extra',0)):
                            trial=private_dir(pages_dir/str(attempt))
                            if not list(trial.glob('page-*.png')):
                                render_dir=trial
                                break
                        if render_dir is None:
                            raise Blocked('external source PDF partial attempts retained; retry-render external required')
                        disk_gate(render_dir,count*3*1024**2,self.config.get('reserve_bytes',4*1024**3))
                        run([self.config['renderer']['pdftoppm'],'-scale-to','1800','-png',str(target),str(render_dir/'page')],render_dir,timeout=300,lock=self.lock)
                        images=sorted(render_dir.glob('page-*.png'),key=lambda p:int(p.stem.rsplit('-',1)[1]))
                        if len(images)!=count:
                            raise Blocked('external PDF source page coverage incomplete')
                        pages=[{'path':str(p),'sha256':file_hash(p),'kind':'source-pdf-page','id':f'{sha}:page:{i}'} for i,p in enumerate(images,1)]
                        atomic_json(receipt,{'source_sha256':sha,'images':pages})
                    source_index=stage/(sha+'-index.json')
                    atomic_json(source_index,{'content_sha256':sha,'pages':pages})
                    inputs.append({'path':str(source_index),'sha256':file_hash(source_index),'kind':'source-index'})
                    inputs.extend(pages)
                else:
                    inputs.append({'path':str(target),'sha256':sha,'kind':'external-source'})
        if found_hashes!=required_hashes:
            raise Blocked('affected external source bytes missing; retain job and supply exact-hash evidence in private checkout sources')
        manifest_record=self.job_dir(job)/'external-manifest-proposal.json'
        atomic_json(manifest_record,{'before':json.loads((candidate.repo/settings.get('pilot_manifest','publication/pilot.json')).read_text()),'after':manifest})
        inputs.append({'path':str(manifest_record),'sha256':file_hash(manifest_record),'kind':'manifest-diff'})
        inputs = list({item["path"]: item for item in inputs}.values())
        renderer = Renderer(self.config["renderer"], self.lock, self.window)
        render_dir=self.job_dir(job)/f"external-render-{job['payload'].get('external_render_attempt',0)}"
        if (render_dir/'build').exists() and not (render_dir/'complete.json').exists():
            attempt=job['payload'].get('external_render_attempt',0)+1
            if attempt>=3+job['payload'].get('external_render_extra',0):
                raise Blocked('external partial render limit; retry-render external required')
            job['payload']['external_render_attempt']=attempt
            self.state.update_job(job['id'],payload=job['payload'])
            render_dir=self.job_dir(job)/f'external-render-{attempt}'
        build, images = renderer.build(candidate.repo, manifest, render_dir)
        inputs += images
        paths = self.bounded_review(job, "external_review", inputs, "external-content,visual", reuse_visual=True,
                                    instructions="Review unacknowledged external range and affected source summaries, sources, figures and designated rendered PDF pages. No edits; missing source means blocked.")
        job["payload"]["external_manifest"] = manifest
        job["payload"]["external_review_envelope"] = self.envelope(job, "external_review", inputs, base=job["payload"]["base"], head=job["payload"]["head"])
        job["payload"]["external_artifacts"] = renderer.artifacts(build)
        job["payload"]["external_build"] = str(build)
        self.state.update_job(job["id"], payload=job["payload"])
        self.state.update_job(job["id"], "review_wait", error="review accepted for exact retained range; finalize-external only while current ack/remote permit it; otherwise inspect current range and use direct-owner close-job after exact obsolete-range assessment/effect reconciliation")

    def public(self, job):
        from .publication import publish
        return publish(self, job)

    def status(self):
        from .session import diagnostics
        return {**diagnostics(self.config),"generated": now(), "report_error": self.state.meta("report-failure") or None, "observations": self.state.rows("SELECT id,learner,kind,state,observed_sha,ack_sha,created FROM observations WHERE id LIKE 'baseline:%' OR id IN (SELECT id FROM observations WHERE id NOT LIKE 'baseline:%' ORDER BY created DESC,rowid DESC LIMIT 20) ORDER BY created DESC"),
                "packages": self.state.rows("SELECT id,learner,source_id,current_seq,state FROM packages ORDER BY id"),
                "jobs": self.state.rows("SELECT id,learner,kind,state,phase,error,updated FROM jobs ORDER BY id"),
                "effects": self.state.rows("SELECT e.stable_key,e.kind,e.target,e.state,e.artifact_hash,e.external_id,e.job_id,j.learner FROM effects e LEFT JOIN jobs j ON j.id=e.job_id ORDER BY e.updated"),
                "questions": self.state.rows("SELECT id,job_id,kind,scope,manifest_hash,prompt,state FROM questions q WHERE state IN ('open','reconcile_wait') OR (state='stale' AND NOT EXISTS (SELECT 1 FROM jobs old JOIN packages p ON p.id=old.package_id JOIN jobs current ON current.package_id=p.id AND current.revision_seq=p.current_seq WHERE old.id=q.job_id AND current.kind IN ('ingest','metadata_update') AND current.state IN ('complete','closed_unprocessed','rejected'))) ORDER BY id")}
