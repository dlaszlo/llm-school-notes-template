"""Complete Drive inventories and immutable local capture before any archive write.

The existing uploader owns OAuth refresh. V1 imports it by explicit path; it
does not silently use a checkout's .drive-state. No delete/move/share API exists.
"""
from __future__ import annotations

import importlib.util
import hashlib
import http.client
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .common import Blocked, EffectPending, Transient, WindowExhausted, atomic_json, digest, disk_gate, file_hash, private_dir, safe_relative

API = "https://www.googleapis.com/drive/v3"
FOLDER = "application/vnd.google-apps.folder"
FIELDS = "id,name,mimeType,parents,size,md5Checksum,version,modifiedTime,description,trashed,appProperties"
MAX_BYTES = 128 * 1024 * 1024


class InventoryChanged(Blocked):
    pass


class InvalidPageToken(Blocked):
    pass


class DriveError(Blocked):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Drive HTTP {status}; credentials/response omitted")


class DriveAPI:
    def __init__(self, tool_path, config_dir, visibility_evidence, window=None, reader_config=None, *, _readonly=False):
        self.window = window
        self.guard(65)
        evidence = json.loads(Path(visibility_evidence).read_text())
        required = ("token_refresh", "oauth_project_status_checked") if reader_config is not None else ("manual_upload_read", "recursive_visibility", "child_account_access", "token_refresh", "oauth_project_status_checked")
        if any(evidence.get(k) is not True for k in required):
            raise Blocked("Drive capability proof incomplete; drive.file list success is not full visibility")
        spec = importlib.util.spec_from_file_location("school_notes_existing_drive_media", tool_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if _readonly:
            # A fresh private module instance changes only its exact expected
            # scope check; shared helper bytes and the writer remain unchanged.
            module.SCOPE = 'https://www.googleapis.com/auth/drive.readonly'
        self.module = module
        try:
            self.drive = module.Drive(Path(config_dir))
        except module.Refused:
            raise Blocked("Drive authentication/configuration failed; existing executor credentials require repair") from None
        except http.client.HTTPException:
            raise Blocked('Drive token refresh interrupted; existing credentials retained, repair/retry later') from None

        self.input_reader = self
        if reader_config is not None:
            if _readonly or reader_config.get('scope')!='https://www.googleapis.com/auth/drive.readonly':
                raise Blocked('optional reader accepts only explicitly existing drive.readonly credentials')
            proof=json.loads(Path(reader_config['evidence']).read_text())
            if proof.get('scope')!=reader_config['scope'] or proof.get('config_dir')!=str(Path(reader_config['config_dir']).resolve()) or proof.get('readonly_only') is not True:
                raise Blocked('read-only proof must bind exact reader credential directory and scope')
            self.input_reader=ReadOnlyDriveAPI(tool_path,reader_config['config_dir'],reader_config['evidence'],window)

    def guard(self, seconds=95):
        if self.window:
            self.window.require(seconds)

    def request(self, *args):
        self.guard()
        try:
            return self.drive.request(*args)
        except self.module.ApiError as e:
            raise DriveError(e.status) from None
        except self.module.Refused:
            raise Blocked("Drive operation failed; retain request ID and reconcile before repetition") from None
        except http.client.HTTPException:
            raise Blocked('Drive response interrupted; retain effect and reconcile before repetition') from None

    def metadata(self, file_id):
        return self.request("GET", API + "/files/" + urllib.parse.quote(file_id, safe="") + "?" + urllib.parse.urlencode({"fields": FIELDS}))[2]

    def list_page(self, parent, token=None):
        params = {"q": "'" + parent.replace("'", "\\'") + "' in parents and trashed = false", "pageSize": "1000", "fields": f"nextPageToken,incompleteSearch,files({FIELDS})", "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if token:
            params["pageToken"] = token
        try:
            result = self.request("GET", API + "/files?" + urllib.parse.urlencode(params))[2]
        except DriveError as e:
            if e.status == 400 and token:
                raise InvalidPageToken("Drive pagination token invalid; restart full inventory") from None
            error = Transient if e.status in (429, 500, 502, 503, 504) else Blocked
            raise error(f"Drive list HTTP {e.status}; inventory is incomplete") from None
        if result.get("incompleteSearch"):
            raise Blocked("Drive returned incompleteSearch; inventory is incomplete")
        return result["files"], result.get("nextPageToken")

    def download(self, file_id, destination):
        self.guard()
        url = API + "/files/" + urllib.parse.quote(file_id, safe="") + "?alt=media"
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.drive.token})
        size = 0
        try:
            with self.drive.opener.open(req, timeout=90) as response, open(destination, "xb") as out:
                os.chmod(destination, 0o600)
                while True:
                    self.guard()
                    data = response.read(1024 * 1024)
                    if not data:
                        break
                    size += len(data)
                    if size > MAX_BYTES:
                        raise Blocked("source exceeds supported 128 MiB capture limit")
                    out.write(data)
                out.flush()
                os.fsync(out.fileno())
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException):
            raise Blocked("source download interrupted; incomplete capture retained") from None

    def reserve_id(self):
        return self.request("GET", API + "/files/generateIds?count=1&space=drive&type=files")[2]["ids"][0]

    def download_hash(self, file_id):
        self.guard()
        url = API + "/files/" + urllib.parse.quote(file_id, safe="") + "?alt=media"
        request = urllib.request.Request(url, headers={"Authorization": "Bearer " + self.drive.token})
        checksum, size = hashlib.sha256(), 0
        try:
            with self.drive.opener.open(request, timeout=90) as response:
                while True:
                    self.guard()
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise Blocked("Drive readback exceeds verified artifact size limit")
                    checksum.update(chunk)
        except urllib.error.HTTPError as e:
            raise DriveError(e.code) from None
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException):
            raise Blocked("Drive readback interrupted; preserved effect requires reconciliation") from None
        return checksum.hexdigest(), size

    def create_folder(self, file_id, name, parent, key):
        payload = {"id": file_id, "name": name, "mimeType": FOLDER, "parents": [parent], "appProperties": {"school_notes_effect": key}}
        return self.request("POST", API + "/files?fields=" + urllib.parse.quote(FIELDS), payload)[2]

    def upload(self, file_id, path, mime, parent, key, sha, *, progress=None, checkpoint=None, name=None):
        """Fixed-ID resumable transfer; session receipt precedes every chunk."""
        path = Path(path)
        total = path.stat().st_size
        if not 0 < total <= MAX_BYTES or file_hash(path) != sha:
            raise Blocked("upload input size/hash differs from frozen artifact")
        meta = {"id": file_id, "name": name or path.name, "parents": [parent], "appProperties": {"school_notes_effect": key, "sha256": sha}}
        progress = dict(progress or {})
        location = progress.get("session")
        if location:
            self.module.allowed_url(location)
            if any(progress.get(k)!=v for k,v in {'file_id':file_id,'sha256':sha,'bytes':total}.items()):
                raise Blocked('resumable receipt identity differs from frozen upload')
            try:
                status, headers, body = self.request("PUT", location, b"", {"Content-Range": f"bytes */{total}", "Content-Length": "0"})
            except DriveError as error:
                if error.status not in (404,410):
                    raise
                # Expired session may be replaced only after exact file absence
                # and readable target are established. Fixed file ID is retained.
                reconciled=self.reconcile({'external_id':file_id,'target':parent,'stable_key':key,'artifact_hash':sha})
                if reconciled and reconciled.get('verified') is True:
                    return self.metadata(file_id)
                if not reconciled or reconciled.get('absent') is not True:
                    raise EffectPending('expired resumable session outcome unknown')
                return self.upload(file_id,path,mime,parent,key,sha,checkpoint=checkpoint,name=name)
            if status in (200, 201):
                return body
            if status != 308:
                raise EffectPending("resumable upload session cannot be reconciled")
            offset = self.module.offset_of(headers, total)
        else:
            status, headers, body = self.request("POST", "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=" + urllib.parse.quote(FIELDS),
                                                 meta, {"X-Upload-Content-Type": mime, "X-Upload-Content-Length": str(total)})
            location = headers.get("Location")
            if not location:
                raise EffectPending("Drive did not return a resumable session")
            self.module.allowed_url(location)
            offset = 0
            progress = {"session": location, "offset": 0, "file_id": file_id, "sha256": sha, "bytes": total}
            if checkpoint:
                checkpoint(progress)
        with path.open("rb") as stream:
            while offset < total:
                self.guard()
                if file_hash(path) != sha:
                    raise Blocked("upload bytes changed during resumable transfer")
                stream.seek(offset)
                chunk = stream.read(min(8 * 1024 * 1024, total - offset))
                status, headers, body = self.request("PUT", location, chunk, {"Content-Type": mime, "Content-Length": str(len(chunk)),
                                                                           "Content-Range": f"bytes {offset}-{offset+len(chunk)-1}/{total}"})
                if status in (200, 201):
                    return body
                if status != 308:
                    raise EffectPending("resumable chunk verification pending")
                new_offset = self.module.offset_of(headers, total)
                if new_offset <= offset or new_offset > offset + len(chunk):
                    raise Blocked("Drive resumable offset is invalid")
                offset = new_offset
                progress["offset"] = offset
                if checkpoint:
                    checkpoint(progress)
        raise EffectPending("Drive resumable final response missing")

    def reconcile(self, effect, *, folder=False):
        if not effect.get("external_id"):
            return None
        try:
            meta = self.metadata(effect["external_id"])
        except DriveError as e:
            # Stable preallocated ID makes this a definitive absence, unlike
            # a list-by-name lookup with ambiguous permissions/visibility.
            if e.status == 404:
                try:
                    parent=self.metadata(effect['target'])
                    if parent.get('mimeType')!=FOLDER or parent.get('trashed'):
                        return None
                except (Blocked,OSError,KeyError):
                    return None
                return {"absent": True}
            return None
        expected = meta.get("parents") == [effect["target"]] and meta.get("appProperties", {}).get("school_notes_effect") == effect["stable_key"] and not meta.get("trashed")
        if not expected:
            raise Blocked("Drive reconciliation target/ownership mismatch")
        if folder:
            if meta.get("mimeType") != FOLDER or digest({'name':meta.get('name'),'parent':effect['target']})!=effect['artifact_hash']:
                raise Blocked("Drive archive folder name/MIME differs from frozen operation")
        else:
            try:
                sha, size = self.download_hash(meta["id"])
            except WindowExhausted:
                raise
            except Blocked:
                return None
            if sha != effect["artifact_hash"]:
                raise Blocked("Drive archive readback hash mismatch")
        return {"verified": True, "external_id": meta["id"], "sha256": effect["artifact_hash"], "target": effect["target"]}



