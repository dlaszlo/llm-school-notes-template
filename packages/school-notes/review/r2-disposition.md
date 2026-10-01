# School Notes V1 — R2 disposition

Reviewed report: independent claude-opus-5-5/high R2 at
`/tmp/school-notes-app-v1-review-20261001-r2/result.md`. The root verified the
source packet input hash guard. Author: fixed gpt-6.1-sol/high. Changes are
limited to the temporary application's package, with no live/provider/credential
calls, scope/ACL change, original-worktree write, commit or production action.

All named regressions are in `tests/test_review_r2.py`; R1 regressions remain.
No supported R2 app finding is dismissed. Qualifications below preserve the
limits of review claims and the distinction between offline orchestration and
actual production proof.

| ID | Disposition and implementation | Regression / proof limit |
| --- | --- | --- |
| N-01 | Fixed: current-source `rebase-candidate` creates a fresh worktree on changed clean acknowledged HEAD, retaining candidate/answers/archive evidence. Reviews and subject approvals invalidated; finite five-rebase cap, attempts preserved. | `test_N01_question_candidate_rebased_after_other_package_push`: two real local Git package jobs, first waits for question, second pushes, first blocks then completes after exact rebase; old candidate/answer retained. |
| N-02 | Fixed: byte-verified same-revision observation refreshes active snapshots. Final stable check recaptures/reuses bytes when provider location/version fields change, comparing byte/context identity. New ordering/role/context remains a new revision. | `test_N02_pure_rename_before_commit_refreshes_without_revision`: rename/version change between review and commit, completes, one revision and one original download. |
| N-03 | Fixed: exact direct-admin `acknowledge-maintenance` checks entire ack-to-HEAD changes/deletions, current valid manifest impact and closed hash-bound records. Verified application pushes also wake ack waiters. | `test_N03_maintenance_ack_exact_manifest_closure_wakes_jobs`, existing SN03 wait wake regressions. Human closure is explicitly recorded rather than invented model acceptance. |
| N-04 | Fixed independently of sandbox: persisted gitfile/gitdir/common-control identity, verified before every subprocess; explicit pinned Git arguments, disabled hooks/fsmonitor/ext protocol; example denies candidate .git. External/public/manifest worktrees also bind identities. | `test_N04_gitfile_and_config_tampering_block_before_subprocess`, `test_N04_git_commands_pin_metadata_disable_execution_hooks`, policy/builder test. The original attack was conditional, not a proven CLI escape; actual VM boundary proof remains pending. |
| N-05 | Fixed renderer contract: branding only contained publication/assets/*.png with PNG signature and exact hash. | `test_N05_renderer_branding_contract_png_only`: correct paths accepted, wiki/SVG/traversal/non-PNG refused. Real renderer/browser proof is still a separate gate. |
| N-06 | Fixed private visual scope: typed per-page exported body, bounded ordered navigation segments, SVGs and every PDF page. Aggregate payload/receipts and duplicated collection chapter bodies excluded; reuse requires accepted exact artifact and unchanged policy hashes. | `test_N06_delta_page_reuse_excludes_oversized_aggregate`: oversized aggregate no model task, unchanged body reused, newly added page reviewed, invalidated old acceptance not reused. R1 SN30 large PDF chunk test remains. Public privacy still scans and binds complete frozen output; public review retains its own full designated coverage. |
| N-07 | Fixed optional separate existing-credential GET-only reader; disabled by omission. Exact readonly scope/directory proof plus unchanged input visibility checks; separate exact drive.file writer token/project gates. | `test_N07_readonly_adapter_reuses_exact_existing_scope_get_only`: isolation of writer/reader scope checks, writer cannot claim manual input proof, all reader mutation surfaces refuse. No real credential grant/activation or API proof. The claim that a new readonly grant is the only visibility solution is not established; this is an optional supported contract. |
| N-08 | Fixed predictable unsupported-glyph/Unicode-control escaping with hmtx wrapping; atomic completed PDF and separately visible rendering failure. Successful state/admin mutation keeps exit zero. | `test_N08_emoji_control_report_poppler_and_nonfatal_missing_font`: actual Poppler extraction, Hungarian/emoji/control escapes, missing-font failure without bogus complete PDF or failed mutation. R1 150W/bbox test remains. |
| N-09 | Fixed wrapper base=current ack; complete earlier unclosed range included. Clean pushed result queued, dirty/unpushed review_wait gives commit/push→run-once→finalize instructions. | `test_N09_wrapper_uses_ack_range_and_dirty_wait`; R1 actual PTY/foreground/interruption regression remains. |
| N-10 | Fixed `link-baseline`: current original ID/SHA map, bytes/meta/revision, acknowledged clean HEAD, exact Source summary and closure records. Original→prepared projection requires exact existing read-source path/SHA plus explicit owner closure. Complete baseline_link records drive later revision comparison; status/report shows pending packages. | `test_N10_link_baseline_exact_hash_later_changes_queue`: actual distinct raw/prepared PNG hashes and Source-summary link; stale/wrong map refused; later Description queues metadata update, new page queues ingest. Projection is owner evidence, not inferred visual equivalence. |
| N-11 | Root-owned ops probe enhancement; app adds .git deny, global startup document-cap flags, trusted learner-policy context for writer/all reviewer phases and shared builder read_dirs. | `test_N04_N11_policy_context_builder_bound_without_coverage_or_private_metadata`: exact policy/context/read-scope wiring, no private-classify leakage. Root reports synthetic controlled boundary tests; actual VM/native denial and memory_isolation remain unready until measured. |
| N-12 | Fixed `public-proposal JOB_ID` exposes canonical proposal_sha256; README rejects sha256sum(JSON file) as approval digest. | `test_N12_public_proposal_canonical_hash_not_file_hash`. |
| N-13 | Fixed successful complete Drive observation closes obsolete learner runtime blockers; failed capture records remain pending when genuinely unresolved. A disappeared source gets an explicit restore/reject next step with retained staging. | `test_N13_N15_runtime_success_prunes_observations_preserves_baseline`, `test_N13_disappeared_capture_stays_retained_with_explicit_next_step`. Source disappearance is not falsely called successful capture. |
| N-14 | Supported safe existing-folder role correction: owner moves same package ID into configured matching ready root, then observation/reconcile generates new context revision and renewed full classification/review. Text answer cannot override role; background/book uses separate local reference/reject workflow. | `test_N14_move_same_package_to_matching_role_creates_context_revision`: same package ID, new role revision, one original download. App performs no live move/sharing/deletion. |
| N-15 | Fixed bounded latest 20 Drive observations per learner, latest complete full inventory and older digest summaries; baseline stored/query-visible independently. Source revisions/captures/reviews are retained. | `test_N13_N15_runtime_success_prunes_observations_preserves_baseline`: 35 surveys, 20 retained rows, one full current inventory, baseline and packages visible. |
| N-16 | Fixed GitHub capability/token gating after approval but before any private public-manifest Git mutation. All accepted public chunks copied and crash-reconciled as exact supervisor paths. | `test_N16_github_gate_before_private_commit_and_all_chunks_recorded`: real local Git, bundle/scanner/PDF with controlled render/transport; missing proof gives zero Git/GitHub mutation; every chunk tracked on successful resume. |
| N-17 | Fixed direct-admin `resolve-effect` bound to exact unchanged complete effect snapshot/receipt/target/artifact/source HEAD and hash-bound provider records. Verified/verified_absent/closed dispositions explicit; prior receipt retained. One repeat only after explicit absence; another interruption requires new evidence. | `test_N17_exact_effect_admin_absence_once_then_new_outcome_required`, `test_N17_verified_and_explicitly_closed_effect_preserve_original_receipt`: stale/wrong evidence rejected, no blind repeat, closed never treated verified. Provider absence is owner evidence, not inferred from 404/incomplete list. |
| N-18 | Fixed `close-job` exact payload/revision/base/record-bound direct closure, with unresolved-effect gate. closed_unprocessed retains all records, makes no accepted-learning/ack claim; manual interactive/maintenance/baseline-link paths documented. | `test_N18_manual_close_retains_files_and_does_not_accept_learning`, `test_N18_unknown_effect_blocks_job_closure`. |

Additional author self-check removed a duplicate read_dirs computation in
Agent.call. The contract now exposes read_dirs, and runtime receipts use that
exact builder value including trusted-policy scopes. The frozen R2 code already
defined read_dirs; this is a consistency improvement, not an unbound-variable
bug fix. `test_successful_finite_adapter_records_bound_read_dirs_without_runtime_attestation`
runs a real finite local synthetic CLI process through schema parsing and
runtime receipt writing; resolved model/effort remain null. This is not a
provider capability proof.

`inspect-job`, `inspect-package` and `inspect-effect` expose the exact private
bindings needed by direct-admin commands without manual database editing or
an additional authorization/provider flow. No command generates positive
owner-review decisions. README contains the JSON evidence contracts.

Production gates remain unready: actual Codex/Claude argv/sandbox/model/vision
and memory isolation, recursive Drive/manual-upload visibility (existing JPG
and PDF probes returned 404), real renderer/browser deployment integration,
GitHub repository/token/workflow capabilities and resource peaks. Optional
readonly activation remains owner-dependent. No timer starts from these
changes. Shared source/policy and ops records are root-owned and untouched here.
Quota, token usage and remaining subscription allowance are unknown (`null`).
