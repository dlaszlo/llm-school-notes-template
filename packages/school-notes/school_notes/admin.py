"""Hash-scoped direct-admin recovery; never inferred from model answers."""
import json
import re
import time
from pathlib import Path

from .common import Blocked, atomic_json, canonical, digest, file_hash, now, safe_relative
from .verify import Git, CandidateViolation, OwnerPolicyViolation, manifest_with_hashes, agent_manifest


def request_public(supervisor, source_job_id, manifest):
    state=supervisor.state
    source=state.job(source_job_id)
    if source['state']!='complete' or source['kind'] not in ('ingest','metadata_update','public_release','external_change_review'):
        raise Blocked('a completed reviewed source job is required')
    learner=source['learner']
    settings=supervisor.learner(learner)
    main=Git(settings['repo'],supervisor.lock)
    head=main.inspect(fetch=True)
    baseline=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f'baseline:{learner}',))
    if not baseline or baseline[0]['ack_sha']!=head:
        raise Blocked('current clean HEAD must have closed review acknowledgement')
    proposal=manifest_with_hashes(main.repo,manifest)
    if proposal.get('mode')!='public' or proposal.get('publicationApproved') is not True:
        raise Blocked('public mode and publicationApproved proposal flag required; direct approval still pending')
    key='public-job:'+digest({'learner':learner,'base':head,'manifest':proposal})
    family=state.rows("SELECT id,state,stable_key FROM jobs WHERE stable_key=? OR stable_key LIKE ? ORDER BY id DESC",(key,key+':retry-%'))
    for previous in family:
        if state.rows("SELECT stable_key FROM effects WHERE job_id=? AND state IN ('unknown','inflight')",(previous['id'],)):
            raise Blocked('previous public family effects remain unknown; resume-effects before a fresh proposal')
    retryable=('blocked','rejected','reconciled','superseded','closed_unprocessed')
    active=next((previous for previous in family if previous['state'] not in retryable),None)
    if active:
        return {'job_id':active['id'],'state':active['state'],'next':'continue existing preview/review/approval job; repeated request is idempotent'}
    if family:
        key+=':retry-'+str(len(family)+1)
    job_id=state.enqueue('public_release',learner,key,{'base':head,'public_manifest':proposal,'source_job_id':source_job_id})
    job=state.job(job_id)
    if job['state']=='queued':
        state.update_job(job_id,phase='public_prepare')
    return {'job_id':job_id,'state':state.job(job_id)['state'],'next':'run-once builds and reviews concrete preview before approve-public'}


def propose_subject(supervisor, job_id, proposal):
    job=supervisor.state.job(job_id)
    if job['state']!='approval_wait' or not supervisor.state.current(job):
        raise Blocked('current new-subject approval_wait job required')
    if not isinstance(proposal,dict) or set(proposal)-{'tools/subjects.json','tools/book-index.json'} or 'tools/subjects.json' not in proposal:
        raise Blocked('only explicit learner subjects/book-index JSON configurations are supported')
    repo=Path(job['payload']['worktree'])
    subjects=proposal['tools/subjects.json']
    old=json.loads((repo/'tools/subjects.json').read_text())
    if set(subjects)!={'labels','subjects'} or subjects['labels']!=old.get('labels') or not isinstance(subjects['subjects'],dict):
        raise Blocked('subject config must preserve labels and contain a subjects mapping')
    if any(subjects['subjects'].get(k)!=v for k,v in old.get('subjects',{}).items()):
        raise Blocked('existing subject configurations cannot change in an addition')
    new=set(subjects['subjects'])-set(old.get('subjects',{}))
    for slug in new:
        item=subjects['subjects'][slug]
        if (not re.fullmatch('[a-z0-9_-]+',slug) or not isinstance(item,dict) or set(item)-{'name','emoji','dark','light','icon','mark','doodles'}
            or not {'name','emoji','dark','light','icon'}<=item.keys() or any(not isinstance(item[k],str) or not item[k] for k in ('name','emoji','dark','light','icon'))
            or any(not re.fullmatch('#[a-fA-F0-9]{6}',item[k]) for k in ('dark','light'))
            or item['icon'] not in ('bubble','book','column','coins','flask','briefcase','math','globe','pencil')
            or ('doodles' in item and (not isinstance(item['doodles'],list) or not all(isinstance(v,str) for v in item['doodles'])))):
            raise Blocked('invalid subject schema')
    requested=set(job['payload'].get('new_subjects',[]))
    if not new or new!=requested:
        raise Blocked('proposal must configure exactly the retained new subjects')
    if 'tools/book-index.json' in proposal:
        book=proposal['tools/book-index.json']
        prior=json.loads((repo/'tools/book-index.json').read_text())
        if set(book)!={'labels'} or set(book['labels'])!=set(prior.get('labels',{})) or not all(isinstance(v,str) and v for v in book['labels'].values()):
            raise Blocked('invalid book-index label schema')
    frozen={'base':job['payload']['base'],'subjects':sorted(new),'files':proposal}
    job['payload']['new_subject_manifest']=frozen
    supervisor.state.update_job(job_id,payload=job['payload'])
    sha=digest(frozen)
    supervisor.state.question(job_id,'authorization','new_subject','Approve exact new-subject learner configuration',sha)
    atomic_json(supervisor.job_dir(job)/'new-subject-proposal.json',frozen)
    return {'job_id':job_id,'proposal_sha256':sha}