class ReadOnlyDriveAPI(DriveAPI):
    """Explicit existing-credential reader; no login/grant or write surface."""
    def __init__(self,tool_path,config_dir,evidence,window=None):
        proof=json.loads(Path(evidence).read_text())
        if proof.get('scope')!='https://www.googleapis.com/auth/drive.readonly' or proof.get('config_dir')!=str(Path(config_dir).resolve()) or proof.get('readonly_only') is not True:
            raise Blocked('readonly reader proof scope/configuration mismatch')
        super().__init__(tool_path,config_dir,evidence,window,_readonly=True)

    def request(self,method,url,*args):
        parsed=urllib.parse.urlsplit(url)
        prefix='/drive/v3/files'
        if method!='GET' or parsed.scheme!='https' or parsed.netloc!='www.googleapis.com' or not (parsed.path==prefix or parsed.path.startswith(prefix+'/')) or parsed.path==prefix+'/generateIds':
            raise Blocked('read-only adapter refuses non-file GET and every mutation')
        return super().request(method,url,*args)

    def reserve_id(self):
        raise Blocked('read-only adapter cannot allocate mutation identities')

    def create_folder(self,*args,**kwargs):
        raise Blocked('read-only adapter cannot create folders')

    def upload(self,*args,**kwargs):
        raise Blocked('read-only adapter cannot upload')

