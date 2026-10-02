# School Notes V1 application

This is a finite Python supervisor for existing private learner repositories.
It does not initialize the template's PROFILE or wiki, create credentials,
change Drive sharing, choose a replacement model, or enable paid images.
Normal operations use one inherited operation flock and one heavy child at a time.
An optional protected owner session holds a separate session guard.

Run from the already prepared Python environment, with no install/sync during
daily work:

    PYTHONPATH=/srv/school-notes/template/packages/school-notes \
      UV_OFFLINE=1 /srv/school-notes/template/.venv/bin/python -B -m school_notes \
      --config /srv/school-notes/ops/config/app-v1.json status

The package also defines a school-notes console entry point for a separately
authorized installation. All executable, renderer, runtime, config, ledger and
storage paths are explicit. The example config is intentionally unready.
It contains no credentials and refuses its placeholder Git identity.

## Initial state and ready folders

The admin runs init once. Before creating a DB it verifies the configured initial SHA against the clean actual HEAD and origin/main. It uses exclusive DB creation, foreign keys,
synchronous=FULL, schema version 1 and an integrity check. Existing or corrupt
state is never replaced. Baseline observed_sha does not imply acknowledged
history. Set baseline_closure to a private evidence file, or later use
acknowledge-baseline LEARNER EVIDENCE.json. Its exact schema is:

    {
      "observed_sha": "<verified 40-character initial main SHA>",
      "ack_sha": "<the same SHA>",
      "open_reviews": [],
      "open_questions": [],
      "closure_records": [{"path": "/absolute/private/closure.json", "sha256": "<64 hex>"}]
    }

The records must document closure, including review/question disposition.
Unclosed historical ranges remain visible blockers; no full-history ingest is
started. init inventories existing Drive inputs as baseline_pending, without
starting agents. select-baseline LEARNER PACKAGE_ID explicitly chooses an
existing unprocessed package. New packages appearing after the completed
initial inventory become normal jobs. Failed initial inventory is recovered
with baseline-inventory LEARNER; this cannot rebaseline an already completed
learner. recover preserves interrupted phases and makes inflight effects
unknown; it never recreates a DB or an executor ledger.

Configure every ready root explicitly, for example
01-Beérkezett/Füzet/math/Kész and each teacher role/subject Kész.
inputs is a list of {ready_id, subject_slug, source_role}, where source_role is
notebook or teacher_learn. teacher_background roots are rejected before any
adapter runs; local reference material remains outside V1 ingest. The app reads only these roots,
never their parent or a Feltöltés folder. Each complete package is a child
folder under Kész; preserve numbered nested filenames inside it. Loose files
under Kész are individual visible package blockers. One empty, unsupported,
changed or oversized package preserves its inventory/staging and does not
prevent other complete packages or initial inventory closure. Subject/role folder context is not source
classification evidence.

All configured roots and recursive pages must finish before an observation
is complete. A failed/partial listing is never an empty folder. A token
invalidation restarts the whole survey once. Each package additionally has
before/download/after inventories. Source movement or disappearance never
deletes local content, a question or a note. Later changes block finalization.
Binary PNG/JPEG/PDF are supported by MIME, extension and signature. Raw
PPTX/DOCX, Google-native files and HEIC currently block as preserved sources:
use a supported PDF/image conversion while retaining the original outside
this V1 ingest path. A package mixing supported conversions and opaque originals
needs a proven exact-byte conversion adapter before it can be ingested as one
package; PDF support alone does not prove that adapter.

Unchanged captures reuse verified local source bytes and their immutable capture
receipt. A complete matching before/after inventory creates no new capture
directory, progress receipt or prepared copy. Matching Drive binary
MD5/size allows metadata-only capture reuse; local SHA-256 is still checked.
Every downloaded or reused original must also match current Drive size and,
when supplied, MD5 before it enters reusable progress. A failed transfer remains
private in its original staging; a later observation downloads fresh bytes.
Integrity-verified unsupported signatures remain recorded only to preserve the
same blocker, and cannot reach classification or archive.
Metadata-only changes create their own monotonic revision/job against the
latest completed, same-byte ingest/metadata revision. An unprocessed or
superseded ingest stays a full ingest; a baseline_pending package stays pending
until explicit selection. This prevents a Description edit from bypassing init. A→B→A gets three observed sequence numbers. A name-only change keeping
reading order is a location update; reordered filenames trigger review.
Source-author, target learner and purpose are separate. The classification
stage reads actual source content and optional Description as private evidence.
Its bounded sanitized context records author=learner/other/teacher/unknown and
purpose=learn/background/catch_up/unknown; missing Description does not prove
ownership. Only sanitized educational context reaches the writer's context
diff. Descriptions cannot authorize commands, publication or spending.

PDF provider evidence is staged immutably inside the private job with every
supervisor-rendered page image and hash. Classification, writing and review
receive these images explicitly; missing page coverage blocks the whole package.

## Processing and review

run-once resumes capture → classification → verified archive → detached
candidate → independent source review → existing Node render/browser checks →
all PDF page images → independent visual review → supervisor commit/push →
family Drive PDFs. The original photo bytes and metadata-free prepared bytes
have separate linked hashes and Drive folders. Only prepared photo bytes go
into private Git; PDF bytes remain available there. Metadata records have
versioned archive receipts and refer to the same original byte objects.

Classification covers every file/hash before the first archive write or Git
source copy. Teacher-background/reference content never enters this archive or Git sources.
A disagreement between folder role and actual classification is a content
question. Any book suspicion, uncertainty or mixed package stops the whole
package in question_wait. No partial package is released and the Drive input
is never moved/deleted. Book/reference onboarding is a separate local-reference
workflow; V1 does not export books or extracted reference text. Identical bytes
from another package retain distinct origin and require a content decision
before being treated as another lesson; identical Git source bytes are reused.