def approve_subject(supervisor,job_id,sha):
    state=supervisor.state
    state.approve(job_id,sha,'new_subject')
    job=state.job(job_id)
    # Close the preliminary notice, which did not yet have concrete config.
    with state.db:
        state.db.execute("UPDATE questions SET state='closed',origin='direct-vm-admin' WHERE job_id=? AND kind='authorization' AND scope='new-subject'",(job_id,))
    job['payload']['approved_subject_config']=job['payload']['new_subject_manifest']
    state.update_job(job_id,'queued','candidate',job['payload'])
    return {'job_id':job_id,'configuration':'approved exact JSON; supervisor applies, then full candidate/review gates'}


def propose_attempts(supervisor,job_id,phase,limit,timeout_limit):
    job=supervisor.state.job(job_id)
    if not supervisor.state.current(job) or not re.fullmatch('[a-z_]+(?::[a-f0-9]{16})?',phase) or not 3<=limit<=10 or not 2<=timeout_limit<=5:
        raise Blocked('invalid bounded phase exception')
    proposal={'revision_seq':job['revision_seq'],'phase':phase,'limit':limit,'timeout_limit':timeout_limit,
              'attempts':supervisor.state.rows('SELECT id,state,result_hash FROM attempts WHERE job_id=? AND phase=? ORDER BY id',(job_id,phase))}
    job['payload']['attempt_manifest']=proposal
    supervisor.state.update_job(job_id,payload=job['payload'])
    sha=digest(proposal)
    supervisor.state.question(job_id,'authorization','attempt','Approve bounded exact-phase attempt exception',sha)
    return {'job_id':job_id,'proposal_sha256':sha}


def approve_attempts(supervisor,job_id,sha):
    state=supervisor.state
    state.approve(job_id,sha,'attempt')
    job=state.job(job_id)
    proposal=job['payload']['attempt_manifest']
    actual=state.rows('SELECT id,state,result_hash FROM attempts WHERE job_id=? AND phase=? ORDER BY id',(job_id,proposal['phase']))
    if actual!=proposal['attempts']:
        raise Blocked('attempt history changed after proposal')
    job['payload'].setdefault('attempt_exceptions',{})[proposal['phase']]=proposal
    state.update_job(job_id,'queued',payload=job['payload'])
    return {'job_id':job_id,'exception':proposal['phase']}


def clear_quota(supervisor,job_id,evidence):
    job=supervisor.state.job(job_id)
    if not job['payload'].get('quota_block') or evidence.get('job_id')!=job_id or evidence.get('revision_seq')!=job['revision_seq'] or not evidence.get('reason') or evidence.get('reset_epoch',float('inf'))>time.time():
        raise Blocked('direct admin reset evidence must bind current job/revision and elapsed reset epoch')
    job['payload']['quota_reset']={'evidence':evidence,'origin':'direct-vm-admin','sha256':digest(evidence)}
    job['payload']['quota_block']=False
    supervisor.state.update_job(job_id,'queued',payload=job['payload'])
    return {'job_id':job_id,'quota':'direct admin reset recorded; attempts unchanged'}


