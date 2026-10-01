"""Direct admin commands and a cooperative interactive wrapper."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid

from .common import Blocked, Busy, RunLock, atomic_json, digest, file_hash, now, private_dir, terminate_group
from . import admin
from .config import load
from .drive import Archive, DriveAPI
from .pipeline import Supervisor
from .report import write as write_report
from .state import State
from . import session
from .verify import Git, Renderer, manifest_with_hashes


def parser():
    p = argparse.ArgumentParser(prog="school-notes")
    p.add_argument("--config", required=True, help="trusted secret-free configuration, absolute paths")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="exclusive DB creation and baseline inventory; never overwrite")
    for command in ('run-once','sync'):
        item=sub.add_parser(command,help='finite processing' if command=='run-once' else 'observation only; no models/archive/finalization')
        item.add_argument('--learner');item.add_argument('--max-seconds',type=int)
        if command=='run-once':item.add_argument('--job',type=int)
    item=sub.add_parser('status',help='read-only state and lock/session-owner report');item.add_argument('--learner')
    item=sub.add_parser('build-preview',help='private unreviewed renderer/browser/PDF QA only');item.add_argument('learner')
    sub.add_parser("recover", help="retain interrupted work and require effect reconciliation")
    baseline = sub.add_parser("baseline-inventory", help="explicit initial inventory recovery; no ingest")
    baseline.add_argument("learner")
    select = sub.add_parser("select-baseline", help="one-time selection of an existing unprocessed package")
    select.add_argument("learner")
    select.add_argument("source_id")
    acknowledge = sub.add_parser("acknowledge-baseline", help="import exact closed-history evidence")
    acknowledge.add_argument("learner")
    acknowledge.add_argument("evidence")
    answer = sub.add_parser("answer", help="content answers only; never authorization")
    answer.add_argument("question_id", type=int)
    answer.add_argument("file", help="UTF-8 content answer file")
    answer.add_argument("--origin", choices=("admin-content", "drive-txt", "drive-description", "private-git"), default="admin-content")
    approve = sub.add_parser("approve-public", help="direct VM-admin exact-manifest authorization")
    approve.add_argument("job_id", type=int)
    approve.add_argument("manifest_sha256")
    request = sub.add_parser("request-public", help="freeze a proposed public manifest for admin review")
    request.add_argument("job_id", type=int)
    request.add_argument("manifest")
    retry = sub.add_parser("resume", help="resume preserved work; does not raise attempt/quota limits")
    retry.add_argument("job_id", type=int)
    ext = sub.add_parser("finalize-external", help="commit reviewed private manifest; guarded private push")
    ext.add_argument("job_id", type=int)
    interactive = sub.add_parser("interactive", help="lock a trusted local session and write provenance receipt")
    interactive.add_argument("learner")
    interactive.add_argument("argv", nargs=argparse.REMAINDER)
    for command in ('propose-subject','clear-quota'):
        item=sub.add_parser(command)
        item.add_argument('job_id',type=int)
        item.add_argument('file')
    for command in ('approve-subject','approve-attempts'):
        item=sub.add_parser(command)
        item.add_argument('job_id',type=int)
        item.add_argument('proposal_sha256')
    attempts=sub.add_parser('propose-attempts')
    attempts.add_argument('job_id',type=int)
    attempts.add_argument('phase')
    attempts.add_argument('limit',type=int)
    attempts.add_argument('timeout_limit',type=int)
    render=sub.add_parser('retry-render')
    render.add_argument('job_id',type=int)
    render.add_argument('target',choices=('source','private','public','prepare','external'))
    reject=sub.add_parser('reject-package')
    reject.add_argument('job_id',type=int)
    reject.add_argument('reason')
    for command in ('reconcile-job','resume-effects','rebase-candidate','public-proposal','inspect-job'):
        item=sub.add_parser(command)
        item.add_argument('job_id',type=int)
    for command in ('acknowledge-maintenance','close-job'):
        item=sub.add_parser(command); item.add_argument('job_id',type=int); item.add_argument('file')
    item=sub.add_parser('resolve-effect'); item.add_argument('effect_key'); item.add_argument('file')
    item=sub.add_parser('inspect-effect'); item.add_argument('effect_key')
    item=sub.add_parser('inspect-package'); item.add_argument('learner'); item.add_argument('source_id')
    item=sub.add_parser('link-baseline'); item.add_argument('learner'); item.add_argument('source_id'); item.add_argument('file')
    return p


def closure(path, observed):
    value = json.loads(Path(path).read_text())
    if value.get("observed_sha") != observed or value.get("ack_sha") != observed or value.get("open_reviews") != [] or value.get("open_questions") != [] or not value.get("closure_records"):
        raise Blocked("baseline requires exact observed/ack SHA and documented closure of all reviews/questions")
    for record in value["closure_records"]:
        if not Path(record["path"]).is_absolute() or file_hash(record["path"]) != record["sha256"]:
            raise Blocked("baseline closure record hash mismatch")
    return value


def acknowledge_initial_baseline(supervisor,learner,path):
    state=supervisor.state
    rows=state.rows('SELECT * FROM observations WHERE id=?',(f'baseline:{learner}',))
    if not rows or rows[0]['ack_sha']:raise Blocked('baseline not awaiting closure import')
    initial=state.meta(f'baseline-initial:{learner}') or json.loads(rows[0]['manifest']).get('observed_sha')
    if not initial:raise Blocked('immutable initial baseline SHA missing; direct maintenance evidence required')
    value=closure(path,initial)
    with state.db:state.db.execute("UPDATE observations SET ack_sha=?,state='complete',manifest=? WHERE id=?",(initial,json.dumps(value),f'baseline:{learner}'))
    state.wake_ack_waiters(learner)
    return {'baseline_ack':initial,'observed_sha':rows[0]['observed_sha'],'later_range':'requires separate external review when observed != initial'}


def scoped_status(status,state,learner=None):
    if learner is None:return status
    for key in ("observations","packages","jobs","effects"):
        status[key]=[row for row in status[key] if row.get("learner")==learner]
    ids={r["id"] for r in state.rows("SELECT id FROM jobs WHERE learner=?",(learner,))}
    status["questions"]=[r for r in status["questions"] if r["job_id"] in ids]
    return status


def read_status(state, config, learner=None):
    # No API client or lock acquisition; a live writer remains visible.
    supervisor = Supervisor(config, state, None, None)
    status = scoped_status(supervisor.status(),state,learner)
    owner_path = Path(config["lock_file"]).with_suffix(".owner.json")
    status["lock_owner"] = json.loads(owner_path.read_text()) if owner_path.exists() else None
    status["last_report"] = json.loads((Path(config["reports_dir"]) / "latest.json").read_text()) if (Path(config["reports_dir"]) / "latest.json").exists() else None
    status.update(session.diagnostics(config))
    if learner:status["last_report"]=None # shared report may contain the other learner
    return status


def initialize(config, lock):
    if Path(config['state_db']).exists() or Path(config['state_db']).is_symlink():
        raise FileExistsError('state DB already exists; explicit init never replaces it')
    baselines = {}
    for learner, settings in config["learners"].items():
        actual=Git(settings["repo"],lock).inspect(fetch=True)
        if actual!=settings["observed_sha"]:
            raise Blocked("configured initial observed_sha differs from clean HEAD/origin main; DB not created")
        info = {"observed_sha": actual}
        if settings.get("baseline_closure"):
            value = closure(settings["baseline_closure"], settings["observed_sha"])
            info.update(ack_sha=value["ack_sha"], closure_evidence={"path": settings["baseline_closure"], "sha256": file_hash(settings["baseline_closure"]), "records": value["closure_records"]})
        baselines[learner] = info
    return State.initialize(config["state_db"], baselines)


wrapper=session.wrapper


def finalize_external(supervisor, job_id):
    state=supervisor.state;job=state.job(job_id);payload=job['payload']
    if job['kind']!='external_change_review':raise Blocked('not an external-change review job')
    completed_push=payload.get('manifest_commit') and state.rows("SELECT stable_key FROM effects WHERE stable_key=? AND job_id=? AND state='verified'",('external-manifest-push:'+payload['manifest_commit'],job_id))
    if job['state']!='review_wait' and not (job['state']=='complete' and completed_push):
        raise Blocked('external finalization requires review_wait state; complete reentry requires exact verified manifest push; closed/superseded/rejected jobs remain retained')
    reviews=state.rows("SELECT * FROM reviews WHERE job_id=? AND state='accepted'",(job_id,))
    if not reviews or any(file_hash(r['path'])!=r['sha256'] for r in reviews):raise Blocked('accepted external review missing/changed')
    settings=supervisor.learner(job['learner']);main=Git(settings['repo'],supervisor.lock)
    main.clean();main.git('fetch','--no-tags','origin','main')
    ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
    known=payload.get('manifest_commit')
    if ack!=payload['base'] and ack!=known and (not known or known not in main.git('rev-list',ack).splitlines()):
        raise Blocked('external review base must be current acknowledged ack, or previously verified manifest commit ancestor; no skipped range; inspect retained job/current range, and if obsolete use direct-owner close-job after exact assessment and effect reconciliation')
    prior_push=state.rows("SELECT stable_key FROM effects WHERE stable_key=? AND state='verified'",('external-manifest-push:'+str(known),)) if known else []
    if prior_push:
        from types import SimpleNamespace
        candidate=SimpleNamespace(repo=Path(supervisor.job_dir(job)/'manifest-worktree').resolve())
    else:
        candidate=main.worktree(supervisor.job_dir(job)/'manifest-worktree',payload['head'],payload.get('maintenance_git_identity'))
        payload['maintenance_git_identity']=candidate.identity
    payload['manifest_base']=payload['head']
    state.update_job(job_id,payload=payload)
    for name,sha in payload['changes'].items():
        if sha is None or file_hash(candidate.repo/name)!=sha:raise Blocked('external reviewed content changed')
    proposal=payload.get('external_manifest')
    if proposal is None or manifest_with_hashes(candidate.repo,proposal)!=proposal:raise Blocked('external reviewed manifest missing/changed')
    envelope=payload['external_review_envelope']
    if any(file_hash(item['path'])!=item['sha256'] for item in envelope['inputs']) or Renderer.artifacts(payload['external_build'])!=payload['external_artifacts']:
        raise Blocked('external review inputs/rendered artifacts changed')
    review_paths=[r['path'] for r in reviews];manifest_path=settings.get('pilot_manifest','publication/pilot.json')
    tree_hash=digest({'base':payload['head'],'manifest':proposal,'reviews':{r['path']:r['sha256'] for r in reviews}})
    commit_job={**job,'payload':{**payload,'base':payload['manifest_base']}}
    commit_effect=state.effect(job_id,'git-commit',str(candidate.repo),tree_hash,f'external-manifest-commit:{job_id}:{tree_hash}')
    def commit_preflight():
        if main.git('rev-parse','refs/remotes/origin/main')!=payload['head'] or ack!=payload['base']:
            raise Blocked('remote/ack changed before external manifest commit; inspect retained job/current range, and if obsolete use direct-owner close-job after exact assessment and effect reconciliation')
    def commit_execute(effect):
        commit=candidate.commit(commit_job,{},review_paths,supervisor.config['git_identity'],manifest_path,proposal)
        return {'verified':True,'commit':commit,'external_id':commit}
    receipt=state.perform_effect(commit_effect,commit_execute,lambda effect:candidate.reconcile_commit(effect,commit_job,{},review_paths,manifest_path,proposal),commit_preflight)
    commit=receipt['commit'];payload['manifest_commit']=commit;state.update_job(job_id,payload=payload)
    effect=state.effect(job_id,'git-push',settings['repo']+':main',commit,'external-manifest-push:'+commit)
    def push_preflight():
        current_ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
        if current_ack!=payload['base'] or main.inspect(fetch=True)!=payload['head']:raise Blocked('remote/ack changed before external manifest push')
        if candidate.head()!=commit:raise Blocked('external manifest candidate changed before push')
    def execute(effect):
        candidate.git('push','origin','HEAD:refs/heads/main');return main.push_reconcile(effect)
    state.perform_effect(effect,execute,main.push_reconcile,push_preflight)
    if main.head()==payload['head']:main.git('merge','--ff-only',commit)
    current_ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
    if current_ack==payload['base']:
        with state.db:state.db.execute("UPDATE observations SET ack_sha=?,observed_sha=CASE WHEN observed_sha IN (?,?) THEN ? ELSE observed_sha END,state='complete' WHERE id=?",(commit,payload['head'],payload['base'],commit,f"baseline:{job['learner']}"))
    elif current_ack!=commit and commit not in main.git('rev-list',current_ack).splitlines():raise Blocked('verified external push cannot regress/skip current acknowledgement')
    state.update_job(job_id,'complete','done',payload);state.wake_ack_waiters(job['learner'])
    return {'commit':commit,'review':'verified','private_manifest':digest(proposal)}


def command_scope(args,state,config,joined):
    learner=getattr(args,'learner',None)
    job_id=getattr(args,'job_id',None) or getattr(args,'job',None)
    if job_id is not None:
        actual=state.job(job_id)['learner']
        if learner and learner!=actual:raise Blocked('selected job does not belong to requested learner')
        learner=actual
    if hasattr(args,'question_id'):
        rows=state.rows('SELECT j.learner FROM questions q JOIN jobs j ON j.id=q.job_id WHERE q.id=?',(args.question_id,))
        if not rows:raise Blocked('unknown question')
        learner=rows[0]['learner']
    if hasattr(args,'effect_key'):
        rows=state.rows('SELECT j.learner FROM effects e LEFT JOIN jobs j ON j.id=e.job_id WHERE e.stable_key=?',(args.effect_key,))
        if not rows:raise Blocked('unknown effect')
        learner=rows[0]['learner']
        if joined and learner is None:raise Blocked('global effect is not learner-scoped; inspect outside session')
    if joined:
        expected=joined['learner']
        if learner and learner!=expected:raise Blocked('protected session cannot access another learner')
        if args.command in session.AUTHORIZATION:raise Blocked('authorization verb requires explicit owner action outside protected session; model/tool membership is not authority')
        learner=expected
    if learner and learner not in config['learners']:raise Blocked('unknown learner')
    return learner


def build_preview(supervisor,learner):
    settings=supervisor.learner(learner);root=Path(settings['repo']).resolve()
    path=root/settings.get('pilot_manifest','publication/pilot.json')
    if path.is_symlink() or not path.resolve().is_relative_to(root):raise Blocked('preview manifest must be contained ordinary file')
    proposal=json.loads(path.read_text());manifest=manifest_with_hashes(root,proposal)
    if manifest.get('mode')!='private-preview':raise Blocked('build-preview requires contained private-preview manifest')
    # Private owner preview is deliberately separate from job payload build,
    # accepted review and Drive family output. Inputs remain hash-bound.
    directory=private_dir(Path(supervisor.config['jobs_dir'])/('preview-'+str(uuid.uuid4())))
    build,images=Renderer(supervisor.config['renderer'],supervisor.lock,supervisor.window).build(root,manifest,directory)
    if manifest_with_hashes(root,proposal)!=manifest:raise Blocked('preview inputs changed while rendering; artifacts retained without acceptance')
    record={'learner':learner,'manifest_sha256':digest(manifest),'artifacts':Renderer.artifacts(build),'images':images,'build':str(build),'review':False,'origin':'owner-preview'}
    atomic_json(directory/'preview.json',record)
    return {'preview':str(build),'receipt':str(directory/'preview.json'),'review':'unreviewed private owner preview; no publication/upload'}


def main(argv=None):
    args = parser().parse_args(argv)
    state = None
    try:
        config = load(args.config)
        joined=session.verify(config,args.config)
        if args.command=='interactive':
            result=wrapper(config,args.learner,args.argv,config_path=args.config)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.command=='recover' and not joined:session.recover(config)
        if args.command in ('status','inspect-job','inspect-effect','inspect-package','public-proposal'):
            state=State(config['state_db'],readonly=True)
            learner=command_scope(args,state,config,joined)
            supervisor=Supervisor(config,state,None,None)
            if args.command=='status':result=read_status(state,config,learner)
            elif args.command=='inspect-job':result=admin.inspect_job(supervisor,args.job_id)
            elif args.command=='inspect-effect':result=admin.inspect_effect(supervisor,args.effect_key)
            elif args.command=='inspect-package':result=admin.inspect_package(supervisor,args.learner,args.source_id)
            else:result=admin.public_proposal(supervisor,args.job_id)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        with session.Admission(config,args.config) as admission, RunLock(config["lock_file"]) as lock:
            admission.recheck();joined=admission.session
            state = initialize(config, lock) if args.command == "init" else State(config["state_db"])
            learner=command_scope(args,state,config,joined)
            learners=[learner] if learner else list(config['learners'])
            runtime_config=config
            if getattr(args,'max_seconds',None) is not None:
                if not 1<=args.max_seconds<=config.get('run_seconds',3000):raise Blocked('max-seconds may only narrow configured finite window')
                runtime_config=dict(config,run_seconds=args.max_seconds)
            def drive_factory(learner):
                settings = config["learners"][learner]
                return DriveAPI(config["drive_tool"], settings["drive_config_dir"], settings["drive_evidence"], supervisor.window, reader_config=settings.get("drive_reader"))
            supervisor = Supervisor(runtime_config, state, lock, drive_factory)
            supervisor.actor_origin="owner-session" if joined else "direct-vm-admin"
            result = {}
            if args.command == "init":
                for learner in config["learners"]:
                    try:
                        supervisor.observe_drive(learner, baseline=True)
                    except (Blocked, OSError, ValueError, KeyError) as e:
                        supervisor.record_runtime_block(learner, str(e))
                result = supervisor.status()
            elif args.command == "run-once":
                if joined:supervisor.preflight_owner(learners)
                result = scoped_status(supervisor.run_once(learners=learners,job_id=args.job),state,learner)
            elif args.command == "sync":
                result=scoped_status(supervisor.sync(learners),state,learner)
            elif args.command == "build-preview":
                result=build_preview(supervisor,args.learner)
            elif args.command == "recover":
                state.recover(learners=learners if joined else None)
                result = {"recovery": "interrupted effects require reconciliation; no database/ledger replaced"}
            elif args.command == "baseline-inventory":
                if state.meta(f"drive-baseline:{args.learner}") == "complete":
                    raise Blocked("initial baseline already inventoried; will not rebaseline new inputs")
                supervisor.observe_drive(args.learner, baseline=True)
                result = {"baseline": "complete", "learner": args.learner}
            elif args.command == "select-baseline":
                result = {"job_id": state.select_baseline(args.learner, args.source_id)}
            elif args.command == "acknowledge-baseline":
                result=acknowledge_initial_baseline(supervisor,args.learner,args.evidence)
            elif args.command == "answer":
                answer_path = Path(args.file)
                if answer_path.stat().st_size > 1024 * 1024:
                    raise Blocked("answer file exceeds 1 MiB")
                state.answer(args.question_id, answer_path.read_text(), "owner-session" if joined else args.origin)
                result = {"question": args.question_id, "kind": "content", "answer": "recorded"}
            elif args.command == "request-public":
                result=admin.request_public(supervisor,args.job_id,json.loads(Path(args.manifest).read_text()))
            elif args.command == "approve-public":
                state.approve(args.job_id, args.manifest_sha256)
                result = {"job_id": args.job_id, "approved_manifest_sha256": args.manifest_sha256, "origin": "direct-vm-admin"}
            elif args.command == "resume":
                job = state.job(args.job_id)
                if job["state"] not in ("blocked", "review_wait", "retry_wait"):
                    raise Blocked("job is not resumable; resolve its question/authorization first")
                if state.rows("SELECT id FROM questions WHERE job_id=? AND state IN ('open','reconcile_wait')", (args.job_id,)):
                    raise Blocked("open question must be resolved before resume")
                if not state.current(job):
                    raise Blocked("stale candidate requires reconciliation, not resume")
                if job["payload"].get("quota_block"):
                    raise Blocked("quota recovery requires independently verified reset evidence/direct admin decision; resume does not clear quota")
                state.update_job(args.job_id, "queued")
                result = {"job_id": args.job_id, "state": "queued", "attempt_limits": "unchanged"}
            elif args.command == "propose-subject":
                result=admin.propose_subject(supervisor,args.job_id,json.loads(Path(args.file).read_text()))
            elif args.command == "approve-subject":
                result=admin.approve_subject(supervisor,args.job_id,args.proposal_sha256)
            elif args.command == "propose-attempts":
                result=admin.propose_attempts(supervisor,args.job_id,args.phase,args.limit,args.timeout_limit)
            elif args.command == "approve-attempts":
                result=admin.approve_attempts(supervisor,args.job_id,args.proposal_sha256)
            elif args.command == "clear-quota":
                result=admin.clear_quota(supervisor,args.job_id,json.loads(Path(args.file).read_text()))
            elif args.command == "retry-render":
                result=admin.retry_render(supervisor,args.job_id,args.target)
            elif args.command == "reject-package":
                result=admin.reject_package(supervisor,args.job_id,args.reason)
            elif args.command == "reconcile-job":
                result=admin.reconcile_job(supervisor,args.job_id)
            elif args.command == "resume-effects":
                result=admin.resume_effects(supervisor,args.job_id)
            elif args.command == 'inspect-job':
                result=admin.inspect_job(supervisor,args.job_id)
            elif args.command == 'inspect-effect':
                result=admin.inspect_effect(supervisor,args.effect_key)
            elif args.command == 'inspect-package':
                result=admin.inspect_package(supervisor,args.learner,args.source_id)
            elif args.command == 'rebase-candidate':
                result=admin.rebase_candidate(supervisor,args.job_id)
            elif args.command == 'public-proposal':
                result=admin.public_proposal(supervisor,args.job_id)
            elif args.command == 'link-baseline':
                result=admin.link_baseline(supervisor,args.learner,args.source_id,json.loads(Path(args.file).read_text()))
            elif args.command == 'acknowledge-maintenance':
                result=admin.acknowledge_maintenance(supervisor,args.job_id,json.loads(Path(args.file).read_text()))
            elif args.command == 'resolve-effect':
                result=admin.resolve_effect(supervisor,args.effect_key,json.loads(Path(args.file).read_text()))
            elif args.command == 'close-job':
                result=admin.close_job(supervisor,args.job_id,json.loads(Path(args.file).read_text()))
            elif args.command == "finalize-external":
                result = finalize_external(supervisor, args.job_id)
            result['controller_origin']=supervisor.actor_origin
            if args.command=='build-preview':
                print(json.dumps(result,ensure_ascii=False,indent=2));return 0
            try:
                report_path = write_report(scoped_status(supervisor.status(),state,learner), Path(config["reports_dir"])/learner if learner else config["reports_dir"], font_path=config.get('report_font','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                result["report"] = str(report_path)
                state.meta('report-failure','')
            except (Blocked,OSError,ValueError,KeyError) as error:
                result['report_error'] = str(error)
                state.meta('report-failure',str(error))
            if args.command == "run-once":
                result["report_drive"] = {}
                for learner in learners:
                    settings=config["learners"][learner]
                    if not settings.get("status_id"):
                        result["report_drive"][learner] = "blocked: explicit status_id not configured"
                        continue
                    try:
                        archive = Archive(supervisor.drive(learner), state, settings["status_id"], supervisor.window.require)
                        learner_report=write_report(supervisor.status(),Path(config['reports_dir'])/learner,learner,font_path=config.get('report_font','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
                        receipt = archive.upload(None, settings["status_id"], learner_report, "application/pdf", f"status-pdf:{learner}:{file_hash(learner_report)}")
                        result["report_drive"][learner] = receipt
                    except (Blocked, OSError, ValueError, KeyError) as error:
                        result["report_drive"][learner] = "blocked: " + str(error)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
    except Busy as e:
        print(f"school-notes busy: {e}",file=sys.stderr);return 75
    except (Blocked, OSError, ValueError, KeyError) as e:
        print(f"school-notes blocked: {e}", file=sys.stderr)
        return 2
    finally:
        if state:
            state.close()
