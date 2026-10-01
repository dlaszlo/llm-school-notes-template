"""Public release effects. Direct admin approval, frozen bytes and readback only."""
from __future__ import annotations

import hashlib
import http.client
import json
from pathlib import Path
import re
import stat
import urllib.error
import urllib.parse
import urllib.request

from .common import Blocked, EffectPending, WindowExhausted, atomic_json, digest, file_hash, run
from .verify import Git, Renderer, manifest_with_hashes, review_gate, scan


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_):
        return None


class GitHub:
    def __init__(self, settings, window=None):
        self.window = window
        self.settings = settings
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", settings.get("repository", "")):
            raise Blocked("explicit public repository target required")
        proof = json.loads(Path(settings["evidence"]).read_text())
        if any(proof.get(k) is not True for k in ("draft_release", "asset_readback", "workflow_dispatch", "dispatch_identity_verified", "public_repo_only")):
            raise Blocked("Release/workflow API capability proof incomplete")
        token = Path(settings["token_file"])
        mode = token.lstat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise Blocked("GitHub token must be a private ordinary file")
        self.token = token.read_text().strip()
        self.opener = urllib.request.build_opener(NoRedirect)
        self.base = "https://api.github.com/repos/" + settings["repository"]

    def request(self, method, path, data=None, *, raw=False, upload=False):
        try:
            return self._request(method,path,data,raw=raw,upload=upload)
        except http.client.HTTPException:
            raise Blocked('GitHub response interrupted; retain effect and reconcile before repetition') from None

    def _request(self, method, path, data=None, *, raw=False, upload=False):
        if self.window:
            self.window.require(95)
        url = self.base + path if not upload else "https://uploads.github.com/repos/" + self.settings["repository"] + path
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/octet-stream" if raw else "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "school-notes-v1"}
        if isinstance(data, dict):
            data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            headers["Content-Type"] = "application/octet-stream"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=90)
        except urllib.error.HTTPError as e:
            if e.code == 404 and method == "GET":
                return None
            if e.code in (301, 302, 303, 307, 308) and raw and method == "GET":
                location = e.headers.get("Location", "")
                address = urllib.parse.urlsplit(location)
                if address.scheme != "https" or not address.hostname or not address.hostname.endswith(".githubusercontent.com"):
                    raise Blocked("unexpected asset download redirect") from None
                # No credential follows a cross-origin asset redirect.
                response = self.opener.open(urllib.request.Request(location), timeout=90)
            else:
                raise Blocked(f"GitHub HTTP {e.code}; response and credential omitted") from None
        body = bytearray()
        with response:
            while True:
                if self.window:
                    self.window.require(95)
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > 1024**3:
                    raise Blocked("GitHub response exceeds finite artifact limit")
        body = bytes(body)
        return body if raw else json.loads(body) if body else {}

    def release(self, tag):
        # Tag lookup is only useful for a published release, never evidence that
        # an authenticated draft is absent.
        return self.request("GET", "/releases/tags/" + urllib.parse.quote(tag, safe=""))

    def pages(self, path):
        items = []
        for page in range(1, 101):
            values = self.request("GET", path + f"?per_page=100&page={page}")
            if not isinstance(values, list):
                raise Blocked("GitHub complete list unavailable")
            items.extend(values)
            if len(values) < 100:
                return items
        raise Blocked("GitHub inventory exceeded finite pagination bound")

    def draft_reconcile(self, effect, tag):
        release = self.request("GET", "/releases/" + effect["external_id"]) if effect.get("external_id") else None
        if release is None:
            matches = [r for r in self.pages("/releases") if r.get("tag_name") == tag]
            if len(matches) > 1:
                raise Blocked("ambiguous draft release identity")
            release = matches[0] if matches else None
        if release is None:
            return None  # Unknown POST outcome may never create a second draft.
        if release.get("tag_name") != tag or release.get("body") != "School Notes bundle sha256=" + effect["artifact_hash"]:
            raise Blocked("Release reconciliation identity/hash differs")
        return {"verified": True, "external_id": str(release["id"]), "tag": tag, "draft": release["draft"]}

    def live_get(self, url):
        if self.window:
            self.window.require(95)
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                content = response.read(128 * 1024**2 + 1)
        except http.client.HTTPException:
            raise Blocked('live response interrupted; retained verification attempt remains bounded') from None
        if len(content) > 128 * 1024**2:
            raise Blocked("live artifact exceeds readback limit")
        return content

    def asset_reconcile(self, effect, release_id, name):
        assets = self.pages(f"/releases/{release_id}/assets")
        matching = [asset for asset in assets if asset["name"] == name]
        if not matching:
            return None
        if len(matching) != 1:
            raise Blocked("Release asset name is ambiguous")
        asset = matching[0]
        content = self.request("GET", f"/releases/assets/{asset['id']}", raw=True)
        if content is None or hashlib.sha256(content).hexdigest() != effect["artifact_hash"]:
            raise Blocked("Release asset downloaded bytes differ from frozen bundle")
        return {"verified": True, "external_id": str(asset["id"]), "sha256": effect["artifact_hash"], "name": name}

    def dispatch_reconcile(self, effect, tag):
        workflow = self.settings.get("workflow", "publish.yml")
        if workflow != "publish.yml":
            raise Blocked("only the configured publish.yml workflow may dispatch")
        expected = self.settings["run_title"].replace("{tag}", tag)
        # Follow every page; a missing correlation is UNKNOWN, never permission
        # to blindly dispatch a second run.
        matches = []
        for page in range(1, 101):
            result = self.request("GET", f"/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=100&page={page}")
            runs = result.get("workflow_runs", [])
            matches += [r for r in runs if r.get("display_title") == expected]
            if len(runs) < 100:
                break
        else:
            raise Blocked("workflow run inventory exceeded finite pagination limit")
        if len(matches) != 1:
            return None
        match = matches[0]
        if match["status"] != "completed":
            return None
        if match.get("conclusion") != "success":
            raise Blocked("Pages workflow completed without success")
        return {"verified": True, "external_id": str(match["id"]), "tag": tag, "conclusion": "success"}