def retry_render(supervisor,job_id,target):
    job=supervisor.state.job(job_id)
    if not supervisor.state.current(job) or target not in ('source','private','public','prepare','external'):
        raise Blocked('current job and explicit retry target required')
    payload=job['payload']
    key={'source':'source_render_extra','private':'render_attempt','public':'public_render_extra','prepare':'prepare_attempt','external':'external_render_extra'}[target]
    amount=payload.get(key,0)+1
    if amount>5:
        raise Blocked('finite admin render/prepare retry limit reached; reject or reconcile package')
    payload[key]=amount
    phase={'source':'capture','prepare':'capture','private':'render','public':'public_prepare','external':'external_review'}[target]
    supervisor.state.update_job(job_id,'queued',phase,payload)
    return {'job_id':job_id,'target':target,'attempt':amount,'retained':'previous files preserved'}


def reject_package(supervisor,job_id,reason):
    job=supervisor.state.job(job_id)
    if not reason.strip() or not job['package_id']:
        raise Blocked('package job and reason required')
    if supervisor.state.rows("SELECT stable_key FROM effects WHERE job_id=? AND state IN ('unknown','inflight')",(job_id,)):
        raise Blocked('unknown effects must be reconciled before closing package')
    with supervisor.state.db:
        supervisor.state.db.execute("UPDATE packages SET state='rejected' WHERE id=?",(job['package_id'],))
        supervisor.state.db.execute("UPDATE jobs SET state='rejected',phase='done' WHERE package_id=? AND state NOT IN ('complete','rejected','reconciled','superseded')",(job['package_id'],))
        supervisor.state.db.execute("UPDATE questions SET state='closed',origin='direct-vm-admin' WHERE job_id IN (SELECT id FROM jobs WHERE package_id=?) AND state IN ('open','reconcile_wait','stale')",(job['package_id'],))
    job['payload']['rejection']={'reason':reason,'origin':'direct-vm-admin'}
    supervisor.state.update_job(job_id,'rejected','done',job['payload'])
    return {'job_id':job_id,'state':'rejected','preservation':'captures, candidates and receipts retained'}


def reconcile_job(supervisor,job_id):
    old=supervisor.state.job(job_id)
    if not old['package_id'] or supervisor.state.current(old):
        raise Blocked('stale package job required')
    if supervisor.state.rows("SELECT stable_key FROM effects WHERE job_id=? AND kind IN ('git-push','git-commit') AND state IN ('unknown','inflight')",(job_id,)):
        raise Blocked('reconcile unknown Git effects first by resume-effects; no stale source writes')
    rows=supervisor.state.rows('SELECT id FROM jobs WHERE package_id=? AND revision_seq=(SELECT current_seq FROM packages WHERE id=?) AND kind IN (\'ingest\',\'metadata_update\')',(old['package_id'],old['package_id']))
    if len(rows)!=1:
        raise Blocked('current revision job missing; inventory/select current baseline first')
    target=supervisor.state.job(rows[0]['id'])
    if target['state'] not in ('queued','blocked','retry_wait','ack_wait','question_wait','approval_wait','review_wait'):
        raise Blocked('current revision is not an eligible waiting/blocked reconciliation target')
    target['payload']['reconciled_from']={'job_id':job_id,'candidate':old['payload'].get('worktree'),'answers':supervisor.state.rows('SELECT scope,answer,origin,answer_hash FROM questions WHERE job_id=? AND answer IS NOT NULL',(job_id,))}
    # Old answers are evidence to re-evaluate, never automatic authorization.
    supervisor.state.update_job(target['id'],target['state'] if target['state'] in ('question_wait','approval_wait','ack_wait') else 'queued',payload=target['payload'])
    with supervisor.state.db:
        supervisor.state.db.execute("UPDATE questions SET state='closed',origin='direct-vm-admin' WHERE job_id=? AND state IN ('open','reconcile_wait','stale')",(job_id,))
    supervisor.state.update_job(job_id,'reconciled',payload=old['payload'])
    return {'old_job_id':job_id,'job_id':target['id'],'review':'new revision fully reclassified and reviewed; old work retained'}