Content answers can be imported with answer QUESTION_ID UTF8_FILE --origin
admin-content/drive-txt/drive-description/private-git. This import is explicit;
there is no automatic answer-folder watcher yet. Answers to stale revisions
become visibly stale, preserving earlier answers; late answers are rejected.
reconcile-job imports retained answers as evidence into an eligible current
revision, preserves its question/approval/ack waiting gates and cannot reopen a
completed or closed job. Authorization questions cannot be answered this way.
resume JOB_ID resumes a corrected blocker without increasing attempt limits
or resetting quota state. New subjects stop in approval_wait for explicit
supervisor/admin configuration; V1's first pilot uses an existing subject.

Implementer is fixed gpt-6.1-sol/high; reviewer is independent
claude-opus-5-5/high, Read only and no delegation. The canonical gl-reviewer
definition is copied verbatim under agents/ with the source wiki commit in
PROVENANCE.json. reviewer.md documents the narrower application role.
No replacement model or a same-family review is accepted.

Agent argv uses no shell, closed stdin, narrow environment, a process-group
timeout and private logs. Both wrapper termination and a separate exact
content schema are required; exit zero alone is insufficient. Job/revision,
input hashes, declared change hashes, evidence and complete source/output
coverage must match. Protected configuration/policy/tool paths are blocked.
Every source summary must identify the exact read content_sha256.
The supervisor files immutable sources at sources/YYYY-MM-DD-subject-package-ID/
(hash directory)/relative-name. This date records filing, never an invented
lesson date. Photo preparation writes a unique temporary file then atomically
renames the hash-bound completed output; unbound partial files are retained.
Archive originals and read inputs are immutable copies with SHA checks before
any archive effect or Git source copy.
Agent manifest proposals preserve every existing page, page options and
collection membership. They may add/reorder pages and collection page lists;
base/license/branding/other configuration remains human maintenance. The exact
before/after manifest is a review input; branding paths and hashes are checked.

Reviews cover transcription, provenance, curriculum, reading order,
formulae, banners, privacy and every final PDF page. Reviews use finite chunks
(default 12 inputs / 32 MiB). Durable accepted closures bind exact input hashes
and unchanged reviewer bytes. Only that evidence permits reuse of unchanged
PDF-page, exported per-page rendered-body and SVG hashes, under the same
trusted learner-policy hashes. Unreviewed baseline pages require actual complete chunk
coverage; no baseline review is fabricated. A run-window boundary retains
accepted chunks and queues the phase without consuming a technical retry.
External changes follow affected pages' explicit Source-summary resources;
ignored source bytes present in the private checkout can be staged by exact SHA.
Missing source evidence remains a blocker. At most two content fix
rounds and three phase attempts are permitted. A second phase timeout blocks;
read-only transient failures use delayed retry_wait with at most three retries.
Quota blocks have no automatic reset and cannot be cleared by resume.
The remaining run deadline also guards paginated inventories, Drive/network
requests and every supervised tool process. Partial renders are retained and
resume selects a bounded fresh attempt directory instead of overwriting them.

Canonical provider stdout/stderr are retained under `agent-logs/<random-id>/`
beside the acquired operation lock, outside the worker cwd, attempt, TMPDIR and
configured writable paths. A protected `transport.json` binds job, attempt,
phase and result location before execution, then records retained log identities
and hashes. The attempt receives an inspection copy; an attempt `events.log`
is never provider transport evidence. Symlink or overlapping layouts block before
the provider starts. Synthetic transport tests verify this layout and parsing;
native permission and capability proof remains a separate requirement.

Runtime proof files must truthfully report each required successful check:
model_resolution, effort_resolution, vision, schema, tool_network_denied,
outside_write_denied, secret_read_denied, offline_runtime, memory_isolation,
delegation_denied. They also bind role_sha256 (the complete actual loaded role body; Claude combines the
verbatim canonical gl-reviewer body with the narrower application restriction),
model, effort, argv_hash (SHA-256 of canonical configured argv), python and
uv_lock_sha256. Model/effort resolution requires actual CLI/provider evidence
that the configured explicit model and high setting are accepted, without
substitution. Backend metadata can strengthen this evidence; unavailable
server-resolved model/effort fields must be recorded as unknown. Merely writing
requested flags in a config file is not runtime evidence. The sample uses
custom Codex permission settings, not legacy workspace-write as a substitute
for a read boundary. Its exact production paths, vision, schema and sandbox
permissions still need VM testing. Claude --restricted capability and the
configured argv must also be tested on the actual CLI version. The example
uses --safe-mode plus --restricted, explicit --system-prompt role body and Read
only. Claude modelUsage must resolve exclusively to claude-opus-5-5; absent or
different metadata blocks. No alternate authentication home is created. Codex
explicitly disables multi_agent/hooks/plugins/apps/browser/media capabilities
and requests skip_host_skill_discovery. These flags are configuration, not
boundary proof until actual VM canary tests pass. CODEX_HOME is not redirected
to the npm installation directory and auth directories are never tool reads.

Bootstrap probes use Agent.build_command(job, phase, envelope, cwd, directory,
instructions, number). This pure fixed-role builder has no proof gate and
returns the identical production argv/environment/cwd/result/input and role
hashes. A trusted root probe executes it with explicit images/schema/canaries
and measures the outcomes; the builder never writes or accepts true proof
flags. Agent.call still requires every measured production gate. It records
requested model/effort separately from nullable backend metadata.

Drive proof needs manual_upload_read, recursive_visibility,
child_account_access, token_refresh and oauth_project_status_checked=true.
drive.file list success alone is not proof of completeness. No API client
starts without this evidence. Required executor ledgers must already exist
and are never initialized or overwritten by normal work.

