# R4 author disposition — School Notes V1

Author fixed gpt-6.1-sol/high; tokens and quota unknown (null). Only temporary
packages/school-notes source/tests/docs/example config changed. Original files,
ops, VM, credentials, scopes, ACLs and live services were untouched. No child
agent or review was launched. Exact R3 guard passed before editing; all 27 R3
files remain in /tmp/school-notes-app-v1-r3-frozen.tar, with the unchanged R3
hash manifest and review receipts retained.

The author read the complete independent Opus/high R4 report and checked the
code paths. R4 is a reading review, not an independently executed integration
claim. Eight author tests were executed against frozen R3: seven failed and
one errored on the newly specified missing PreconditionFailed contract
(/tmp/school-notes-r4-before.log). All eight then passed (2.122s). Additional
regressions were added, not all executed against historical bytes. A root-found
two-push initial-ack edge was separately reproduced by the author against the
intermediate one-push fix: latest base B rather than initial A; failure is in
/tmp/school-notes-r4-n409-multiple-before.log. Root separately reports actual
local Git/no-write/blocked-capture reproductions in its own receipt.

All names below are in tests/test_review_r4.py unless stated otherwise. Tests
use real temporary Git repositories/commits/pushes and explicitly controlled
agent/Drive/renderer/GitHub fixtures. They do not prove production capability.

| ID | Disposition and implemented boundary | Regression |
| --- | --- | --- |
| N4-01 | Confirmed/fixed. perform_effect accepts a mutation-free preflight before inflight and immediately before execute; failed checks preserve planned state and old receipt. PreconditionFailed is reserved for a known unstarted effect mutation. Actual command/write exceptions remain unknown. Last-check WindowExhausted retains its type. resume-effects records authoritative full remote absence as planned with prior receipt preserved. Explicit rebase permits a verified local commit absent from current remote history, only planned pushes and no interrupted/verified push, retaining old commit/effects/worktree/answers/reviews and renewing all gates. | test_N401_prewrite_ack_failure_stays_planned_and_local_commit_can_rebase (actual window boundary after commit, external human push, exact direct-admin closure, pre-push block, rebase and completion); test_N401_last_prewrite_failure_restores_planned_not_unknown; test_N401_last_preflight_window_failure_is_planned_and_keeps_exception_type (zero writes); test_N401_exact_remote_absence_resolves_unknown_push_without_erasing_receipt. |
| N4-02 | Confirmed/fixed. source/external/public chunks all carry exact comparison_context; external includes changed/dependent teaching text, Source summaries and proposed manifest diff, public includes public source text. Exact result context marker and post-result byte hashes are required; same 64-file/configured byte bounds block oversized context. External visual reuse requires the same comparison context, preventing an old output closure from concealing new source/teaching content. | test_N402_external_and_public_chunks_bind_complete_text_context: five source images in three chunks for each phase, each with full text/hash. Existing R306 context-negative/size tests still enforce refusal; R1 affected-summary/external rehydration integration remains green. Native semantic/vision judgment remains unproven. |
| N4-03 | Confirmed/fixed supported already-verified continuations; qualified for unverified work. Ingest push uses fresh pinned main Git to reconcile before constructing old candidate Git; verified receipt completion performs no old candidate Git. External/public verified-push continuation reads frozen source/artifact/review bytes and fresh main Git, without trusting changed old metadata. Pending unverified external/public worktrees cannot silently acquire a new identity: README documents finish/reconcile/close/fresh-review maintenance. Old candidate distrust and public approval remain intact. | test_N403_verified_ingest_push_finishes_after_common_config_change; test_N403_external_verified_push_reentry_avoids_old_git_after_config_drift; test_N403_published_job_survives_config_drift_without_old_candidate_git (traps any old candidate subprocess, one release and one dispatch). Unverified metadata changes are an explicitly unsupported automatic continuation, with preserved direct-admin closure/review paths. |
| N4-04 | Confirmed/fixed. Central process gate refuses quota_block before any phase; State.update_job preserves retry_wait during queued/running rescheduling. Admin approvals, retry-render and reconciliation cannot clear the flag. Only exact clear-quota direct-admin elapsed-reset evidence does. Rebase retains quota reset evidence as well as the block and old audit records. | test_N404_quota_gate_blocks_rescheduled_job_before_agent_or_renderer; test_N404_render_rescheduler_preserves_quota_wait_until_explicit_clear. Existing attempt/clear-quota tests remain unchanged. No quota inferred from local tokens. |
| N4-05 | Confirmed/fixed. Whole-package MIME/extension/known-size preflight precedes directory/progress allocation. Already reusable bytes undergo signature validation before any new directory, including partial invalid captures. Metadata-known unsupported inputs remain on Drive with complete private inventory; earlier real staging remains retained. Only actually existing staging directories enter retained_staging. | test_N405_unsupported_middle_file_does_not_allocate_repeated_staging: four observations, zero folders/downloads for middle HEIC, one stable blocker. Existing test_SN05_repeated_unsupported_capture_reuses_preserved_bytes verifies repeated invalid signatures reuse captured bytes. R312 fixture now creates genuine temporary retained directories, replacing its former nonexistent synthetic paths. |
| N4-06 | Confirmed/fixed. Stale questions stay in the private database with their answers; current status hides them after current revision completion/closure/rejection. reject-package and close-job close stale rows without deleting answers. README says answer current revision's question or explicitly reconcile retained earlier evidence. | test_N406_stale_questions_hide_after_current_completion_and_close_retains_answers; test_N406_manual_close_closes_stale_rows_preserving_answer. R316 eligible target/wait-state and preserved-answer tests remain green. |
| N4-07 | Confirmed conditional transform defect; proposed blanket attribute rejection rejected as overbroad. Shared * text=auto eol=lf legitimately applies to ordinary binary sources and was preserved. Source filter/working-tree-encoding attrs block before staging/invoking the source filter. Exact index blob byte membership is checked before commit; actual normalization difference raises a known no-commit precondition failure. Post-commit/reconcile source verification remains. No shared .gitattributes change. | test_N407_filter_rejects_before_writer_or_executable_filter_runs uses an actual configured source-filter canary, which never runs; test_N407_text_auto_binary_allowed_actual_normalization_blocks_before_commit allows real PNG bytes with shared attrs and rejects text-like synthetic PDF normalization without a commit. This tests Git byte preservation, not validity/vision of that synthetic PDF. |
| N4-08 | Confirmed/fixed. Git.changes checks ignored untracked wiki/docs output; candidate/commit gates therefore refuse it before render and again before staging. All reviewed private manifest pages/assets must be ordinary exact-byte index blobs before commit and committed blobs afterward/reconciliation. Public source manifest membership is checked before a new public manifest push. Source target containment is additionally checked before copying. | test_N408_ignored_generated_wiki_asset_blocks_before_render; test_N408_manifest_tree_gate_rejects_missing_or_changed_ordinary_blob. R308 existing source tree test separately proves source blobs. Renamed the misleading R308 ignore-only test to test_R308_ignored_source_blocks_before_agent, matching its actual assertion and R3 citation; tree proof belongs to test_R308_exact_commit_blob_membership_requires_present_matching_source. |
| N4-09 | Confirmed/fixed, including root's multiple-push edge. Init persists immutable initial SHA. Initial acknowledgement binds that SHA (legacy pending DB uses saved initial manifest), retains later observed SHA and does not close later changes. Unacknowledged observe_git always diffs from immutable initial A, never the advancing observed B. Already acknowledged range behavior is unchanged. Missing initial evidence blocks rather than guessing. | test_N409_initial_ack_preserves_newer_observed_external_range now covers real A->B->C pushes before ack: latest range A->C contains both changes, initial ack A preserves observed C, controlled independent external review/finalize then closes the full range. Separate failing-before multi-push log retained. |
| N4-10 | Confirmed finite timeout/documentation gap; detached escape claim remains conditional. README documents 2875s child limit for default 3000s run, saving before limit and unsupported detached/background/setsid processes. Interactive SIGTERM grace defaults to 2s, configurable 0.05..10s, then SIGKILL. Automated agent grace unchanged. No promise to manage detached descendants. | test_N410_interactive_finite_grace_allows_sigterm_save runs an actual signal handler that needs 0.1s to save during 0.3s grace, then checks retained file and timeout receipt. Existing real TTY/interrupt/child cleanup tests remain green. Native isolation/FD remains a deployment gate. |
| N4-11 | Confirmed/fixed. Before source_review/render/review/commit, current package candidate base must equal current ack; otherwise block with explicit rebase-candidate guidance before a further costly phase. Push retains separate final checks and verified-effect recovery. | test_N411_base_change_stops_before_source_review traps renderer and verifies no source review invocation. R301 candidate creation/push acknowledgement and stale-source regressions remain green. |