def resume_effects(supervisor,job_id):
    """Read-only reconciliation precedes stale-source gates and new writes."""
    state=supervisor.state
    job=state.job(job_id)
    unknown=state.rows("SELECT * FROM effects WHERE job_id=? AND state IN ('unknown','inflight')",(job_id,))
    if not unknown:
        raise Blocked('no interrupted effects awaiting reconciliation')
    for effect in unknown:
        receipt=None
        if effect['kind']=='git-push':
            receipt=Git(supervisor.learner(job['learner'])['repo'],supervisor.lock).push_reconcile(effect)
        elif effect['kind']=='git-commit' and job['payload'].get('worktree') and job['payload'].get('private_manifest'):
            payload=job['payload']
            paths=sorted(set(payload.get('source_review_paths',[payload['source_review']])+payload.get('visual_review_paths',[payload['visual_review']])+[payload['candidate_result']]))
            receipt=Git(payload['worktree'],supervisor.lock,payload.get('git_identity')).reconcile_commit(effect,job,payload['changes'],paths,supervisor.learner(job['learner']).get('pilot_manifest','publication/pilot.json'),payload['private_manifest'])
            if receipt and receipt.get('verified') is True:
                payload['commit']=receipt['commit']
                state.update_job(job_id,phase='push',payload=payload)
        elif effect['kind'] in ('drive-upload','drive-folder'):
            receipt=supervisor.drive(job['learner']).reconcile(effect,folder=effect['kind']=='drive-folder')
        if receipt and receipt.get('verified') is True:
            state.effect_state(effect['stable_key'],'verified',receipt,receipt.get('external_id'))
        elif receipt and receipt.get('absent') is True:
            state.effect_state(effect['stable_key'],'planned',{'reconciliation':receipt,'previous_receipt':json.loads(effect['receipt']) if effect['receipt'] else None})
    current=state.job(job_id)
    may_finish_push=current['phase'] in ('push','family_output') and bool(state.rows("SELECT stable_key FROM effects WHERE job_id=? AND kind='git-push' AND state='verified'",(job_id,)))
    if not state.current(current) and not may_finish_push:
        state.update_job(job_id,'blocked',error='stale effects reconciled read-only; reconcile-job selects current source before any new write')
    else:
        state.update_job(job_id,'queued')
    return {'job_id':job_id,'state':state.job(job_id)['state'],'reconciliation':'read-only first; unknown outcomes never imply a repeat'}


def _records(evidence):
    records=evidence.get('closure_records')
    if not isinstance(records,list) or not records:
        raise Blocked('nonempty exact-hash closure_records required')
    for record in records:
        if set(record)!={'path','sha256'} or not Path(record['path']).is_absolute() or file_hash(record['path'])!=record['sha256']:
            raise Blocked('closure record changed or malformed')
    return records


def ordinary_snapshot(root):
    root=Path(root).resolve();ordinary={};opaque=[]
    for path in root.rglob('*'):
        relative=str(path.relative_to(root))
        if not path.is_file() or path.is_symlink() or '.git' in path.relative_to(root).parts or not path.resolve().is_relative_to(root):continue
        sha=file_hash(path)
        try:relative.encode('utf-8')
        except UnicodeEncodeError:
            opaque.append({'relative_fs_bytes_hex':__import__('os').fsencode(relative).hex(),'sha256':sha,'size':path.stat().st_size,'mode':path.stat().st_mode & 0o777})
        else:ordinary[relative]=sha
    return ordinary,opaque


