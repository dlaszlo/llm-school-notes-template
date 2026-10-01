# R14 disposition — fixed author gpt-6.1-sol/high

Scope: packages/school-notes in the isolated /tmp stage only. R13's exact 49 files
remain in /tmp/school-notes-r13-frozen.tar and its original hash manifest; root
also preserved /tmp/school-notes-r14-before.tar. No provider, credentials, VM,
original checkout, permission, shared-policy or proof flags changed. Tokens and
quota are unknown (null). The independent reviewer read code; author execution
below is separate evidence, not reviewer execution or native/provider proof.

| ID | Verified disposition and regression |
| --- | --- |
| N14-01 | Fixed. Joined CLI retains strict Busy before recovery/job mutation. Standalone run-once excludes dirty/ahead/diverged learners with categorized Git blockers before scoped recover/retry/observation/processing. Excluded jobs, attempts and inflight effects remain unchanged; healthy learner completes. Clean-behind is allowed and normally fast-forwarded by Git.inspect. `test_N1401_standalone_dirty_learner_keeps_all_jobs_and_other_proceeds`, `test_N1401_clean_behind_checkout_fast_forwards_and_processes`; existing real joined dirty-session test retained. |
| N14-02 | Fixed. Provisional registration never supersedes another job; ready registration cannot supersede jobs with accepted reviews. Returning to the original committed range retains its accepted review_wait bytes/state. `test_N1402_provisional_and_ready_new_range_preserve_accepted_job`; existing same-key promotion/dedup tests retained. Preserved acceptance cannot authorize finalizing an obsolete remote range. |
| N14-03 | Fixed through the existing direct-owner acknowledge-maintenance route, with no new authorization verb. Only the observer registers divergence_maintenance: exact old ack/current clean-pushed HEAD, committed-tree changes and merge_base (SHA or null for unrelated available histories). Manual job never enters models, even if queued via an ordinary continuation. Closure revalidates endpoints, history relation, full changes, valid manifest impact and nonempty hash-bound closed records. It records direct-owner maintenance, never accepted model review. Normal register_external/wrapper ancestry remains strict. `test_N1403_divergence_observer_only_exact_manual_closure` uses real local force-pushed bare Git; invalid merge-base refuses closure. Missing old endpoint objects remain an explicit owner-restoration blocker, not guessed closure. |
| N14-04 | Fixed. Maintenance compares Git.committed_changes against the registered map, never follows filesystem symlinks. Nonordinary/deleted entries remain null. `test_N1404_symlink_maintenance_uses_committed_tree_none`. This does not permit renderer manifest pages to be symlinks. |
| N14-05 | Fixed. Finalization requires review_wait; complete reentry requires the exact job's already verified manifest-push effect. closed_unprocessed/superseded/rejected and unjustified complete are refused before Git/effects. `test_N1405_finalizer_refuses_closed_superseded_rejected_before_git`; older interrupted/verified finalization recovery tests retained. |
| N14-06 | Fixed. Last public push preflight also requires clean main HEAD == freshly fetched origin/main. A late owner commit leaves the planned push unexecuted and remote unchanged; preview/approval/evidence retained. `test_N1406_public_last_prewrite_rejects_local_unpushed_commit` exercises actual local Git with fake public transport, never live publication. |
| N14-07 | Fixed. Stable block keys/payloads distinguish git/drive; successful observation clears only its own category. Legacy uncategorized blockers are conservatively retained, rather than falsely proven repaired by Drive. Sync describes behind checkout explicitly and does not merge it. `test_N1407_drive_success_retains_git_block_and_clears_only_drive`. |
| N14-08 | Fixed supported userspace case; D-state limitation remains. Parent supplies absolute system monotonic deadline before Popen, guardian refuses expired/dead-parent startup, and parent SIGTERM allows four seconds for the guardian's two-second cleanup plus reserve before a last-resort group kill. Failure is blocked, not claimed cleanup success. `test_N1408_absolute_deadline_cleans_delayed_guardian_sigterm_ignoring_worker` reproduced an actual orphan before and cleaned it explicitly; fixed delayed startup does not start expired work. `test_N1408_parent_timeout_signals_guardian_and_waits_cleanup_reserve` tests the parent's timeout branch with a controlled process object. Existing actual controller-SIGKILL/separate-grandchild and inherited-operation-FD tests remain. Uninterruptible kernel tasks cannot be claimed killed by these tests. |
| N14-09 | Fixed. Every outer Codex event/result and Claude wrapper parse maps RecursionError to plain Blocked within failed-attempt recording. Raw files remain, failed result SHA is recorded when ordinary result bytes exist, malformed outer envelope is never invalid-manifest authority, and later queued work proceeds. `test_N1409_outer_deep_result_blocks_attempt_and_other_job_proceeds`, `test_N1409_deep_codex_event_and_claude_wrapper_are_failed_bounded_attempts` use the actual Agent.call validation boundary with synthetic transports. No successful API schema/proof claim. |
| N14-10 | Conditional hardening deferred as root directed. Ancestry remains cooperative same-UID provenance, not authorization; finite workers receive no session marker/guard. App-state denial and FD17 are unmeasured production gates, never bypassed or marked passed. No cmdline-only security claim or inherited-lock stripping added. |
| N14-11 | Performance optimization deferred as root directed. Every Git subprocess keeps the independent guardian and integrity gates. Existing synthetic overhead measurements are not VM capacity evidence; root owns real VM window/RAM/disk measurement. No speculative plumbing bypass/cache added. |
| N14-12 | Fixed prompt -B and UV_OFFLINE=1 without new entrypoints or global rules. README clarifies authorization only after session exit, default agent timeout plus five-second reserve and preparation overhead, interrupted-attempt accounting, scheduled learner exclusion, range preservation and exact manual divergence closure. Other Info caveats remain: full-tree private snapshot cost/opaque names, replaced guard inode fail-closed recovery, unsafe committed owner filenames requiring maintenance. Their broader redesign is intentionally deferred. `test_N1412_controller_guidance_disables_bytecode_and_network_dependency_resolution`. Root owns ops runbook and activation docs; its appended learner-block/retraction contract was read and matches the implemented merge_base/committed-map semantics. |

