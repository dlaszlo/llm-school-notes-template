# R5 author disposition — School Notes V1

Fixed author gpt-6.1-sol/high; token usage and quota unknown (null). No child
agent, provider review, production call or original/ops/VM/auth change. All 29 R4
file hashes matched before edits; exact bytes are retained in
/tmp/school-notes-app-v1-r4-frozen.tar. The complete independent Opus/high R5
reading report was read and checked against the actual code paths.

Tests use real temporary Git and private local files, with controlled agent,
Drive, renderer and public adapters. They do not attest native/Drive capability.
The final eight regressions were also run against the exact R4 archive, not an
approximate historical checkout: /tmp/school-notes-r5-exact-r4-before.log.
All eight fail against R4 (five assertion failures, three errors, 0.970s).
All eight pass against the fixes (1.385s).
The initial test draft used the fixture's PNG signature instead of the pilot's
actual PNG bytes in two equality assertions; those fixture comparisons were
corrected before the final frozen-before and targeted runs. A prior
/tmp/school-notes-r5-frozen-before.log used root's older R3 support snapshot and
is not claimed as exact R4 evidence.
The first full run also exposed an old PDF coverage fixture that replaced PNG
bytes, size and MIME but retained the PNG MD5. Its metadata now contains the
actual PDF MD5; this corrects the fake adapter, without weakening integrity or
page coverage. The changed test_app.py is included in the review handoff.

| ID | Disposition | Evidence in tests/test_review_r5.py |
| --- | --- | --- |
| N5-01 | Confirmed/fixed. Fresh and every reusable original must match current Drive size and MD5 when available. Only integrity-verified bytes enter progress. Suspect old bytes remain private, are ineligible for reuse and trigger fresh download. Signature gating still blocks integrity-verified unsupported files on every reuse, avoiding repeated download/staging for the same unsupported original. download and readback HTTPException become bounded Blocked, with staging/effect retained. | test_N501_short_capture_never_enters_progress_and_retry_downloads; test_N501_every_reused_byte_checks_current_size_and_md5 (same-size corruption as well as size mismatch with exact old snapshot and self-consistent old SHA); test_N501_md5_mismatch_fresh_not_reusable; test_N501_http_incomplete_read_maps_to_bounded_block. Existing repeated unsupported-signature preservation test remains unchanged. |
| N5-02 | Confirmed/fixed. A precise IgnoredOutputs subclass permits only the direct-admin rebase's ordinary-file snapshot path for this blocker. Old bytes including ignored output remain retained/hash-bound; fresh candidate renews all review/approval gates. Other protected-path errors do not receive this exception. Finite five-rebase limit remains. | test_N502_ignored_output_rebase_preserves_bytes_and_completes: actual ignored writer output, actual owner .gitignore maintenance/push, exact direct-admin maintenance acknowledgement, rebase history including ignored SHA, complete fresh candidate, original bytes intact. |
| N5-03 | Ops-owned. Report's production-vs-probe argv parity concern is accepted for root handling. No app proof field was changed or enabled. Native parity/isolation remains unmeasured here. | No author claim of native probe execution. Root owns probe implementation/evidence. |
| N5-04 | Confirmed conditional path defect/fixed. Verified external continuation resolves its manifest-worktree path exactly as the initial Git object, preserving effect target identity. | test_N504_verified_external_reentry_resolves_symlink_jobs_path: real jobs_dir symlink, actual reviewed local manifest commit/push, successful repeated finalize. |
| N5-05 | Ops-use documentation owned by root. Current content answer already queues an eligible job; run-once is the next action. No unnecessary new resume authority was added. | Existing answer/eligibility tests retained. |
| N5-06 | Qualified intentional finite-context limitation. Whole affected directory context is conservative, hash-bound and bounded to 64 files/configured bytes. Oversized external review must block rather than omit dependencies or claim unsupported semantic coverage. Root documents exact direct-admin maintenance closure; no new dependency graph or wider model context introduced. | Existing bounded context/negative coverage tests retained; no claim of a newly implemented graph. |
| N5-07 | Confirmed conditional agent Git-policy mutation/fixed. Any depth .gitattributes/.gitignore basename is protected in candidate changes; existing exact supervisor-config hash exceptions and trusted owner maintenance remain available. Shared ordinary text=auto/eol policy remains untouched. | test_N507_nested_git_policy_files_are_protected checks wiki/subjects/sources/docs nested locations with actual Git, while existing source-filter/raw-blob tests retain common-policy coverage. |
| N5-08 | Deployment ordering owned by root. Migration, fresh observed SHA configuration, init, then exact baseline closure is required. Application's stale configured-SHA init refusal remains appropriate, not weakened. | Existing non-overwrite/init/exact-baseline gates retained. No migration or new closure claim. |
| N5-09 | Confirmed/fixed. Explicit request-public after closed_unprocessed obtains a fresh retry job, retaining earlier direct-admin closure and enforcing unknown/inflight effect guard. New public preview/review/exact approval gates remain. | test_N509_closed_public_new_request_retains_old_job checks distinct new job, old closure intact and authoritative refusal if earlier effects become unknown. |

Inherited lock FD remains intentional and the conditional native threat remains
unmeasured. No LOCK_UN, FD stripping, fake native proof, public approval or Drive
visibility weakening. Full passing results and final hashes are in the handoff
receipt. Root handles the requested ops documentation/probe changes separately.

Final verification: all 150 tests pass in 27.901s
(/tmp/school-notes-r5-final-tests.log). The corrected three-page PDF coverage
test passes alone in 0.501s (/tmp/school-notes-r5-pdf-fixture.log). Python AST
parsing (19 files), both JSON files and CLI help pass. Eight R5 targeted tests
pass in 1.385s (/tmp/school-notes-r5-targeted.log). No native proof is inferred.