def rebase_candidate(supervisor,job_id):
    state=supervisor.state
    job=state.job(job_id)
    if job['kind'] not in ('ingest','metadata_update') or not state.current(job) or not job['payload'].get('worktree'):
        raise Blocked('current retained package candidate required')
    git_effects=state.rows("SELECT * FROM effects WHERE job_id=? AND kind IN ('git-commit','git-push')",(job_id,))
    if any(e['state'] not in ('planned','verified') or (e['kind']=='git-push' and e['state']=='verified') for e in git_effects):
        raise Blocked('candidate has interrupted/verified push effects; resume-effects/finish or close before rebase')
    main=Git(supervisor.learner(job['learner'])['repo'],supervisor.lock)
    head=main.inspect(fetch=True)
    baseline=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))
    if not baseline or baseline[0]['ack_sha']!=head :
        raise Blocked('new clean acknowledged HEAD required')
    old=job['payload']
    actor=getattr(supervisor,'actor_origin','direct-vm-admin')
    failure=old.get('owner_policy_failure')
    if failure:
        # Current pinned main policy decides before any old candidate Git,
        # metadata-drift snapshot or retry allocation. Sources alone cannot
        # prove an inherited wiki/docs filter was repaired.
        if failure.get('path'):
            main.source_attributes(str(safe_relative(failure['path'])))
        elif head==old['base']:
            raise Blocked('owner policy repair lacks exact failing path; acknowledge-maintenance before rebase-candidate; no rebase budget consumed')
        for name in main.ordinary_changed_paths(old['worktree'],old['base']):
            main.source_attributes(name)
    # Test current acknowledged owner attributes using immutable captured
    # bytes, not potentially altered agent copies, before allocating a retry.
    for source in old.get('git_sources',[]):
        name=str(Path(source['path']).relative_to(Path(old['worktree'])))
        bound=next((f['read_source'] for f in old.get('manifest',{}).get('files',[]) if f.get('prepared_sha256',f['sha256'])==source['sha256']),source['path'])
        if file_hash(bound)!=source['sha256']:raise Blocked('immutable source evidence changed; reconcile before owner-policy rebase')
        main.source_policy(name,bound)
    owner_repaired=bool(old.get('owner_policy_failure') and old.get('git_sources'))
    if old.get('owner_policy_failure') and head==old['base'] and not owner_repaired:
        raise Blocked('owner policy repair lacks exact immutable source preflight; no rebase budget consumed')
    local_commit=old.get('commit')
    if local_commit:
        absence=main.push_reconcile({'artifact_hash':local_commit,'target':supervisor.learner(job['learner'])['repo']+':main'})
        if not absence or absence.get('absent') is not True:raise Blocked('old local commit is remote/unknown; finish/reconcile existing push before rebase')
    opaque=[]
    drift={'origin':actor+'-repaired-owner-policy-rebase','prior_failure':old['owner_policy_failure'],'immutable_source_policy_preflight':'passed'} if owner_repaired else None
    try:
        candidate=Git(old['worktree'],supervisor.lock,old.get('git_identity'))
    except Blocked as error:
        # Direct-admin rebase never executes old Git after identity drift.
        # Preserve an ordinary-file snapshot and record the mismatch instead.
        drift={'error':str(error),'expected_identity':old.get('git_identity'),'origin':actor+'-rebase'}
        root=Path(old['worktree']).resolve()
        changes,opaque=ordinary_snapshot(root)
    else:
        if local_commit:
            verified=[e for e in git_effects if e['kind']=='git-commit' and e['state']=='verified' and e['receipt'] and json.loads(e['receipt']).get('commit')==local_commit]
            paths=sorted(set(old.get('source_review_paths',[old['source_review']])+old.get('visual_review_paths',[old['visual_review']])+[old['candidate_result']]))
            if len(verified)!=1 or candidate.reconcile_commit(verified[0],job,old['changes'],paths,supervisor.learner(job['learner']).get('pilot_manifest','publication/pilot.json'),old['private_manifest']).get('verified') is not True:
                raise Blocked('verified local commit no longer matches retained reviewed artifact')
            changes=dict(old['changes'])
        else:
            try:
                changes=candidate.changes(old['base'],old.get('supervisor_config_paths',{}),old.get('git_sources',[]))
                if 'agent_manifest_proposal' in old:
                    existing=json.loads((main.repo/supervisor.learner(job['learner']).get('pilot_manifest','publication/pilot.json')).read_text())
                    agent_manifest(candidate.repo,existing,old['agent_manifest_proposal'])
            except OwnerPolicyViolation as error:
                if head==old['base']:
                    raise Blocked('unchanged owner policy failure at '+str(error.path)+': owner maintenance, observe external range, acknowledge-maintenance, then rebase-candidate; no rebase budget consumed') from None
                root=Path(old['worktree']).resolve()
                changes,opaque=ordinary_snapshot(root)
                drift={'error':str(error),'origin':actor+'-owner-policy-maintenance-rebase','snapshot':'ordinary-files-only'}
            except CandidateViolation as error:
                # The direct admin renews the candidate against acknowledged
                # owner maintenance. Preserve every old ordinary file; never
                # run another agent over or delete the blocked old outputs.
                root=Path(old['worktree']).resolve()
                changes,opaque=ordinary_snapshot(root)
                drift={'error':str(error),'origin':actor+'-candidate-violation-rebase','snapshot':'ordinary-files-only'}
    retained={'actor_origin':actor,'base':old['base'],'candidate':old['worktree'],'commit':local_commit,'git_effects':git_effects,'changes':changes,'opaque_files':opaque,'metadata_drift':drift,'owner_policy_failure':old.get('owner_policy_failure'),'agent_manifest_proposal':old.get('agent_manifest_proposal'),'candidate_result':old.get('candidate_result'),'invalid_manifest_attempt':old.get('invalid_manifest_attempt'),
              'answers':state.rows('SELECT scope,answer,origin,answer_hash FROM questions WHERE job_id=? AND answer IS NOT NULL',(job_id,)),
              'reviews':state.rows('SELECT path,sha256,state FROM reviews WHERE job_id=?',(job_id,))}
    if head==old['base'] and drift is None:
        raise Blocked('changed acknowledged HEAD or explicit metadata drift required')
    if len(old.get('candidate_history',[]))>=5:
        raise Blocked('finite candidate rebase limit reached; close or manual maintenance required')
    history=old.get('candidate_history',[])+[retained]
    keep={'manifest','previous','classification','classification_result','archive_receipts','source_context','attempt_exceptions','quota_block','quota_reset','owner_policy_recoveries','owner_supervised'}
    payload={key:value for key,value in old.items() if key in keep}
    payload.update(candidate_history=history,reconciled_from=retained,worktree_name=f'worktree-rebase-{len(history)}',base=head,fix_round=0)
    # Encode before any transition; one transaction preserves all approvals
    # on serialization/SQL failure, including byte-faithful opaque snapshots.
    encoded=canonical(payload).decode()
    next_state='retry_wait' if payload.get('quota_block') else 'queued'
    with state.db:
        state.db.execute("UPDATE reviews SET state='invalidated' WHERE job_id=?",(job_id,))
        state.db.execute("UPDATE questions SET state='closed',origin=? WHERE job_id=? AND kind='authorization' AND state IN ('open','approved')",(actor+'-rebase',job_id))
        state.db.execute("UPDATE jobs SET state=?,phase='candidate',payload=?,error=?,updated=? WHERE id=?",(next_state,encoded,'provider quota block: verified direct-admin reset required' if payload.get('quota_block') else None,now(),job_id))
    return {'job_id':job_id,'base':head,'retained_candidate':retained['candidate'],'review':'all candidate approvals and reviews renewed'}


