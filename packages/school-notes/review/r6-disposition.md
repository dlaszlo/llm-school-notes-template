# R6 author disposition — School Notes V1

Fixed author gpt-6.1-sol/high; tokens/quota unknown (null). Complete Opus/high R6
reading report checked against code. All31 R5 hashes matched before edits;
exact /tmp/school-notes-app-v1-r5-frozen.tar and prior hashes are preserved.
Only temporary app files changed: no child agent, provider call, shared helper,
original checkout, ops/VM/auth, scope, ACL or permission change. Native proof
flags remain unready. Local tests are controlled adapters plus actual Git/files,
not production capability evidence.

| ID | Verified disposition | Tests in test_review_r6.py |
| --- | --- | --- |
| N6-01 | Confirmed/fixed. CandidateViolation includes protected/disallowed paths, deletion/symlink, ignored generated output and transforming attributes/normalization. Exact direct-admin rebase records ordinary old file hashes/reason, at the same current clean ack if necessary, and creates a fresh candidate; violating bytes are never carried forward. Existing five-rebase/effect/current revision gates remain. Prompt explicitly forbids deletion/rename/symlink, policy mutation and disallowed writes; requires LF. | test_N601_deleted_candidate_rebase_same_ack_preserves_and_completes deletes an existing tracked index page, records the actual blocker, same-ack rebase and full completion; old deletion/log bytes retained. test_N601_candidate_violation_classes_cover_paths covers protected/disallowed/symlink/deletion classes. Existing R5 ignored snapshot recovery remains. |
| N6-02 | Confirmed/fixed. Exact base key and retry-prefix family checked together; any family unknown/inflight effect refuses the request before returning/creating jobs. Active retry returned idempotently, all earlier jobs retained; completed existing proposal is also not duplicated. | test_N602_active_retry_idempotent_and_all_family_unknown_guard. |
| N6-03 | Confirmed/fixed. GitHub API including response reads/redirected downloads and live GET map HTTPException to bounded Blocked. Actual interrupted mutation still becomes unknown under perform_effect. Shared drive_media.request was read: HTTPError/URLError/TimeoutError only, so app DriveAPI.request now maps HTTPException for writer and inherited reader; shared bytes unchanged. | test_N603_github_http_exception_preserves_unknown_effect covers API mutation and live read; test_N603_drive_request_http_exception_bounded_without_shared_change covers legacy-helper boundary. No real network/auth call. |
| N6-04 | Confirmed/fixed. Interactive finally always attempts bounded group/child/terminal cleanup separately, retaining cleanup failures. Fresh owner Git records identity drift instead of reusing a stale pinned object. Inspection/enqueue errors are recorded; receipt persists before enqueue, preserving original child exit/timeout. Invalid metadata may leave only a recorded receipt for direct repair, not a fictitious review. | test_N604_wrapper_records_metadata_drift_and_original_exit; test_N604_wrapper_cleanup_error_still_records_exit_and_failure. Existing timeout/SIGTERM/TTY/descendant/dirty receipt tests remain. This trusted owner wrapper does not relax worker identity gates. |
| N6-05 | Confirmed conditional exact-byte defect/fixed. Raw tree/file/mode comparisons discover changes without a working-tree Git diff, which can execute clean filters. Only after filter/encoding refusal does hash-object compare normalization against raw bytes. Every reviewed changed ordinary file and copied review record is checked in index/commit/reconcile; manifest/source gates remain. Only exact reviewed names are staged, with unexpected existing index entries blocked and preserved. | test_N605_nonmanifest_crlf_blocks_before_source_review_then_rebase; test_N605_every_changed_blob_verified_and_filter_never_executes; test_N605_nonmanifest_index_blob_must_match_reviewed_bytes; test_N605_nonmanifest_committed_blob_reconcile_rejects_normalization; test_N605_unreviewed_index_entry_blocks_without_reset. |
| N6-06 | Confirmed documentation mismatch/fixed. README now describes preserved snapshot/fresh candidate recovery at same clean ack for all CandidateViolation types, without falsely requiring owner maintenance for a writer mistake. Invalid inherited owner attributes/ignore policy still require owner maintenance; no old violating bytes are imported. | Same-ack deletion and prior ignored-output integrations. |
| N6-07 | Qualified Info/performance. Full integrity rehash gates kept. No unproven inode/mtime cache or silent reduction of integrity checks. Actual pilot measurements still pending. | R5 integrity/unchanged-reuse tests retained unchanged. |

The final source-filter regression builds the Git object after configuring the
filter, so it does not accidentally pass merely from metadata identity drift.
The final deletion regression uses a tracked baseline index page, not a newly
untracked lesson. Earlier draft before logs are retained but superseded by the
exact R5-archive before run. The older R4 normalization test now asserts the
stronger candidate violation first, then bypasses only that changes() gate to
retain its independent final staged-source-byte test; it was not weakened.

Root owns D2 diagnostic failure receipt and ops deployment/current-SHA/baseline
interactive documentation. D1 inherited-FD issue remains conditional/unmeasured;
no stripping, LOCK_UN, scope/public/proof relaxation. Schema, actual runtime,
Drive visibility, renderer/browser/resource pilot and public gates remain.

Final evidence: 12 corrected regressions against exact R5 all fail (six assertion
failures and six errors, 1.307s; /tmp/school-notes-r6-exact-r5-before.log).
Those 12 plus the retained older staged-source test pass in 2.800s
(/tmp/school-notes-r6-targeted-expanded.log). Full final suite passes all162 in
47.867s (/tmp/school-notes-r6-final-tests.log). AST20 Python files, JSON2 and CLI
help pass. Final changed-file hashes accompany the write-stop handoff.