def inventory(api, root_id, guard=None, *, strict_names=True):
    """A new result is returned only after every recursive page has succeeded."""
    result = []
    seen = set()
    if guard:
        guard(95)
    root = api.metadata(root_id)
    if root.get("trashed") or root.get("mimeType") != FOLDER:
        raise Blocked("configured input root is not an available folder")
    result.append({**root, "path": "", "root": True})
    def visit(parent, prefix):
        token = None
        tokens = set()
        children = []
        while True:
            if guard:
                guard(95)
            files, next_token = api.list_page(parent, token)
            for f in files:
                if f["id"] in seen:
                    raise InventoryChanged("duplicate item in paginated inventory")
                if f.get("parents") != [parent] or f.get("trashed"):
                    raise InventoryChanged("item moved during inventory")
                seen.add(f["id"])
                if strict_names:
                    safe_relative(f["name"])
                    if "/" in f["name"]:
                        raise Blocked("Drive filename contains path separator")
                children.append(f)
            if not next_token:
                break
            if next_token in tokens:
                raise Blocked("Drive returned repeating pagination token")
            tokens.add(next_token)
            token = next_token
        names = [f["name"] for f in children]
        if strict_names and len(names) != len(set(names)):
            raise Blocked("ambiguous duplicate sibling names in source package")
        for f in sorted(children, key=lambda f: (f["name"], f["id"])):
            path = str(Path(prefix) / f["name"])
            result.append({**f, "path": path})
            if f["mimeType"] == FOLDER:
                visit(f["id"], path)
    visit(root_id, "")
    return result


