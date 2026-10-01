"""Versioned SQLite state. No constructor or normal run ever creates a database."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

from .common import PreconditionFailed, Blocked, EffectPending, canonical, digest, now, private_dir

SCHEMA_VERSION = 1
SCHEMA = """
PRAGMA user_version=1;
CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE observations(id TEXT PRIMARY KEY, learner TEXT NOT NULL, kind TEXT NOT NULL,
 state TEXT NOT NULL, manifest TEXT, observed_sha TEXT, ack_sha TEXT, created TEXT NOT NULL);
CREATE TABLE packages(id INTEGER PRIMARY KEY, learner TEXT NOT NULL, source_id TEXT NOT NULL,
 state TEXT NOT NULL, current_seq INTEGER NOT NULL DEFAULT 0, UNIQUE(learner,source_id));
CREATE TABLE revisions(id INTEGER PRIMARY KEY, package_id INTEGER NOT NULL REFERENCES packages(id),
 seq INTEGER NOT NULL, bytes_hash TEXT NOT NULL, metadata_hash TEXT NOT NULL, manifest TEXT NOT NULL,
 created TEXT NOT NULL, UNIQUE(package_id,seq));
CREATE TABLE jobs(id INTEGER PRIMARY KEY, stable_key TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
 package_id INTEGER REFERENCES packages(id), revision_seq INTEGER, learner TEXT NOT NULL,
 state TEXT NOT NULL, phase TEXT NOT NULL DEFAULT 'capture', payload TEXT NOT NULL,
 error TEXT, created TEXT NOT NULL, updated TEXT NOT NULL);
CREATE UNIQUE INDEX one_running_package ON jobs(package_id) WHERE state='running';
CREATE TABLE attempts(id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
 number INTEGER NOT NULL, phase TEXT NOT NULL, model TEXT NOT NULL, effort TEXT NOT NULL,
 state TEXT NOT NULL, result_hash TEXT, started TEXT NOT NULL, ended TEXT,
 UNIQUE(job_id,number));
CREATE TABLE reviews(id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
 path TEXT NOT NULL, sha256 TEXT NOT NULL, inputs_hash TEXT NOT NULL, scope TEXT NOT NULL,
 state TEXT NOT NULL, closure TEXT);
CREATE TABLE effects(stable_key TEXT PRIMARY KEY, job_id INTEGER REFERENCES jobs(id),
 kind TEXT NOT NULL, target TEXT NOT NULL, artifact_hash TEXT NOT NULL,
 state TEXT NOT NULL, external_id TEXT, receipt TEXT, updated TEXT NOT NULL);
CREATE TABLE questions(id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs(id),
 revision_seq INTEGER, kind TEXT NOT NULL CHECK(kind IN ('content','authorization')),
 scope TEXT NOT NULL, manifest_hash TEXT, prompt TEXT NOT NULL, state TEXT NOT NULL,
 answer TEXT, origin TEXT, answer_hash TEXT, created TEXT NOT NULL);