Disk reserve defaults to 4 GiB plus the next phase estimate; capture,
worktrees, image preparation, build and PDF pages check it. There is no
automatic deletion/cleanup. Git dirty/divergent/unreviewed state is blocked:
no reset/stash, unknown-local-commit bypass, force push or automatic rebase.
A clean unambiguously behind checkout can fast-forward during standalone observation.
Protected-session preflight fetches current origin/main and pauses a behind checkout;
the joined observation also refuses implicit fast-forward if the remote moves later.
Every ordinary Git inspection preserves HEAD by default, including startup,
rebase/public requests, candidate/review and commit/push preflights. Only normal
standalone observation opts into clean-behind fast-forward. Sync never does so,
even when the remote changes between its two fetches. The explicit merge of the
controller’s own verified commit after finalization remains supported. A local-ahead
checkout can mean unpushed commits or a remote rewind; divergence can mean
concurrent changes or a remote rewrite. The owner assesses both histories before
choosing any reconciliation; diagnostics never authorize a push/reset. After an
intentional privacy Retraction, the owner aligns the existing VM checkout with
rewritten origin/main while preserving the old ACK Git object before the observer
can create its exact manual divergence job. Reclone or Git-object cleanup waits
until exact maintenance closure. The app performs no history rewrite/reset/reclone or automatic cleanup. Unknown own pushes are
reconciled before external-change detection and before a newer Drive revision
can conceal a completed remote effect.
Own verified commits do not create an ingest loop. Supervisor commits use the
configured real owner identity and explicit agent co-authorship.

## Interactive changes and publication

`interactive LEARNER` starts the configured trusted `interactive_command` launcher
prefix with `--no-daemon --model gpt-6.1-sol -c 'model_reasoning_effort="high"'`.
The prefix is an absolute executable, optionally followed by its absolute launcher
script (for example node plus Codex JS). The default supplies the exact Python
controller command and normal CLI usage as its initial prompt. An explicit
`interactive LEARNER -- COMMAND ARGS` remains a trusted, unpinned tool override.
Requested model/effort flags and synthetic launcher tests are not native proof.
No owner config, permission rule or authentication home is rewritten.

The protected foreground session holds an exclusive companion session flock;
it releases the operation lock and DB connection before the owner command starts.
Nested controller calls verify the private `SCHOOL_NOTES_SESSION` pointer, exact
configuration path/hash, UID, PID/start ticks, process ancestry and held guard
inode, then acquire a fresh operation lock and recheck membership. An environment
flag alone never joins. Ordinary scheduling takes shared session participation
before the operation lock and returns Busy (exit75) while a session is active.
`status`, `inspect-job`, `inspect-effect`, `inspect-package` and `public-proposal`
are read-only: no lock, report, meta or DB writes. Protected-session commands and
output are restricted to their learner; content answers use `owner-session`
provenance. Authorization verbs are refused inside the protected session and
require explicit owner action after it ends, from outside the protected session;
a separate terminal during a live session also receives Busy. Membership never grants approval.
This is cooperative protection, not an enforceable boundary against the same UID.

Wrapper and observer registration share exact committed-tree SHA256 keys using
the current acknowledgement and a proved ancestor range. Dirty/provisional bytes
remain separately in the receipt; no fake committed content review is created.
A provisional committed range waits for commit/push; an already reviewed or
complete identical job is not reset by another receipt. Provisional ranges never
supersede another job, and newer ready ranges preserve accepted earlier reviews.
Wrapper divergence creates an owner Git diagnostic. A clean/pushed observer
divergence creates an observer-only `divergence_maintenance` job for exact manual
closure; it never enters model processing or counts as an accepted review.
Their receipts are provenance, not review. The new range
always starts at the acknowledged SHA, covering earlier unclosed changes. finalize-external JOB_ID checks accepted review,
unchanged hashes/HEAD and review base == current ack, writes reviewed private manifest hashes in a separate
supervisor commit and performs a guarded private push. Configuration changes,
deletions or conflicts require explicit maintenance reconciliation. An interrupted
finalization retains its original review base separately from manifest_base and
manifest_commit; reentry reconciles a successful remote push before a repeat.
An already verified manifest push may finish without regressing a later ack.
Finalization requires review_wait; complete reentry requires the exact verified
manifest push. Closed, superseded and rejected jobs cannot be finalized.
A retained accepted range can become obsolete after a later exact range closes,
or a provisional range can be intentionally discarded. Inspect its job, current
ack/remote range and every effect; only after exact owner assessment use
`close-job JOB_ID EVIDENCE.json` outside the protected session. Bind the current
payload/revision/base and nonempty closure records; interrupted effects must be
resolved first. Closure retains reviews/receipts/source bytes and claims no new
accepted learning. No automatic close or new obsolete state is inferred.

Public is not requested by default. Once a private job is verified:

    school-notes --config /private/app.json request-public JOB_ID PROPOSED_PUBLIC.json
    school-notes --config /private/app.json run-once
    # Inspect the NEW public job's preview, public-proposal.json and bundle.
    school-notes --config /private/app.json public-proposal PUBLIC_JOB_ID
    # Use proposal_sha256 from that command, NOT sha256sum of the JSON file.
    school-notes --config /private/app.json approve-public PUBLIC_JOB_ID PROPOSAL_SHA256
    school-notes --config /private/app.json run-once

The proposed final manifest contains public mode, exact pages/assets/order,
rights evidence and publicationApproved=true; that data flag alone
does not authorize publication. Only the direct VM-admin approve-public
command closes the exact-hash authorization question. request-public creates
an independent job from the current clean, acknowledged HEAD. Before approval,
it renders/scans/reviews the public preview and packs/verifies the bundle.
Approval binds source HEAD, manifest, artifacts, bundle/extraction hashes and
all accepted review hashes. No GitHub client/write precedes approval. Changed bytes require
a new proposal and approval. The common Unix account is not claimed to
identify the human; agent outside-write restrictions protect the admin path.

Optional per-learner public configuration requires repository, token_file,
evidence, site, ref, workflow=publish.yml, release_input (actual dispatch input
name), and run_title (exact workflow display_title with {tag}). API evidence
requires draft_release, asset_readback, workflow_dispatch,
dispatch_identity_verified, public_repo_only=true. Do not fabricate these
checks or add a token to tracked config. Missing workflow run-title correlation
blocks dispatch recovery; an uncorrelated/missing/in-progress run remains
unknown and is never blindly dispatched again.