R3-17 / R4 inherited-FD discussion remains conditional and unmeasured here.
The lock FD remains deliberately inherited for supervisor-crash exclusion.
No stripping, LOCK_UN, sandbox weakening or positive native boundary proof was
introduced. Root owns actual FD/canary controls and any owner-authorized runtime
resolution. This code does not claim a native gate passed.

The final R4 suite passes 21 cases in 4.654s. The previous R1/R2/R3 focused
suite passed 87 in 23.299s before final documentation/finite-grace/multi-push
updates; the final full suite passes all 142 cases in 23.994s
(/tmp/school-notes-r4-final-tests.log). Python AST parsing (18 files), both JSON
files and CLI help pass. Changed-file hashes are included in the root handoff receipt.
No production ingest or timer is enabled. Remaining gates include actual Drive
visibility (404 on the existing JPG/PDF connection probes), native model/effort/
schema/isolation/vision/FD proofs, production renderer/browser/resource pilot,
initial closure evidence and optional public API/rights/CDN runtime proof.

Final narrow isolation check: root actual VM exec help confirms --ignore-rules.
The author added it to the example worker argv because ignore-user-config is not
independent evidence that user/project allow rules are suppressed. The real
Agent.build_command configuration regression below binds the flag; this does
not attest native rule isolation. Owner rule files/permissions remain unchanged.
The test is test_N4_worker_explicit_ignore_rules_bound_by_real_command_builder;
its missing attempt-number fixture argument was corrected before the final
targeted and full passing runs. This fixture correction changed no runtime behavior.