"""


class State:
    @classmethod
    def initialize(cls, path, baselines):
        path = Path(path)
        private_dir(path.parent)
        # Exclusive creation protects existing DBs, including corrupt ones.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        db = sqlite3.connect(path)
        try:
            db.executescript(SCHEMA)
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            with db:
                db.execute("INSERT INTO meta VALUES ('initialized',?)", (now(),))
                for learner, info in baselines.items():
                    sha = info["observed_sha"]
                    ack = info.get("ack_sha")
                    if ack and not info.get("closure_evidence"):
                        raise Blocked("baseline acknowledgement requires closure evidence")
                    db.execute('INSERT INTO meta VALUES (?,?)',(f'baseline-initial:{learner}',sha))
                    db.execute("INSERT INTO observations VALUES (?,?, 'git',?, ?,?,?,?)",
                               (f"baseline:{learner}", learner, "complete" if ack else "baseline_pending",
                                canonical(info).decode(), sha, ack, now()))
        except Exception:
            # Preserve even failed initialization for explicit recovery.
            db.close()
            raise
        db.close()
        return cls(path)

    def __init__(self, path, *, readonly=False):
        path = Path(path)
        if not path.is_file() or path.is_symlink():
            raise Blocked("state database missing: explicit init or recovery required")
        try:
            self.db = sqlite3.connect(f"file:{path}?mode={'ro' if readonly else 'rw'}", uri=True)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA foreign_keys=ON")
            if readonly:self.db.execute("PRAGMA query_only=ON")
            else:self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA busy_timeout=5000")
            if self.db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise Blocked("unsupported schema version: explicit migration required")
            if self.db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise Blocked("state database failed integrity check: recovery required")
        except sqlite3.DatabaseError:
            raise Blocked("corrupt state database: recovery required") from None

    def close(self):
        self.db.close()

    def rows(self, query, args=()):
        return [dict(r) for r in self.db.execute(query, args)]

    def job(self, job_id):
        rows = self.rows("SELECT * FROM jobs WHERE id=?", (job_id,))
        if not rows:
            raise Blocked("unknown job")
        result = rows[0]
        result["payload"] = json.loads(result["payload"])
        return result

    def update_job(self, job_id, state=None, phase=None, payload=None, error=None):
        job = self.job(job_id)
        effective_payload=payload if payload is not None else job['payload']
        if state in ('queued','running') and effective_payload.get('quota_block'):
            state='retry_wait';error='provider quota block: clear-quota requires verified reset/direct-admin evidence'
        with self.db:
            self.db.execute("UPDATE jobs SET state=?,phase=?,payload=?,error=?,updated=? WHERE id=?",
                            (state or job["state"], phase or job["phase"], canonical(payload if payload is not None else job["payload"]).decode(), error, now(), job_id))

    def observation(self, observation_id, learner, manifest=None, state="staging"):
        with self.db:
            self.db.execute("INSERT INTO observations VALUES (?,?,'drive',?,?,NULL,NULL,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,manifest=excluded.manifest",
                            (observation_id, learner, state, canonical(manifest).decode(), now()))
            if state == 'complete':
                # Keep the newest complete inventory and bounded audit summaries;
                # source revisions/captures/reviews and the baseline are retained.
                old = self.db.execute("SELECT id,manifest FROM observations WHERE learner=? AND kind='drive' AND state='complete' AND id!=?", (learner, observation_id)).fetchall()
                for row in old:
                    value = json.loads(row['manifest'])
                    if not isinstance(value, dict) or 'inventory_sha256' not in value:
                        self.db.execute('UPDATE observations SET manifest=? WHERE id=?', (canonical({'inventory_sha256':digest(value),'retained_as':'summary'}).decode(),row['id']))
                self.db.execute("DELETE FROM observations WHERE learner=? AND kind='drive' AND id NOT IN (SELECT id FROM observations WHERE learner=? AND kind='drive' ORDER BY created DESC,rowid DESC LIMIT 20)", (learner,learner))

    def meta(self, key, value=None):
        if value is None:
            row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
        with self.db:
            self.db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def revision(self, learner, source_id, manifest, *, baseline=False):
        """Compare only to the current revision. A→B→A gets seq 1,2,3."""
        bytes_hash = digest(sorted((f["id"], f["sha256"]) for f in manifest["files"]))
        metadata_hash = manifest["metadata_hash"]
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO packages(learner,source_id,state) VALUES (?,?,?)", (learner, source_id, "baseline_pending" if baseline else "detected"))
            package = self.db.execute("SELECT * FROM packages WHERE learner=? AND source_id=?", (learner, source_id)).fetchone()
            previous = self.db.execute("SELECT * FROM revisions WHERE package_id=? AND seq=?", (package["id"], package["current_seq"])).fetchone()
            if previous and previous["bytes_hash"] == bytes_hash and previous["metadata_hash"] == metadata_hash:
                # Path/name location-only updates do not create another lesson.
                recorded = json.loads(previous["manifest"])
                if "source_context" in recorded:
                    manifest["source_context"] = recorded["source_context"]
                self.db.execute("UPDATE revisions SET manifest=? WHERE id=?", (canonical(manifest).decode(), previous["id"]))
                # A byte-verified complete observation may refresh location and
                # provider-version fields without invalidating accepted content.
                for row in self.db.execute("SELECT id,payload FROM jobs WHERE package_id=? AND revision_seq=? AND state NOT IN ('complete','rejected','reconciled','superseded','closed_unprocessed')", (package['id'], previous['seq'])).fetchall():
                    payload = json.loads(row['payload'])
                    if 'manifest' not in payload:
                        continue
                    old = payload['manifest']
                    refreshed = dict(old, **{k:manifest[k] for k in ('inventory','snapshot_hash') if k in manifest})
                    payload['manifest'] = refreshed
                    self.db.execute('UPDATE jobs SET payload=? WHERE id=?', (canonical(payload).decode(), row['id']))
                return package["id"], previous["seq"], False
            seq = package["current_seq"] + 1
            self.db.execute("INSERT INTO revisions(package_id,seq,bytes_hash,metadata_hash,manifest,created) VALUES (?,?,?,?,?,?)", (package["id"], seq, bytes_hash, metadata_hash, canonical(manifest).decode(), now()))
            self.db.execute("UPDATE packages SET current_seq=? WHERE id=?", (seq, package["id"]))
            self.db.execute("UPDATE jobs SET state='superseded',updated=? WHERE package_id=? AND state IN ('queued','retry_wait','blocked','question_wait','review_wait','approval_wait') AND phase IN ('capture','classify','archive')", (now(), package["id"]))
            self.db.execute("UPDATE questions SET state='stale' WHERE job_id IN (SELECT id FROM jobs WHERE package_id=? AND revision_seq!=?) AND state IN ('open','answered','reconcile_wait')",(package['id'],seq))
            if not baseline and package["state"] not in ("baseline_pending", "rejected"):
                closed = self.db.execute("SELECT r.* FROM revisions r JOIN jobs j ON j.package_id=r.package_id AND j.revision_seq=r.seq WHERE r.package_id=? AND j.state='complete' AND j.kind IN ('ingest','metadata_update','baseline_link') ORDER BY r.seq DESC LIMIT 1", (package["id"],)).fetchone()
                kind = "metadata_update" if closed and closed["bytes_hash"] == bytes_hash else "ingest"
                payload = {"manifest": manifest, "previous": json.loads(closed["manifest"]) if closed else None}
                self.enqueue(kind, learner, f"{kind}:{learner}:{source_id}:{seq}", payload, package["id"], seq, transaction=False)
            return package["id"], seq, True

    def enqueue(self, kind, learner, stable_key, payload, package_id=None, revision_seq=None, transaction=True):
        if not stable_key:
            raise Blocked("job key is required")
        def insert():
            self.db.execute("INSERT OR IGNORE INTO jobs(stable_key,kind,package_id,revision_seq,learner,state,payload,created,updated) VALUES (?,?,?,?,?,'queued',?,?,?)",
                            (stable_key, kind, package_id, revision_seq, learner, canonical(payload).decode(), now(), now()))
            return self.db.execute("SELECT id FROM jobs WHERE stable_key=?", (stable_key,)).fetchone()[0]
        if transaction:
            with self.db:
                return insert()
        return insert()

    def select_baseline(self, learner, source_id):
        package = self.db.execute("SELECT * FROM packages WHERE learner=? AND source_id=?", (learner, source_id)).fetchone()
        if not package or package["state"] != "baseline_pending" or not package["current_seq"]:
            raise Blocked("package is not awaiting baseline selection")
        revision = self.db.execute("SELECT * FROM revisions WHERE package_id=? AND seq=?", (package["id"], package["current_seq"])).fetchone()
        with self.db:
            job_id = self.enqueue("ingest", learner, f"ingest:{learner}:{source_id}:{revision['seq']}", {"manifest": json.loads(revision["manifest"]), "previous": None}, package["id"], revision["seq"], False)
            self.db.execute("UPDATE packages SET state='detected' WHERE id=?", (package["id"],))
        return job_id

    def current(self, job):
        if job["package_id"] is None:
            return True
        return self.db.execute("SELECT current_seq FROM packages WHERE id=?", (job["package_id"],)).fetchone()[0] == job["revision_seq"]

    def question(self, job_id, kind, scope, prompt, manifest_hash=None):
        job = self.job(job_id)
        existing = self.rows("SELECT id FROM questions WHERE job_id=? AND kind=? AND scope=? AND state='open' AND manifest_hash IS ?", (job_id, kind, scope, manifest_hash))
        if existing:
            return existing[0]["id"]
        with self.db:
            cur = self.db.execute("INSERT INTO questions(job_id,revision_seq,kind,scope,manifest_hash,prompt,state,created) VALUES (?,?,?,?,?,?,'open',?)", (job_id, job["revision_seq"], kind, scope, manifest_hash, prompt, now()))
        return cur.lastrowid

    def answer(self, question_id, answer, origin):
        row = self.db.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not row or row["state"] != "open":
            raise Blocked("question is not open")
        if row["kind"] != "content":
            raise Blocked("authorization cannot be answered by source text or model output")
        if origin not in ("admin-content", "drive-txt", "drive-description", "private-git", "owner-session"):
            raise Blocked("unsupported answer origin")
        job = self.job(row["job_id"])
        state = "answered" if self.current(job) else "reconcile_wait"
        with self.db:
            self.db.execute("UPDATE questions SET answer=?,origin=?,answer_hash=?,state=? WHERE id=?", (answer, origin, digest({"answer": answer, "origin": origin}), state, question_id))
        if state == "answered":
            self.update_job(job["id"], "queued")

    def approve(self, job_id, manifest_hash, scope="public"):
        job = self.job(job_id)
        if not self.current(job):
            raise Blocked("stale revision cannot be authorized")
        proposal = job["payload"].get("public_proposal" if scope == "public" else f"{scope}_manifest")
        if proposal is None or digest(proposal) != manifest_hash:
            raise Blocked("approval hash differs from frozen proposal")
        rows = self.rows("SELECT id FROM questions WHERE job_id=? AND kind='authorization' AND scope=? AND manifest_hash=? AND state='open'", (job_id, scope, manifest_hash))
        if len(rows) != 1:
            raise Blocked("no matching authorization question")
        with self.db:
            self.db.execute("UPDATE questions SET state='approved',origin='direct-vm-admin',answer_hash=? WHERE id=?", (manifest_hash, rows[0]["id"]))
        self.update_job(job_id, "queued")

    def effect(self, job_id, kind, target, artifact_hash, key):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO effects VALUES (?,?,?,?,?,'planned',NULL,NULL,?)", (key, job_id, kind, target, artifact_hash, now()))
        effect = self.rows("SELECT * FROM effects WHERE stable_key=?", (key,))[0]
        if (effect["kind"], effect["target"], effect["artifact_hash"]) != (kind, target, artifact_hash):
            raise Blocked("effect key reused for different immutable operation")
        return effect

    def effect_state(self, key, state, receipt=None, external_id=None):
        with self.db:
            self.db.execute("UPDATE effects SET state=?,receipt=COALESCE(?,receipt),external_id=COALESCE(?,external_id),updated=? WHERE stable_key=?", (state, canonical(receipt).decode() if receipt is not None else None, external_id, now(), key))

    def perform_effect(self, effect, execute, reconcile, preflight=None):
        """The reconciler returns verified receipt, definitive absence, or None.

        Only definitive absence authorizes repeating an interrupted operation.
        Reconciliation itself must check frozen target AND exact artifact hash.
        """
        key = effect["stable_key"]
        if effect["state"] == "admin_closed":
            raise Blocked("effect explicitly closed by direct admin; no repetition")
        if effect["state"] == "verified":
            return json.loads(effect["receipt"])
        if effect["state"] in ("inflight", "unknown"):
            receipt = reconcile(effect)
            if receipt is None:
                self.effect_state(key, "unknown")
                raise EffectPending("unknown effect: reconciliation pending; no blind repeat")
            if receipt.get("absent") is not True:
                if receipt.get("verified") is not True:
                    raise EffectPending("reconciliation lacks exact verified receipt")
                self.effect_state(key, "verified", receipt, receipt.get("external_id"))
                return receipt
        # No mutation has begun while these checks run. An interrupted effect
        # reaches this point only after authoritative reconciliation of absence.
        if preflight is not None:
            try:preflight()
            except BaseException:
                self.effect_state(key,'planned')
                raise
        self.effect_state(key, "inflight")
        checking_preflight=False
        try:
            if preflight is not None:
                checking_preflight=True
                preflight()
                checking_preflight=False
            receipt = execute(effect)
            if not receipt or receipt.get("verified") is not True:
                raise EffectPending("effect verification pending; no blind repeat")
            self.effect_state(key, "verified", receipt, receipt.get("external_id"))
            return receipt
        except PreconditionFailed:
            self.effect_state(key,"planned")
            raise
        except BaseException:
            self.effect_state(key, "planned" if checking_preflight else "unknown")
            raise

    def recover(self, *, learners=None):
        """Local crash repair; scoped processing never alters excluded learners."""
        if learners is None:
            clause='';values=()
        else:
            if not learners:return
            clause=' AND job_id IN (SELECT id FROM jobs WHERE learner IN ('+','.join('?' for _ in learners)+'))';values=tuple(learners)
        with self.db:
            self.db.execute("UPDATE effects SET state='unknown',updated=? WHERE state='inflight'"+clause, (now(),*values))
            self.db.execute("UPDATE attempts SET state='interrupted',ended=? WHERE state='running'"+clause, (now(),*values))
            job_clause='' if learners is None else ' AND learner IN ('+','.join('?' for _ in learners)+')'
            self.db.execute("UPDATE jobs SET state='queued',error='interrupted; reconcile retained phase',updated=? WHERE state='running'"+job_clause, (now(),*values))

    def wake_ack_waiters(self, learner):
        with self.db:
            self.db.execute("UPDATE jobs SET state='queued',error=NULL,updated=? WHERE learner=? AND state='ack_wait'", (now(), learner))

    def admin_resume(self, job_id):
        job = self.job(job_id)
        if not self.current(job):
            raise Blocked("stale candidate: use reconcile-job to select the current revision")
        if self.rows("SELECT id FROM questions WHERE job_id=? AND state IN ('open','reconcile_wait')", (job_id,)):
            raise Blocked("resolve the open question/authorization before resume")
        self.update_job(job_id, "queued")