def acknowledge_maintenance(supervisor,job_id,evidence):
    state=supervisor.state; job=state.job(job_id)
    if job['kind'] not in ('external_change_review','divergence_maintenance'):
        raise Blocked('external maintenance review or observer-only divergence job required')
    main=Git(supervisor.learner(job['learner'])['repo'],supervisor.lock)
    head=main.inspect(fetch=True)
    ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f"baseline:{job['learner']}",))[0]['ack_sha']
    if evidence.get('job_id')!=job_id or evidence.get('base')!=ack or evidence.get('head')!=head or job['payload']['base']!=ack or job['payload']['head']!=head or evidence.get('changes')!=job['payload']['changes']:
        raise Blocked('maintenance evidence must bind entire acknowledged-base/current-HEAD range')
    actual=main.committed_changes(ack,head)
    if job['kind']=='divergence_maintenance':
        if ack in main.git('rev-list',head).splitlines() or job['payload'].get('observer_only') is not True or 'merge_base' not in evidence or evidence['merge_base']!=job['payload']['merge_base'] or evidence['merge_base']!=main.merge_base(ack,head):
            raise Blocked('divergence maintenance requires exact observer-bound acknowledged endpoints and merge_base; no model closure')
    if actual!=evidence['changes'] or evidence.get('open_reviews')!=[] or evidence.get('open_questions')!=[] or not evidence.get('reason'):
        raise Blocked('maintenance exact changes and explicit closed review/questions required')
    records=_records(evidence)
    path=supervisor.learner(job['learner']).get('pilot_manifest','publication/pilot.json')
    manifest=json.loads((main.repo/path).read_text())
    impact={'path':path,'sha256':file_hash(main.repo/path),'manifest':manifest}
    if manifest.get('mode')!='private-preview' or evidence.get('manifest_impact')!=impact or manifest_with_hashes(main.repo,manifest)!=manifest:
        raise Blocked('maintenance requires exact valid current manifest impact')
    job['payload']['maintenance_closure']={'origin':'direct-vm-admin','evidence':evidence,'sha256':digest(evidence),'records':records}
    state.update_job(job_id,'complete','done',job['payload'])
    with state.db:
        state.db.execute("UPDATE observations SET observed_sha=?,ack_sha=?,state='complete' WHERE id=?",(head,head,f"baseline:{job['learner']}"))
    state.wake_ack_waiters(job['learner'])
    return {'job_id':job_id,'ack_sha':head,'closure':'direct admin maintenance; retained evidence is not a model review'}