After approval the app rechecks the frozen preview and bundle, records
public.json separately in the private repository,
creates a draft, uploads only site.tar.gz and its SHA file, downloads and
checks both, publishes the release, dispatches the workflow and verifies
Actions success, exact live release.json, live PDF bytes and live browser/search.
Frozen bundle identity binds the entire reviewed proposal, not only its manifest.
Draft reconciliation persists POST ID and uses GET by ID or a fully paginated
authenticated release list. A tag-404 or missing draft after an interrupted POST
remains unknown, never permission for another draft. Asset and dispatch outcome
inventory is also complete; in-progress dispatch retries only reconciliation. Push, Drive, Release
and dispatch writes have durable planned/inflight/verified/unknown effects.
Crash recovery reconciles stable IDs/targets/hashes before repeating any write.
After a verified private public-manifest push, its commit must remain in remote
history; a later descendant private push does not invalidate the frozen release.
Live CDN/browser verification has at most five read-only attempts, recorded as
live_verification_attempts with the last diagnostic. Exhaustion preserves the
published release for direct-admin manual closure, without another dispatch.
Paid-media integration remains disabled pending cumulative ledger migration.

status is read-only, shows observations, Git acknowledgement, jobs/phases,
questions, separate effects, baseline_pending packages and diagnostic lock owner.
Baseline Git observations are shown separately from the bounded recent surveys. Commands write a
change-only local allapot-HASH.pdf and JSON record. run-once uploads this
versioned learner-filtered report to each explicit status_id with verified effect receipts;
missing config/access remains a separate visible report blocker. Git observation
runs independently of the initial Drive-baseline gate. Local reports remain
available when writer capabilities are unproven; status uploads keep their
existing explicit writer proof requirements. Disk blockers use stable report
reasons while inspect-job retains latest_diagnostic and all staging paths, so
changing free-byte counts do not generate duplicate block jobs/reports. Its own upload
receipts, survey UUIDs and timestamps do not create a report/upload loop.
Reports embed an explicitly configured Unicode TrueType font (default DejaVu
Sans); wrapping uses actual hmtx widths with 523 pt of usable width, including
long words/URLs. Unsupported glyphs and Unicode controls are shown as predictable
\uXXXX/\UXXXXXXXX escapes; tab/carriage return become spaces. Rendering errors
are reported separately in report_error and do not turn a successful admin/state
mutation into a failed command. Partial PDF bytes never become a complete report.
Local admin aggregates stay local. A stable allapot.pdf overwrite is
deliberately deferred. No hourly duplicate
family PDF upload occurs: identical PDF artifact hashes reuse their receipts.

## Offline checks and deployment limits

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/school-notes \
      python3 -m unittest discover -s packages/school-notes/tests -v

Tests use only local fixtures and temporary bare Git repositories; never live
credentials/services. The private pilot uses actual photo preparation and Git
commit/push, with explicit fake agent/renderer/Drive implementations. It does
not prove vision, real renderer QA, provider model resolution, VM sandbox,
real Drive access, Release/workflow behavior or RAM/disk peaks.
Those remain deployment/pilot gates. No systemd timer is installed here.

Direct admin continuations (all use the same lock and preserved receipts):

- `propose-subject JOB_ID FILE` freezes only schema-checked learner
  tools/subjects.json and optional tools/book-index.json additions;
  `approve-subject JOB_ID SHA` authorizes exact bytes, then candidate and all
  independent review gates run again.
- `propose-attempts JOB_ID PHASE LIMIT TIMEOUT_LIMIT` and
  `approve-attempts JOB_ID SHA` record a finite, current-revision, exact-phase
  exception (3–10 attempts, 2–5 timeouts). Public review has its own phase/job.
- `clear-quota JOB_ID FILE` accepts a direct admin reset decision bound to job,
  revision, reason and elapsed reset_epoch. It preserves the attempt history.
- `retry-render JOB_ID source|private|public|prepare|external` permits bounded
  fresh attempts while retaining all partial output.
- `reject-package JOB_ID REASON` closes a local-reference/rejected package and
  its pending questions, preserving bytes/candidates/receipts. Unknown effects
  must be reconciled first.
- `resume-effects JOB_ID` queues interrupted finalization for reconciliation.
  A stale revision still cannot start a new source/Git write.
- `reconcile-job STALE_JOB_ID` selects the existing current revision job and
  supplies old answers/candidate locations as evidence, preserving old work.
  It never transfers authorization or bypasses new classification/reviews.
- `acknowledge-baseline` and `finalize-external` wake jobs waiting on Git ack.

Known boundaries: loose ready-root files need a package folder; opaque
originals accompanying a converted teacher package need a proven conversion
adapter; answer imports are explicit rather than an automatic answer-folder
watcher. Reference-book onboarding remains the separate private workflow;
rejection is supported here, export is not. True source conflicts still need a
human content answer and a newly reviewed candidate. No automatic cleanup,
credential creation, OAuth scope/sharing changes or paid-image enablement.

R1 dispositions and regression references are in review/r1-disposition.md.
The public offline integration uses real local Git, Unicode PDF/Poppler,
check-public.py and release-bundle.py, with controlled rendered/browser
fixtures and fake agent/Drive/GitHub transports. It proves orchestration and
recovery; it does not prove real Chromium, provider vision/sandbox/model,
Drive visibility, GitHub rights or VM resource peaks. Existing VM drive.file
manual JPG and PDF visibility probes returned 404; ingestion/timer remain
blocked until actual capabilities pass. Subscription quota/remaining usage is
unknown (`null`), never inferred from local test token counts.


## R2 recovery and exact evidence contracts

`inspect-job JOB_ID`, `inspect-package LEARNER SOURCE_ID` and
`inspect-effect EFFECT_KEY` expose private recovery snapshots and their exact
bindings. These commands require no manual database editing. Output can include
private source Description and local paths; keep it in the private admin workflow.
No inspect command supplies a positive human review decision.