def publish(supervisor, job):
    state, payload = supervisor.state, job["payload"]
    if job["kind"] != "public_release":
        raise Blocked("publication requires an independent current-HEAD public job")
    settings = supervisor.learner(job["learner"])
    main = Git(settings["repo"], supervisor.lock)
    prior_push=state.rows("SELECT * FROM effects WHERE stable_key=? AND state='verified'",('public-manifest-push:'+payload.get('public_commit',''),))
    if prior_push:
        # Immutable source/render gates remain active; no old candidate Git
        # is executed after its exact remote push has already been verified.
        from types import SimpleNamespace
        candidate=SimpleNamespace(repo=Path(payload['worktree']))
    else:
        candidate=main.worktree(supervisor.job_dir(job)/'public-worktree',payload['base'],payload.get('git_identity'))
        payload['git_identity']=candidate.identity
    payload["worktree"] = str(candidate.repo)
    payload["commit"] = payload["base"]
    state.update_job(job["id"],payload=payload)
    manifest = payload["public_manifest"]
    manifest_hash = digest(manifest)
    if manifest_with_hashes(candidate.repo, manifest) != manifest or manifest.get("mode") != "public" or manifest.get("publicationApproved") is not True:
        raise Blocked("public source/configuration changed")
    renderer = Renderer(supervisor.config["renderer"], supervisor.lock, supervisor.window)
    root = Path(supervisor.config["renderer"]["package"])
    tag = "school-notes-" + digest({"base":payload["base"],"manifest":manifest,"job_id":job["id"]})[:24]
    render_dir = supervisor.job_dir(job) / f"public-preview-{payload.get('public_render_attempt',0)}"
    if (render_dir / "build").exists() and not (render_dir / "complete.json").exists():
        attempt = payload.get("public_render_attempt",0)+1
        if attempt >= 3 + payload.get("public_render_extra",0):
            raise Blocked("partial public previews retained; retry-render public required")
        payload["public_render_attempt"] = attempt
        state.update_job(job["id"],payload=payload)
        render_dir = supervisor.job_dir(job) / f"public-preview-{attempt}"
    build, images = renderer.build(candidate.repo, manifest, render_dir)
    artifacts = renderer.artifacts(build)
    review_input = [{"path": str(build/name),"sha256":sha,"kind":"public-artifact"} for name,sha in artifacts.items() if name.endswith((".html",".svg",".json",".txt"))]
    review_input += images
    review_input += [{"path": str(candidate.repo/item["path"]),"sha256":item["sha256"],"kind":"public-source"} for item in manifest["pages"]+manifest.get("assets",[])]
    paths = supervisor.bounded_review(job,"public_review",review_input,"public-privacy,rights,visual,all_pdf_pages",require_public=True,
                                      instructions="Review every designated public HTML/search/asset/PDF page against exact source/rights manifest. Check public privacy, generated credits, attribution, and asset rights. No edits.")
    payload["public_review"] = paths[0]
    payload["public_review_paths"] = paths
    payload["public_artifacts"] = artifacts
    bundle_base="bundle-"+manifest_hash[:16]
    bundle=None
    for attempt in range(3+payload.get('public_render_extra',0)):
        attempt_dir=supervisor.job_dir(job)/(bundle_base+f'-{attempt}')
        if not attempt_dir.exists() or ((attempt_dir/'site.tar.gz').is_file() and (attempt_dir/'site.tar.gz.sha256').is_file()):
            bundle=attempt_dir
            break
    if bundle is None:
        raise Blocked('partial bundle attempts retained; retry-render public required')
    verified=None
    for attempt in range(3+payload.get('public_render_extra',0)):
        attempt_dir=bundle.with_name(bundle.name+f'-verified-{attempt}')
        complete=attempt_dir.with_name(attempt_dir.name+'.complete.json')
        if not attempt_dir.exists() or complete.exists():
            verified=attempt_dir
            break
    if verified is None:
        raise Blocked('partial bundle verification attempts retained; retry-render public required')
    if not bundle.exists():
        run([supervisor.config["agents"]["python"],str(root/"release-bundle.py"),"pack",str(build),str(bundle),tag],supervisor.job_dir(job),lock=supervisor.lock)
    if not verified.exists():
        run([supervisor.config["agents"]["python"],str(root/"release-bundle.py"),"verify",str(bundle/"site.tar.gz"),str(verified),manifest["base"],tag],supervisor.job_dir(job),lock=supervisor.lock)
        atomic_json(verified.with_name(verified.name+'.complete.json'),{'bundle_sha256':file_hash(bundle/'site.tar.gz'),'files':renderer.artifacts(verified)})
    verified_receipt=json.loads(verified.with_name(verified.name+'.complete.json').read_text())
    if verified_receipt!={'bundle_sha256':file_hash(bundle/'site.tar.gz'),'files':renderer.artifacts(verified)}:
        raise Blocked('verified extraction changed after bundle verification')
    expected_sha=(bundle/"site.tar.gz.sha256").read_text().split()[0]
    if file_hash(bundle/"site.tar.gz") != expected_sha:
        raise Blocked("frozen public bundle hash changed")
    proposal={"base_sha":payload["base"],"manifest":manifest,"artifacts":artifacts,"bundle_sha256":expected_sha,
              "bundle_files":renderer.artifacts(bundle),"verified_files":renderer.artifacts(verified),
              "reviews":{p:file_hash(p) for p in paths},"release_tag":tag}
    if payload.get("public_proposal") and payload["public_proposal"] != proposal:
        raise Blocked("approved/frozen public preview changed; request a new public job")
    payload["public_proposal"] = proposal
    payload["public_preview"] = str(build)
    state.update_job(job["id"],payload=payload)
    atomic_json(supervisor.job_dir(job)/"public-proposal.json",proposal)
    approval_hash=digest(proposal)
    approval=state.rows("SELECT id FROM questions WHERE job_id=? AND kind='authorization' AND scope='public' AND manifest_hash=? AND state='approved' AND origin='direct-vm-admin'",(job["id"],approval_hash))
    if len(approval) != 1:
        state.question(job["id"],"authorization","public",f"Review concrete preview {build} and frozen bundle {bundle}; approve exact proposal hash via direct VM admin",approval_hash)
        state.update_job(job["id"],"approval_wait",error=f"approve-public {job['id']} {approval_hash}")
        return
    if not settings.get("public"):
        raise Blocked("public adapter not configured; reviewed and approved bytes retained")
    api = GitHub(settings["public"], supervisor.window)
    current=main.inspect(fetch=True)
    prior_push=state.rows("SELECT * FROM effects WHERE stable_key=? AND state='verified'",('public-manifest-push:'+payload.get('public_commit',''),))
    if prior_push:
        if payload['public_commit'] not in main.git('rev-list','refs/remotes/origin/main').splitlines():
            raise Blocked('verified public manifest commit no longer in remote history')
    elif current not in (payload['base'],payload.get('public_commit')):
        raise Blocked('public HEAD moved before verified manifest push; request a fresh public job')
    review_records={f"docs/review/school-notes-{job['id']}-public-{digest(path)[:16]}.json":path for path in payload.get('public_review_paths',[payload['public_review']])}
    # Recover only the exact supervisor manifest and EVERY accepted chunk.
    if not prior_push and candidate.head() != payload.get("public_commit",payload["base"]):
        names=set(candidate.diff_names(payload['base'],'HEAD'))
        if (payload.get('public_commit') or candidate.git('rev-parse','HEAD^')!=payload['base'] or names!={'publication/public.json',*review_records}
            or json.loads((candidate.repo/'publication/public.json').read_text())!=manifest
            or any(file_hash(candidate.repo/name)!=file_hash(path) for name,path in review_records.items())):
            raise Blocked('public candidate moved outside exact supervisor commit')
        payload['public_commit']=candidate.head();state.update_job(job['id'],payload=payload)
    # Track only public.json and accepted private review evidence in a separate
    # supervisor commit. Publication source bytes remain exactly the reviewed
    # fixed source commit. Crash repair requires the saved commit receipt.
    if not prior_push:candidate.verify_manifest_tree(manifest,payload['base'])
    if not payload.get("public_commit"):
        target = candidate.repo / "publication/public.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        import shutil
        for review_name,path in review_records.items():
            review_target=candidate.repo/review_name
            review_target.parent.mkdir(parents=True,exist_ok=True)
            if review_target.exists() and file_hash(review_target)!=file_hash(path):
                raise Blocked('public review Git record differs')
            if not review_target.exists():shutil.copyfile(path,review_target)
        candidate.git('add','--','publication/public.json',*review_records)
        identity = supervisor.config["git_identity"]
        if identity["email"].endswith(".invalid"):
            raise Blocked("real approved Git author identity required")
        candidate.git("-c", f"user.name={identity['name']}", "-c", f"user.email={identity['email']}", "commit", "-m", f"Approve public manifest {manifest_hash}\n\nCo-Authored-By: School Notes (gpt-6.1-sol/high) <agent@school-notes.invalid>")
        payload["public_commit"] = candidate.head()
        state.update_job(job["id"], payload=payload)
    effect = state.effect(job["id"], "git-push", settings["repo"] + ":main", payload["public_commit"], "public-manifest-push:" + payload["public_commit"])
    def push_preflight():
        current_ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
        if current_ack!=payload['base']:raise Blocked('public push base is no longer acknowledged')
        main = Git(settings["repo"], supervisor.lock)
        main.clean()
        main.git("fetch", "--no-tags", "origin", "main")
        if main.head()!=main.git('rev-parse','refs/remotes/origin/main'):
            raise Blocked('unpushed/diverged owner commit before public manifest push; reconcile owner Git, then continue preserved job')
        if main.git("rev-parse", "refs/remotes/origin/main") != payload["commit"]:
            raise Blocked("private remote moved before public manifest push")
        if candidate.head()!=payload['public_commit']:raise Blocked('public candidate commit changed before push')
    def push(e):
        candidate.git('push','origin','HEAD:refs/heads/main')
        return main.push_reconcile(e)
    state.perform_effect(effect,push,main.push_reconcile,push_preflight)
    main = Git(settings["repo"], supervisor.lock)
    try:
        main.clean()
        if main.head() == payload["commit"]:
            main.git("merge", "--ff-only", payload["public_commit"])
        elif main.head() != payload["public_commit"]:
            raise Blocked("interactive checkout changed after public manifest push")
        payload["public_local_sync"] = "verified"
    except Blocked:
        payload["public_local_sync"] = "blocked_after_verified_push"
    current_ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
    if current_ack==payload['base']:
        with state.db:state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=?,state='complete' WHERE id=?",(payload['public_commit'],payload['public_commit'],f"baseline:{job['learner']}"))
        state.wake_ack_waiters(job['learner'])
    elif current_ack!=payload['public_commit'] and payload['public_commit'] not in main.git('rev-list',current_ack).splitlines():
        raise Blocked('public manifest acknowledgement cannot regress or skip unknown history')
    state.update_job(job["id"], payload=payload)
    effect = state.effect(job["id"], "release-draft", settings["public"]["repository"], expected_sha, f"release-draft:{settings['public']['repository']}:{tag}:{expected_sha}")
    def draft(e):
        matches=[r for r in api.pages("/releases") if r.get("tag_name")==tag]
        if matches:
            return api.draft_reconcile(e,tag)
        created=api.request("POST", "/releases", {"tag_name": tag, "name": tag, "draft": True, "prerelease": False,"body":"School Notes bundle sha256="+expected_sha})
        if not isinstance(created,dict) or not created.get("id"):
            raise EffectPending("draft POST identity unavailable")
        state.effect_state(e["stable_key"],"inflight",external_id=str(created["id"]))
        return api.draft_reconcile({**e,"external_id":str(created["id"])},tag)
    receipt = state.perform_effect(effect, draft, lambda e: api.draft_reconcile(e, tag))
    release_id = receipt["external_id"]
    for path in (bundle / "site.tar.gz", bundle / "site.tar.gz.sha256"):
        effect = state.effect(job["id"], "release-asset", f"{release_id}:{path.name}", file_hash(path), f"release-asset:{release_id}:{path.name}:{file_hash(path)}")
        def upload(e, path=path):
            api.request("POST", f"/releases/{release_id}/assets?name=" + urllib.parse.quote(path.name), path.read_bytes(), upload=True)
            return api.asset_reconcile(e, release_id, path.name)
        state.perform_effect(effect, upload, lambda e, path=path: api.asset_reconcile(e, release_id, path.name))
    effect = state.effect(job["id"], "release-publish", release_id, expected_sha, f"release-publish:{release_id}:{expected_sha}")
    def publication_reconcile(e):
        release = api.request("GET",f"/releases/{release_id}")
        if release is None:
            return None
        if str(release["id"]) != release_id:
            raise Blocked("public release ID changed")
        return {"absent": True} if release["draft"] else {"verified": True, "external_id": release_id, "tag": tag}
    def publication_execute(e):
        api.request("PATCH", f"/releases/{release_id}", {"draft": False})
        return publication_reconcile(e)
    state.perform_effect(effect, publication_execute, publication_reconcile)
    effect = state.effect(job["id"], "workflow-dispatch", settings["public"]["repository"] + ":publish.yml", expected_sha, f"dispatch:{settings['public']['repository']}:{tag}:{expected_sha}")
    def dispatch(e):
        release_input = settings["public"].get("release_input")
        if not isinstance(release_input, str) or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_-]*", release_input):
            raise Blocked("verified workflow release input name must be configured")
        api.request("POST", "/actions/workflows/publish.yml/dispatches", {"ref": settings["public"].get("ref", "main"), "inputs": {release_input: tag}})
        # Workflow completion is asynchronous. If not yet visible/successful,
        # leave UNKNOWN. Subsequent runs reconcile and never blindly repeat.
        return api.dispatch_reconcile(e, tag)
    state.perform_effect(effect, dispatch, lambda e: api.dispatch_reconcile(e, tag))
    live = settings["public"]["site"].rstrip("/")
    live_attempt=payload.get('live_verification_attempts',0)+1
    if live_attempt>5:raise Blocked('live verification attempt limit (5/5) exhausted; inspect retained release and close/manual verification, never redispatch')
    payload['live_verification_attempts']=live_attempt
    state.update_job(job['id'],payload=payload)
    try:
        live_record = json.loads(api.live_get(live + manifest["base"] + "release.json"))
        frozen_record = json.loads((verified / "release.json").read_text())
        if live_record != frozen_record:
            raise EffectPending("CDN release.json not yet at frozen release")
        for pdf in sorted((build / "site/pdf").glob("*.pdf")):
            content = api.live_get(live + manifest["base"] + "pdf/" + urllib.parse.quote(pdf.name))
            if hashlib.sha256(content).hexdigest() != file_hash(pdf):
                raise EffectPending("CDN PDF not yet at reviewed bytes")
        run([supervisor.config["renderer"]["node"], str(root / "check-browser.mjs"), live, str(build / "payload.json"), supervisor.config["renderer"]["browser"], str(supervisor.job_dir(job) / "live-browser.json")], root, timeout=300, lock=supervisor.lock, log=supervisor.job_dir(job) / "live-browser.log")
    except WindowExhausted:
        payload['live_verification_attempts']=live_attempt-1;state.update_job(job['id'],payload=payload)
        raise
    except (Blocked,OSError,ValueError) as error:
        payload['live_verification_error']=str(error);state.update_job(job['id'],payload=payload)
        if live_attempt>=5:raise Blocked('live verification attempt limit (5/5) exhausted; published release retained, direct admin/manual closure required') from None
        raise EffectPending('live verification/CDN pending; bounded read-only retry, no repeated release or dispatch') from None
    payload.update(public_state="verified", release_tag=tag, release_id=release_id)
    state.update_job(job["id"], "complete", "done", payload)