def snapshot_signature(items):
    keys = ("id", "name", "path", "mimeType", "parents", "size", "md5Checksum", "version", "modifiedTime", "description", "appProperties")
    return digest(sorted(({k: item.get(k) for k in keys} for item in items), key=lambda f: f["id"]))


def semantic_metadata(items):
    # Name affects interpretation only through relative reading order. A pure
    # rename keeping the same order and roles is a location update.
    return digest({"order": [f["id"] for f in sorted(items, key=lambda f: f["path"]) if f["mimeType"] != FOLDER],
                   "context": sorted(({"id": f["id"], "description": f.get("description", ""), "mime": f["mimeType"], "roles": f.get("appProperties", {}).get("source_role")} for f in items), key=lambda f: f["id"])})


def source_contract(path,mime,size=None):
    checks={"image/jpeg":(".jpg",".jpeg"),"image/png":(".png",),"application/pdf":(".pdf",)}
    if mime not in checks or Path(path).suffix.lower() not in checks[mime]:
        raise Blocked(f'unsupported source MIME/extension: {mime}; remote source and inventory preserved')
    if size is not None and not 0<int(size)<=MAX_BYTES:raise Blocked('source exceeds supported size; remote source and inventory preserved')


def supported(path, mime):
    with Path(path).open("rb") as f:
        prefix = f.read(16)
    checks = {"image/jpeg": (".jpg", ".jpeg"), "image/png": (".png",), "application/pdf": (".pdf",)}
    signatures = {"image/jpeg": prefix.startswith(b"\xff\xd8\xff"), "image/png": prefix.startswith(b"\x89PNG\r\n\x1a\n"), "application/pdf": prefix.startswith(b"%PDF-")}
    if mime not in checks or Path(path).suffix.lower() not in checks[mime] or not signatures.get(mime):
        raise Blocked(f"unsupported source MIME/signature: {mime}; original preserved in staging")
    if not 0 < Path(path).stat().st_size <= MAX_BYTES:
        raise Blocked("unsupported source size")


def verified_capture_bytes(path, metadata):
    """Validate against authoritative Drive bytes before progress or reuse."""
    path = Path(path)
    if metadata.get('size') is not None and path.stat().st_size != int(metadata['size']):
        raise InventoryChanged('source size differs from current Drive metadata')
    if metadata.get('md5Checksum'):
        checksum = hashlib.md5()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                checksum.update(chunk)
        if checksum.hexdigest() != metadata['md5Checksum']:
            raise InventoryChanged('source MD5 differs from current Drive metadata')