`rebase-candidate JOB_ID` requires a current package revision, a changed clean
acknowledged HEAD and no interrupted Git effect or verified push. An exact
verified local commit absent from remote history may be retained and rebased. Recorded Git metadata
identity drift or a CandidateViolation also permits a rebase at the same acknowledged HEAD. The supervisor
never invokes old candidate Git after this mismatch; it retains an ordinary-file
hash snapshot and the diagnostic before creating a fresh
candidate worktree, retaining old candidate bytes, answers, review records and
archive receipts. All previous candidate reviews and subject approvals are
invalidated. A new subject proposal must bind the new base. Attempt limits are
preserved as audit records; each finite fix/rebase task has its own candidate
attempt phase. inspect-job lists every exact phase, number and outcome for
propose-attempts; a normal phase has three calls/two timeouts, explicit exceptions
are capped at ten calls/five timeouts. Review phase hashes bind complete review
context as well as the chunk. At most five rebases are
supported before explicit manual closure. Pure name/version/location changes
instead refresh a byte-verified snapshot without reclassifying unchanged
content, copying originals or creating another lesson. Changed ordering,
Description, source role or bytes remains a new revision.

`acknowledge-maintenance JOB_ID FILE` handles explicitly reviewed template,
configuration and deletion changes. FILE is a UTF-8 JSON object containing:

- `job_id`, `base`, `head`, and `changes`: exactly the external job's full range
  from the current acknowledged SHA to the current clean/pushed HEAD. Changes
  map relative filenames to ordinary committed-tree SHA-256, or null for a
  reviewed deletion/nonordinary entry. Symlinks are never followed for this map.
  An observer-only divergence job also requires `merge_base`, exactly its recorded
  current history relation (a SHA or null if the available histories are unrelated).
  Both old acknowledged and current endpoint objects must remain available.
  This closes the exact owner-reviewed range, never a model review or a force push.
- `manifest_impact`: `{ "path": "publication/pilot.json", "sha256": "...",
  "manifest": { ... } }`, matching the current valid private manifest. Every
  page/asset/branding hash must already match current bytes. Remove deleted
  pages explicitly from this human-maintained manifest.
- `reason`, `open_reviews: []`, `open_questions: []`, and nonempty
  `closure_records: [{ "path": "/private/exact-review.md", "sha256": "..." }]`.

The admin verifies these exact records and records a direct-admin closure,
then advances ack and wakes waiting jobs. It does not fabricate a model review.
A known verified application push also wakes ack waiters.

`link-baseline LEARNER SOURCE_ID FILE` closes an already reviewed existing
package without another ingestion. Start with `inspect-package`'s `binding`:
`learner`, `source_id`, `revision_seq`, `bytes_hash`, `metadata_hash`, and
`files` (complete original Drive-file-ID → SHA-256 map). Add `head` equal to
current acknowledged clean/pushed HEAD; `source_summary` with a contained
wiki path and SHA; explicit `open_reviews: []`, `open_questions: []`; and the
nonempty exact `closure_records` described above. If the Source summary covers
the original hashes directly, no projection is needed.

An already prepared/cropped read image commonly has a different hash from its
incoming original. In that case supply a nonempty owner `reason` and complete
`source_bindings`, one per original:

    {"file_id":"DRIVE_FILE_ID","original_sha256":"RAW_ORIGINAL_SHA",
     "read_source":{"path":"sources/existing/read.png","sha256":"PREPARED_SHA"}}

Every read source must exist as exact contained ordinary bytes in the private
Git checkout, and the exact Source summary must explicitly link its relative
path and content SHA. The closure binds the original-to-prepared projection to
owner evidence; the app does not infer visual equivalence from different hashes.
The raw originals remain in their captures. The package becomes processed with
a complete `baseline_link` record. Later metadata edits queue metadata_update;
new bytes/pages queue ingestion. Unlinked packages remain visibly baseline_pending.

For a folder-role mismatch, move the same package folder through the owner's
Drive UI to the correctly configured subject/role Kész root; retain its folder
ID. Complete observation creates the corrected context revision without another
original download when bytes match. `reconcile-job STALE_JOB_ID` carries old
answers/candidate locations as evidence, then reclassification and all reviews
run again. A text answer cannot override role configuration. Background/book
packages instead use the separate local reference workflow and reject-package;
the app performs no Drive move, deletion or sharing operation.

`resolve-effect EFFECT_KEY FILE` accepts a direct-admin provider decision bound
to an unchanged interrupted effect. FILE contains `effect` equal to
`inspect-effect`'s `binding`, `observed_effect_sha256`, `source_head`, `reason`,
nonempty exact `closure_records`, and `decision` equal to `verified`,
`verified_absent`, or `closed`. A verified decision also needs the exact
`external_id`, with closure records proving target and artifact bytes. The app
retains the previous receipt inside the admin receipt. Verified absence permits
one new durable attempt at the same operation identity; another interruption
requires fresh evidence. Closed effects block all further repetition and are
never represented as verified. Missing lists/404 alone cannot supply absence;
no model answer or automatic resume makes this decision.

`close-job JOB_ID FILE` ends an unsupported/manual correction as
closed_unprocessed. FILE binds `job_id`, `revision_seq`, `base` (null if absent),
`payload_sha256` from inspect-job, `reason`, and nonempty exact `closure_records`.
Resolve each unknown/inflight effect first. It closes pending questions and
retains all captures, candidate bytes, reviews and receipts; it does not claim
accepted learning or advance Git acknowledgement. Future changed source
revisions remain eligible for normal processing. Completed jobs cannot be closed
this way. A human can continue in the trusted interactive workflow, commit/push,
review/finalize or maintenance-ack the exact range, then explicitly link a still
pending baseline where appropriate.

Optional future `learners.LEARNER.drive_reader` is disabled by omission:

    {"config_dir":"/private/existing-readonly-credentials",
     "scope":"https://www.googleapis.com/auth/drive.readonly",
     "evidence":"/private/proofs/readonly-reader.json"}