Before execution: /tmp/school-notes-r14-before-tests.log reproduces the accepted
source defects; its initial N01 config-loader and N06 approval-fixture mistakes
were corrected and rerun separately in /tmp/school-notes-r14-before-fixture-corrected.log.
The original N09 "following job" fixture inserted that job too early; corrected
ordering observes the ingest first and queues later work afterward. Corrected
extra parse/cleanup probes against extracted R13 code (running from /tmp so
current cwd cannot shadow old source) are in
/tmp/school-notes-r14-additional-before-corrected.log. The earlier additional-before
log accidentally imported current cwd and is diagnostic only, not before evidence.

First fixes: 10/10 passed, 24.477s (/tmp/school-notes-r14-targeted.log).
Expanded diagnostic run passed 29 cases with two fixture-selection errors
(parent mock's already-finished wait and a mistyped historical test name).
Both were corrected. Final corrected focused run passed 14/14, 29.968s
(/tmp/school-notes-r14-corrected-targeted.log); the final guardian expired-start
check is covered again before full acceptance. Existing interactive real-process
and both interrupted-external-finalization tests passed in the expanded run.
Full stable suite/result and final source guard are recorded in the final handoff.

Production gates remain unchanged: actual Drive read visibility unproven;
all native model/schema/sandbox/FD17 and protected-owner-session probes require
root's actual measurement. Synthetic transport/process tests never enable them.
No DB, timer, public credential/permission or live content mutation was performed.

Final verification (root-authorized partition): full invocation ran 221 cases in
885.841s, with 220 passing and one historical SN08 assertion failure; it was NOT
a green full invocation. SN08 now separately asserts the earlier terminal-state
refusal and preserves acknowledged-base refusal on an eligible review_wait job.
The corrected case passed 1/1 in1.624s. SHA verification proves only that test
(and this result annotation) differs from the full-run guard; every product,
role, config and other test byte is identical. Root explicitly accepted this
bounded partition instead of repeating the entire unchanged implementation suite.
All logs, original expectations, before archive and full-run source guard remain.
Final hashes and write-stop are in /tmp/school-notes-r14-handoff.json.