def capture(api, root_id, destination, reserve=4 * 1024**3, previous=None, guard=None):
    before = inventory(api, root_id, guard)
    files = [f for f in before if f["mimeType"] != FOLDER]
    if not files:
        raise Blocked("empty source package")
    old = {f["id"]: f for f in previous["files"]} if previous else {}
    # Reject metadata-known unsupported packages before creating any staging.
    for f in files:source_contract(f['path'],f['mimeType'],f.get('size'))
    same_snapshot = previous is not None and snapshot_signature(before) == previous["snapshot_hash"]
    reusable = {}
    for f in files:
        if guard:
            guard(95)
        prior = old.get(f["id"])
        same_bytes = prior and (same_snapshot or (f.get("md5Checksum") and f["md5Checksum"] == prior.get("md5Checksum") and f.get("size") == str(prior["size"])))
        if same_bytes and Path(prior["local"]).is_file() and file_hash(prior["local"]) == prior["sha256"]:
            try:
                verified_capture_bytes(prior['local'], f)
            except InventoryChanged:
                # Retain suspect old bytes; only a fresh capture can replace
                # their eligibility. Never promote a self-consistent old hash.
                continue
            supported(prior['local'], f['mimeType'])
            reusable[f["id"]] = prior
    if same_snapshot and len(reusable)==len(files):
        for f in files:verified_capture_bytes(reusable[f['id']]['local'], f)
        after=inventory(api,root_id,guard)
        if snapshot_signature(before)!=snapshot_signature(after):
            raise InventoryChanged('unchanged source changed during validation')
        # No destination directory or duplicate capture receipt for unchanged
        # complete observations. Existing immutable bytes are rehashed above.
        return {'source_id':root_id,'inventory':before,'snapshot_hash':snapshot_signature(before),'metadata_hash':semantic_metadata(before),'files':[{**reusable[f['id']],**f,'size':reusable[f['id']]['size']} for f in files]}
    estimate = sum(int(f.get("size", 0)) for f in files if f["id"] not in reusable)
    disk_gate(destination, estimate * 3, reserve)
    destination = private_dir(destination)
    original = private_dir(destination / "original")
    captured = []
    for f in files:
        if f["id"] in reusable:
            prior = reusable[f["id"]]
            verified_capture_bytes(prior['local'], f)
            supported(prior['local'], f['mimeType'])
            captured.append({**f, "sha256": prior["sha256"], "local": prior["local"], "size": prior["size"],
                             **{k: prior[k] for k in ("prepared", "prepared_sha256", "archive_original", "read_source", "source_pages") if k in prior}})
            atomic_json(destination/'progress.json',{'inventory':before,'captured':captured})
            continue
        disk_gate(destination, int(f.get("size", MAX_BYTES)), reserve)
        path = original / safe_relative(f["path"])
        private_dir(path.parent)
        if int(f.get("size", 0)) > MAX_BYTES:
            atomic_json(destination / "blocked.json", {"inventory": before, "captured": captured, "reason": "source exceeds 128 MiB"})
            raise Blocked("source exceeds supported 128 MiB size; retained inventory")
        api.download(f["id"], path)
        verified_capture_bytes(path, f)
        captured.append({**f, "sha256": file_hash(path), "local": str(path), "size": path.stat().st_size})
        atomic_json(destination / "progress.json", {"inventory": before, "captured": captured})
        # Integrity-verified but unsupported signatures remain recorded for a
        # stable blocker. They never pass the signature gate on later reuse.
        supported(path, f['mimeType'])
    after = inventory(api, root_id, guard)
    if snapshot_signature(before) != snapshot_signature(after):
        raise InventoryChanged("source package changed during capture; no archive/classification")
    manifest = {"source_id": root_id, "inventory": before, "snapshot_hash": snapshot_signature(before), "metadata_hash": semantic_metadata(before), "files": captured}
    atomic_json(destination / "capture.json", manifest)
    return manifest