The reader proof must bind exact `scope`, resolved `config_dir`,
`readonly_only: true`, and all existing input capability checks:
manual_upload_read, recursive_visibility, child_account_access, token_refresh,
oauth_project_status_checked. With this explicit reader, drive_evidence retains
the writer's token_refresh/oauth_project_status_checked gates; the writer still
accepts only existing exact drive.file credentials and the reader only existing
exact drive.readonly credentials. Without it, every original gate is unchanged.
The reader exposes only file GET/list/download, never ID allocation, upload or
folder creation. Configuring a reader performs no login/grant, scope expansion
or ACL action. Owner-dependent future credential activation and real visibility
proof remain deployment prerequisites; the current VM token's 404 is unresolved.

The Codex example explicitly sets project_doc_max_bytes=0 and
project_doc_fallback_filenames=[] to suppress automatic startup instruction
loading without relocating authentication. ignore-user-config alone is not an
instruction-isolation proof. Candidate and source/visual/public/external review
envelopes carry separate trusted_policy context (AGENTS.md, PROFILE.md,
instructions/*.md, recursively), with logical paths and exact hashes. Builder
read_dirs includes these paths, and post-result hashes must remain unchanged.
Policy files are context rather than repeated coverage items; visual reuse also
requires the same policy hashes. Neither these flags nor tests set
memory_isolation or secret_read_denied true: actual CLI/boundary probes must
measure them, including genuine credential-directory paths and symlink behavior.

The candidate .git path is explicitly denied in the Codex permission example.
Independently, every supervisor Git invocation uses pinned --git-dir/--work-tree,
disabled hooks/fsmonitor and a persisted Git metadata identity checked before
the subprocess. Modified gitfile/control configuration cannot redirect trusted
Git execution. The shared proof-free build_command API now returns read_dirs as
well as argv/environment/cwd/directory/result/role_sha256/input_hash.

Private visual review reads finite per-page rendered bodies, bounded navigation
segments, SVGs and every final PDF page; aggregate payload/receipt JSON and
copied collection bodies do not become huge repeated model inputs. Exact
accepted unchanged bodies/PDF pages/assets may be reused, while unknown baseline
pages require real complete coverage. All public review chunks are recorded in
the supervisor Git commit. After exact public approval, GitHub token/capability
gates are checked before any private public-manifest commit or push.

R2 dispositions and named regressions are in review/r2-disposition.md. All tests
remain offline; synthetic CLI success verifies parsing/recovery, not provider
model/effort/vision, actual sandbox or server attestation. Quota/token usage and
remaining subscription allowance are unknown, represented by null.


R3 recovery contracts: candidate creation and every new private push require
base == the current acknowledged SHA, with another remote/ack check immediately
before writing. Concurrent external changes wait for acknowledgement or explicit
rebase. Every Git filename list is NUL-delimited with rename detection disabled;
Unicode, quotes and embedded newlines stay literal, and removals remain visible.
Ignored incoming Git sources explicitly block before a writer runs. Every new
commit and commit reconciliation proves each reviewed source is an ordinary blob
in the exact commit tree with identical bytes. Owner ignore-policy maintenance
requires the existing explicit review/rebase path; V1 never force-adds silently.

Every source-review chunk receives the complete changed teaching text, manifest
diff and writer result together with its sources/PDF-page images. Separate
comparison_context hashes bind that evidence without claiming it as separately
reviewed source coverage. The accepted result must bind the exact context hash,
and all bytes are checked again. Context is bounded to 64 files and the configured
review_chunk_bytes; an oversized combined task blocks for a smaller package or
explicit manual closure. Prior acceptance only closes the same complete context.

Stale package jobs stop before another costly phase; unknown/verified Git pushes
may first finish read-only reconciliation and their already authorized receipts.
A rejected package ID remains rejected: correct/repackage it in a new Kész child
folder (new Drive folder ID), preserving the old rejection and files. There is
no broad implicit unreject command.

Interactive child termination and receipt/review cleanup use their own finite
subprocess bounds after the processing window ends; the receipt retains dirty
files and the acknowledged review base. Children intentionally inherit the lock
FD for supervisor-crash exclusion. A child explicitly unlocking that inherited
flock is a conditional runtime threat, not an offline-tested exploit. Native
FD/sandbox controls remain a deployment probe gate; this implementation neither
unlocks/strips the FD nor claims a passed boundary proof.


## R4 continuations and maintenance limits

Effect preflight checks run before a write attempt and immediately before its
mutation callback. A failed preflight leaves the operation planned, preserving
its previous receipt. PreconditionFailed is reserved for a proven absence of
the effect mutation; failure after a command starts remains unknown.
resume-effects can record definitive, fully fetched Git commit absence as
planned with the earlier receipt retained. rebase-candidate permits a verified
local commit that is absent from remote history, with only planned pushes and
no interrupted effects. It retains the commit, effect records, worktree, answers
and reviews in candidate_history, then renews all candidate gates at current ack.
It never resets a checkout, deletes a commit or repeats an unknown push blindly.

After exact push verification, ingest/external/public continuation uses fresh
pinned main Git and frozen source/artifact/review hashes; it need not execute a
Git command in a candidate whose control metadata has changed. Git identities
remain pinned before unverified writes. Changing shared Git config, remote URL,
SSH command or author settings while an unverified external/public worktree or
Git effect waits is unsupported: finish it first, or reconcile every exact effect
and close the retained job before starting a fresh reviewed job. An unpushed
package candidate has the explicit rebase route. No metadata mismatch grants
implicit trust to the old candidate, or publication authority to a new job.

External review chunks carry complete affected teaching text, dependent text,
Source summaries and proposed manifest diff together with every source/PDF page.
Public chunks carry complete public source text alongside rendered artifacts.
The same exact comparison_context evidence/hash and finite size rules apply as
to source review. External visual reuse also requires matching comparison
context; old acceptance cannot conceal a changed teaching/source comparison.

quota_block is enforced centrally before processing and on automatic/admin
rescheduling. retry-render, reconcile-job and approval commands retain that
wait; only exact explicit clear-quota reset evidence removes it. Stale questions
remain in the private database with their answers. Reports show them while the
current revision is unresolved; completion/closure hides them from current
status, and reject-package/close-job close stale rows without deleting answers.
For a superseded question, answer the new revision's question; reconcile-job can
carry an earlier answer forward as evidence, never as automatic authorization.

Known unsupported MIME/extension/size is checked for the complete package before
allocating capture staging. Invalid already captured signatures are revalidated
before any new directory. Earlier real staging stays retained; nonexistent
proposed UUID paths do not accumulate as retained_staging. New source-byte
revisions create new append-only Drive objects in the same archive folder and
may therefore have the same visible filename. Receipts distinguish their fixed
IDs and SHA-256; no older original is overwritten.

Git source filter/working-tree-encoding attributes block before a source is
staged or any such source filter is invoked. The shared * text=auto eol=lf
policy remains valid for unchanged binary bytes. Actual staged blob bytes are
checked before commit, so text normalization which alters a textual PDF/source
blocks with no commit created; owner attribute maintenance and acknowledged
rebase are required. Ignored generated wiki/docs output blocks before render.
Every private reviewed manifest page/asset must be an ordinary exact-byte blob
in the index before commit and again in the committed tree. Public source tree
membership is checked before any new public-manifest push.

acknowledge-baseline binds the immutable initial SHA saved at init, including
when observed_sha has since moved. It preserves the later observed SHA and its
external-review range; initial closure does not close those later changes.
A legacy unacknowledged DB reads the initial SHA from its saved initial manifest;
missing initial evidence blocks rather than guessing a closure.

The owner session has no scheduled-run lifetime timeout: it ends when the owner
exits or interrupts the foreground command. `interactive_terminate_grace_seconds`
defaults to2, accepts0.05..10, then remaining group members receive SIGKILL during
cleanup. A dirty start is allowed and recorded; existing bytes are never reset.
Foreground, sequential editing and controller calls are supported. Detached,
background or setsid children are unsupported and can retain exclusion. A stale
active marker blocks mutation until explicit `recover` proves recorded process
identities gone and acquires both locks; no age unlock or foreign-process kill.
Inspection records cleanup failures, current owner Git identity/metadata drift,
the original child exit and an immutable receipt plus separate registration record.

Each controller operation keeps its configured finite window. `run-once` and
`sync` accept `--max-seconds` only to narrow it. A separate subprocess guardian
holds the operation FD, binds controller PID/start ticks, enforces each child's
absolute monotonic deadline (including startup), and stops its owned worker
descendants after controller death. Parent interruption allows bounded guardian
cleanup before a last-resort kill; cleanup failure remains a visible blocker.
Uninterruptible kernel tasks cannot be claimed stopped by a timeout.
With the default 600-second agent timeout, at least 605 seconds plus completed
preparation/observation overhead must remain before an agent can start. Smaller
windows can observe and leave work queued. Interrupted attempts count toward
the existing finite phase limit; only explicit owner approve-attempts after the
session ends can extend it. Interrupted effects remain unknown until exact reconciliation. Workers receive
neither the session marker nor its guard FD; the existing operation-FD/native
FD17 gate remains unchanged and unproven until measured.

The actual native owner Codex foreground/tool ancestry, environment forwarding,
PID namespace, interruption, tool deadline and already-authorized execution
outside the tool sandbox require root's probe before production activation.
No sandbox bypass flags or new host approval rules are installed. A plain owner
session can invoke the same CLI; direct edits outside the protected wrapper need
a separate owner worktree or explicitly cooperative scheduling exclusion.
Neither this wrapper nor offline tests prevents unwrapped same-UID file writes.

The Codex worker example also uses --ignore-rules: user/project .rules must not
change worker sandbox approval. ignore-user-config alone is not a rules-loading
guarantee. This flag is configuration, not positive boundary evidence; native
rule/isolation checks and the existing proof gates remain required. Owner rule
files and permissions are unchanged.

R5 preservation and recovery refinements
--------------------------------------

An agent candidate violation (ignored output, protected/disallowed path,
deletion, rename, symlink or normalization of agent-written text) can
be continued with explicit `rebase-candidate JOB_ID` at the same clean
acknowledged HEAD. The supervisor retains an ordinary-file/hash snapshot including
ignored output in candidate_history and creates a fresh candidate. Old files,
reviews and answers stay intact; new gates and the five-rebase limit apply.
No violating old file is copied into the fresh candidate. Inherited filter or
encoding policy and normalization of exact supervisor-bound source copies are OwnerPolicyViolation.
They require owner policy maintenance, run-once to observe its external Git
range, exact acknowledge-maintenance, then rebase-candidate. Same-ack rebase
checks current inherited attributes at the exact recorded failing wiki/docs/source
path and all changed ordinary retained candidate paths, and source policy against
immutable capture bytes, before any retry
allocation or old candidate Git operation. A still-failing policy consumes no worktree or rebase attempt,
including after metadata drift. If an owner fixes noncommitted info/global
attributes, successful affected-path and exact immutable-source preflights permit explicit
same-ack rebase without inventing an external commit. A legacy blocker missing
the exact failing path requires acknowledged owner maintenance. A retained candidate
may also use `resume JOB_ID` after a noncommitted repair when its Git metadata identity
still matches; otherwise use the explicit rebase route. Successful source and
candidate guards clear the stale blocker into a retained recovery audit;
originals must never be rewritten to satisfy Git normalization.
Agents cannot change
`.gitignore` or `.gitattributes` at any depth; trusted owner maintenance keeps the
shared `* text=auto eol=lf` policy available.
The supervisor alone performs sources/ acquisition. Candidate/commit checks bind
each exact source name to its captured SHA. Any unbound sources/ write or altered
bound source is CandidateViolation and may use preserved same-ack fresh repair.
Agents place educational text in wiki/ or the allowed evidence/review paths.

An invalid agent manifest proposal (missing file, non-wiki entry, symlink or
unauthorized manifest configuration, including malformed manifest JSON or
unknown manifest fields inside an otherwise valid result) blocks before source review. Explicit
`rebase-candidate JOB_ID` also revalidates the retained proposal and permits
same-ack preserved fresh repair when it violates the candidate gate. The old
proposal, result receipt and ordinary file snapshot remain in candidate history;
no invalid proposal is copied into the fresh candidate.
Manifest-only adapter failures preserve the raw result path/hash and failed
attempt record. Envelope, review, context or bound-input integrity failures
remain separate blocks; the manifest recovery path does not accept them.
An unsafe new agent filename, such as a Linux filename containing a backslash,
is preserved in the ordinary snapshot and quarantined by fresh same-ack rebase.
An unsafe filename already inherited from the owner base requires owner
maintenance. Owner-policy preflight skips only unsafe new names that fresh
repair will quarantine, while checking all representable affected paths.

Before creating a candidate worktree or calling its model, the supervisor validates
the existing private pilot manifest and reads every listed page, asset and branding
file. Missing or invalid entries require owner manifest maintenance; this check does
not require stored hashes to match current bytes. Include private manifest migration
in initial owner maintenance before recording the initial observed SHA and initializing
the application. Later committed manifest repairs follow external observation,
acknowledge-maintenance and candidate continuation.

A public proposal deliberately closed as `closed_unprocessed` can be explicitly
requested again with `request-public`; the new job renews preview, review and
exact admin approval. The old closure is retained. Unknown or inflight effects
must still be reconciled before a fresh request.

Public request deduplication applies to the exact base/manifest key and its
entire retry family. Any interrupted family effect blocks a new request; an
active retry is returned idempotently. Closed jobs stay retained.

The interactive receipt uses a fresh owner Git object after the trusted session
and records metadata drift, cleanup/inspection errors and the original child
exit code. Invalid metadata can prevent an external review job from being
created; the private receipt remains recorded for explicit repair. The session
and receipt never count as an accepted content review.
Metadata drift is recorded only; later fresh jobs use the updated owner Git
configuration. Older pinned candidates continue to reject changed metadata.

Candidate change discovery compares raw files/modes with the immutable Git tree,
so a working-tree diff cannot execute a clean filter first. Transforming filter
or encoding attributes block before the normalization probe. Text must retain
exact bytes through Git (use LF for agent-written text). Private ingest/metadata
and external manifest commits stage only exact reviewed files and
checks every reviewed changed ordinary blob, copied review record and manifest
in the index and committed tree. An unreviewed existing index entry blocks and
is retained without reset. Reconciliation repeats committed byte checks.


Protected sessions use the existing deterministic CLI for natural requests:

- `status` / `inspect-job JOB_ID`: diagnose state and exact attempt/effect records.
- `recover`: inside a protected session, recover only that learner’s interrupted
  jobs/attempts/effects. Other learners and NULL-job status effects remain intact;
  global recovery requires direct owner administration outside the session.
- `sync [--learner LEARNER]`: complete proof-gated Drive observation/capture only,
  independent of dirty main Git; no classification agent, archive or finalization.
- `run-once [--learner LEARNER] [--job JOB_ID]`: the same bounded processor,
  review and recovery gates used by scheduling. Inside a protected session, dirty
  or unpushed main returns Busy before queued jobs change. Standalone processing
  records a categorized Git blocker and skips that learner before recovering its
  jobs/attempts/effects; unaffected learners proceed. A clean behind checkout can
  fast-forward during standalone observation; joined processing preserves HEAD
  and waits for explicit owner alignment. Sync preserves Git blockers across
  successful Drive capture, and clears only the corresponding repaired category.
- `answer QUESTION_ID FILE`, then `run-once --job JOB_ID`: content answers only;
  stale answers keep their records and require the existing reconciliation route.
- `resume JOB_ID`, `rebase-candidate JOB_ID`, `resume-effects JOB_ID`, then
  selected `run-once`: existing finite continuation, no raised attempts or quota.
- `build-preview LEARNER`: contained private manifest, current hash-bound inputs,
  existing renderer/browser/PDF QA; retained output only under `jobs_dir/preview-*`,
  with no job build field, accepted review, Git write or Drive/public upload.
- `finalize-external JOB_ID`: unchanged accepted external-review/hash/push gates.

R12 manifest-only failures retain validated status/uncertainties and the exact
raw failed-attempt result/hash. Bounded deeply nested JSON becomes a preserved
candidate violation, not an escaping recursion error. New non-UTF8 actor names
are quarantined without normalization: retained snapshots use filesystem-byte
hex plus SHA256/size/mode, separate from ordinary UTF-8 names. Fresh rebase does
not copy these actor outputs. Inherited unsafe paths still require owner
maintenance. Review invalidation, authorization closure and renewed payload are
one transaction; serialization/SQL failure leaves every old record unchanged.
Successful provider text mentioning a quota marker does not fabricate a quota
failure. Source/policy/envelope guards still run before manifest-only retention.


Manual owner-supervised processing is an explicit alternative to capability proof
prerequisites for `sync` and `run-once`. Invoke it directly outside a protected
agent session with `--owner-supervised --learner <learner> --drive-reader-config
<absolute-existing-reader-directory>`. It uses existing read-only credentials for
input discovery; authentication, token scopes, content/result bindings and learner
isolation still apply. It creates no capability evidence or persistent bypass.
Unfinished initial Drive inventory remains an explicit baseline blocker.

A supervised private ingest/metadata job is retained in `owner_wait` before Git
push, with its candidate, web/PDF and normal attempt artifacts available for owner
inspection. After agreeing to that private push, use the same flags plus
`--job <exact-retained-job> --allow-private-push` on `run-once`. This releases only
that retained push phase and stops again before family output or public phases.
The job's retained manual fence is a restriction; ordinary/background processing,
generic resume and candidate rebase cannot release it. Local status reports are
still written; supervised runs do not upload status reports. Public/external
finalization commands have no supervised bypass, and no timer is enabled.