def link_baseline(supervisor,learner,source_id,evidence):
    state=supervisor.state
    rows=state.rows('SELECT p.*,r.manifest,r.bytes_hash,r.metadata_hash FROM packages p JOIN revisions r ON r.package_id=p.id AND r.seq=p.current_seq WHERE p.learner=? AND p.source_id=?',(learner,source_id))
    if len(rows)!=1 or rows[0]['state']!='baseline_pending':
        raise Blocked('current unprocessed baseline package required')
    row=rows[0]; manifest=json.loads(row['manifest'])
    if any(file_hash(f['local'])!=f['sha256'] for f in manifest['files']):
        raise Blocked('baseline captured original bytes changed or missing')
    expected={'learner':learner,'source_id':source_id,'revision_seq':row['current_seq'],'bytes_hash':row['bytes_hash'],'metadata_hash':row['metadata_hash'],
              'files':{f['id']:f['sha256'] for f in manifest['files']}}
    if any(evidence.get(k)!=v for k,v in expected.items()) or evidence.get('open_reviews')!=[] or evidence.get('open_questions')!=[]:
        raise Blocked('baseline link must bind current full package and closed review/questions')
    _records(evidence)
    main=Git(supervisor.learner(learner)['repo'],supervisor.lock); head=main.inspect(fetch=True)
    ack=state.rows('SELECT ack_sha FROM observations WHERE id=?',(f'baseline:{learner}',))[0]['ack_sha']
    summary=evidence.get('source_summary',{})
    name=summary.get('path','')
    target=main.repo/safe_relative(name)
    if evidence.get('head')!=head or ack!=head or not name.startswith('wiki/') or target.is_symlink() or not target.resolve().is_relative_to(main.repo) or file_hash(target)!=summary.get('sha256'):
        raise Blocked('baseline link needs exact acknowledged HEAD and Source summary hash')
    text=(main.repo/name).read_text()
    bindings=evidence.get('source_bindings')
    if bindings is None:
        if not all(f['sha256'] in text for f in manifest['files']):
            raise Blocked('Source summary must cover every original SHA or exact owner-bound original/read-source projection')
    else:
        if not evidence.get('reason') or not isinstance(bindings,list) or not all(isinstance(b,dict) for b in bindings) or len(bindings)!=len(manifest['files']) or {b.get('file_id') for b in bindings}!={f['id'] for f in manifest['files']}:
            raise Blocked('baseline projection must cover every original once, with explicit owner reason')
        originals={f['id']:f['sha256'] for f in manifest['files']}
        for binding in bindings:
            if set(binding)!={'file_id','original_sha256','read_source'} or binding['original_sha256']!=originals[binding['file_id']]:
                raise Blocked('baseline original projection identity mismatch')
            source=binding['read_source'];name=source.get('path','')
            target=main.repo/safe_relative(name)
            if set(source)!={'path','sha256'} or not name.startswith('sources/') or target.is_symlink() or not target.resolve().is_relative_to(main.repo) or file_hash(target)!=source['sha256'] or source['sha256'] not in text or name not in text:
                raise Blocked('baseline read source needs exact existing bytes plus explicit Source-summary path/hash link')
    job_id=state.enqueue('baseline_link',learner,f"baseline-link:{learner}:{source_id}:{row['current_seq']}",{'manifest':manifest,'closure':evidence,'closure_sha256':digest(evidence),'origin':'direct-vm-admin'},row['id'],row['current_seq'])
    state.update_job(job_id,'complete','done')
    with state.db:state.db.execute("UPDATE packages SET state='processed' WHERE id=?",(row['id'],))
    return {'job_id':job_id,'state':'processed','basis':'exact direct-admin baseline closure; no synthetic model acceptance'}


def public_proposal(supervisor,job_id):
    job=supervisor.state.job(job_id); proposal=job['payload'].get('public_proposal')
    if not proposal:raise Blocked('concrete reviewed public proposal not prepared')
    return {'job_id':job_id,'proposal_sha256':digest(proposal),'proposal':proposal}