class Archive:
    def __init__(self, api, state, root_id, guard=None):
        self.api, self.state, self.root_id = api, state, root_id
        self.guard = guard

    def _effect(self, job_id, kind, target, artifact_hash, key):
        if self.guard:
            self.guard(95)
        effect = self.state.effect(job_id, kind, target, artifact_hash, key)
        if effect["state"] == "planned" and not effect["external_id"]:
            # Reserve IDs is non-writing and safely repeatable; ID is persisted
            # before any externally visible create/upload.
            self.state.effect_state(key, "planned", external_id=self.api.reserve_id())
            effect = self.state.rows("SELECT * FROM effects WHERE stable_key=?", (key,))[0]
        return effect

    def folder(self, job_id, parent, name, key):
        effect = self._effect(job_id, "drive-folder", parent, digest({"name": name, "parent": parent}), key)
        def execute(e):
            self.api.create_folder(e["external_id"], name, parent, key)
            return self.api.reconcile(e, folder=True)
        return self.state.perform_effect(effect, execute, lambda e: self.api.reconcile(e, folder=True))["external_id"]

    def upload(self, job_id, parent, path, mime, key, *, expected_hash=None, name=None):
        sha = file_hash(path)
        if expected_hash is not None and sha != expected_hash:
            raise Blocked("archive input hash differs from classified frozen source")
        effect = self._effect(job_id, "drive-upload", parent, sha, key)
        def execute(e):
            if file_hash(path) != sha:
                raise Blocked("upload input changed before external write")
            if isinstance(self.api, DriveAPI):
                receipt = json.loads(e["receipt"]) if e["receipt"] else None
                self.api.upload(e["external_id"], path, mime, parent, key, sha, progress=receipt,
                                checkpoint=lambda p: self.state.effect_state(key, "inflight", p), name=name)
            else:
                self.api.upload(e["external_id"], path, mime, parent, key, sha, name=name)
            return self.api.reconcile(e)
        return self.state.perform_effect(effect, execute, self.api.reconcile)

    def package(self, job, classified):
        files = job["payload"]["manifest"]["files"]
        check_classification(files, classified, job["payload"]["manifest"].get("input_context", {}).get("source_role"))
        for f in files:
            for field, expected in (("archive_original", f["sha256"]), ("read_source", f.get("prepared_sha256", f["sha256"]))):
                path = f.get(field, f["local"] if field == "archive_original" else f.get("prepared", f["local"]))
                if file_hash(path) != expected:
                    raise Blocked("frozen classified/archive source bytes changed; no archive writes")
        root = self.folder(job["id"], self.root_id, f"package-{job['package_id']}", f"archive-package:{job['learner']}:{job['package_id']}")
        receipts = []
        for category, field in (("original", "archive_original"), ("prepared", "read_source")):
            base = self.folder(job["id"], root, category, f"archive-root:{job['learner']}:{job['package_id']}:{category}")
            folder_ids = {".": base}
            for f in files:
                if category == "prepared" and "prepared_sha256" not in f:
                    continue
                path = f.get(field, f["local"] if category == "original" else f["prepared"])
                relative = safe_relative(f["path"])
                parent = base
                for i in range(1, len(relative.parts)):
                    sub = "/".join(relative.parts[:i])
                    if sub not in folder_ids:
                        folder_ids[sub] = self.folder(job["id"], parent, relative.parts[i - 1], f"archive-sub:{job['learner']}:{job['package_id']}:{category}:{digest(sub)}")
                    parent = folder_ids[sub]
                # Identical byte objects in metadata-only revisions are reused.
                expected = f["sha256"] if category == "original" else f["prepared_sha256"]
                key = f"archive-file:{job['learner']}:{job['package_id']}:{category}:{f['id']}:{expected}"
                receipts.append(self.upload(job["id"], parent, path, f["mimeType"], key, expected_hash=expected, name=relative.name))
        record = {"revision_seq": job["revision_seq"], "metadata_hash": job["payload"]["manifest"]["metadata_hash"],
                  "input_context": job["payload"]["manifest"].get("input_context"), "inventory": job["payload"]["manifest"]["inventory"],
                  "files": [{"id": f["id"], "path": f["path"], "original_sha256": f["sha256"], "prepared_sha256": f.get("prepared_sha256")} for f in files],
                  "receipts": receipts}
        record_path = Path(files[0]["local"]).parents[len(Path(files[0]["path"]).parts)] / f"metadata-{job['revision_seq']}.json"
        atomic_json(record_path, record)
        receipts.append(self.upload(job["id"], root, record_path, "application/json", f"archive-metadata:{job['learner']}:{job['package_id']}:{job['revision_seq']}:{digest(record)}"))
        return receipts


def check_classification(files, classified, source_role=None):
    expected = {f["id"]: f.get("prepared_sha256", f["sha256"]) for f in files}
    if not isinstance(classified, list) or len(classified) != len(expected):
        raise Blocked("classification does not cover the entire package")
    seen = set()
    for item in classified:
        if item.get("id") in seen or expected.get(item.get("id")) != item.get("sha256"):
            raise Blocked("classification hash/identity mismatch")
        seen.add(item["id"])
        if item.get("source_class") not in ("notebook", "teacher_learn") or item.get("uncertain") is not False:
            raise Blocked("book/background/reference, mixed or uncertain package: local-reference decision required before archive")
        if source_role and item["source_class"] != source_role:
            raise Blocked("input role and content classification differ: content question required")