def resolve_effect(supervisor,key,evidence):
    state=supervisor.state; rows=state.rows('SELECT * FROM effects WHERE stable_key=?',(key,))
    if len(rows)!=1 or rows[0]['state'] not in ('unknown','inflight'):
        raise Blocked('interrupted exact effect required')
    effect=rows[0]; job=state.job(effect['job_id']) if effect['job_id'] else None
    binding={k:effect[k] for k in ('stable_key','job_id','kind','target','artifact_hash','external_id','receipt')}
    if evidence.get('effect')!=binding or evidence.get('observed_effect_sha256')!=digest(effect) or not evidence.get('reason') or evidence.get('decision') not in ('verified','verified_absent','closed'):
        raise Blocked('direct admin decision must bind exact unchanged effect including its last receipt')
    if evidence.get('source_head')!=(job['payload'].get('base') if job else None):
        raise Blocked('effect source HEAD binding differs')
    _records(evidence)
    receipt={'origin':'direct-vm-admin','evidence':evidence,'sha256':digest(evidence),'previous_receipt':effect['receipt']}
    decision=evidence['decision']
    if decision=='verified':
        if not evidence.get('external_id'):raise Blocked('verified exact external identity required')
        receipt.update(verified=True,external_id=evidence['external_id'],target=effect['target'],artifact_hash=effect['artifact_hash'])
        state.effect_state(key,'verified',receipt,evidence['external_id'])
    else:
        receipt['absent']=decision=='verified_absent'
        state.effect_state(key,'planned' if decision=='verified_absent' else 'admin_closed',receipt)
    return {'effect':key,'decision':decision,'repeat':'one new durable attempt only after explicit verified absence; interrupted outcomes require new evidence'}


def close_job(supervisor,job_id,evidence):
    state=supervisor.state;job=state.job(job_id)
    if job['state']=='complete' or evidence.get('job_id')!=job_id or evidence.get('revision_seq')!=job['revision_seq'] or evidence.get('base')!=job['payload'].get('base') or evidence.get('payload_sha256')!=digest(job['payload']) or not evidence.get('reason'):
        raise Blocked('closure must bind current uncompleted job payload/revision/base')
    if state.rows("SELECT stable_key FROM effects WHERE job_id=? AND state IN ('unknown','inflight')",(job_id,)):
        raise Blocked('resolve each interrupted exact effect before closing job')
    _records(evidence)
    job['payload']['manual_closure']={'origin':'direct-vm-admin','evidence':evidence,'sha256':digest(evidence),'outcome':'closed_unprocessed'}
    with state.db:state.db.execute("UPDATE questions SET state='closed',origin='direct-vm-admin' WHERE job_id=? AND state IN ('open','reconcile_wait','stale')",(job_id,))
    state.update_job(job_id,'closed_unprocessed','done',job['payload'])
    return {'job_id':job_id,'state':'closed_unprocessed','preservation':'all captures, candidate bytes, reviews, questions and effect receipts retained; no accepted-learning claim'}


def inspect_job(supervisor,job_id):
    job=supervisor.state.job(job_id)
    return {'job':job,'payload_sha256':digest(job['payload']),
            'questions':supervisor.state.rows('SELECT * FROM questions WHERE job_id=?',(job_id,)),
            'reviews':supervisor.state.rows('SELECT * FROM reviews WHERE job_id=?',(job_id,)),
            'attempts':supervisor.state.rows('SELECT * FROM attempts WHERE job_id=? ORDER BY id',(job_id,))}


def inspect_effect(supervisor,key):
    rows=supervisor.state.rows('SELECT * FROM effects WHERE stable_key=?',(key,))
    if len(rows)!=1:raise Blocked('unknown effect key')
    effect=rows[0];job=supervisor.state.job(effect['job_id']) if effect['job_id'] else None
    return {'effect':effect,'observed_effect_sha256':digest(effect),'source_head':job['payload'].get('base') if job else None,
            'binding':{k:effect[k] for k in ('stable_key','job_id','kind','target','artifact_hash','external_id','receipt')}}


def inspect_package(supervisor,learner,source_id):
    rows=supervisor.state.rows('SELECT p.*,r.bytes_hash,r.metadata_hash,r.manifest FROM packages p JOIN revisions r ON r.package_id=p.id AND r.seq=p.current_seq WHERE p.learner=? AND p.source_id=?',(learner,source_id))
    if len(rows)!=1:raise Blocked('captured current package required')
    row=rows[0];manifest=json.loads(row.pop('manifest'))
    return {'package':row,'manifest':manifest,'binding':{'learner':learner,'source_id':source_id,'revision_seq':row['current_seq'],'bytes_hash':row['bytes_hash'],'metadata_hash':row['metadata_hash'],'files':{f['id']:f['sha256'] for f in manifest['files']}}}
