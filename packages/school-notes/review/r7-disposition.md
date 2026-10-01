# R7 author disposition — School Notes V1

Author fixed gpt-6.1-sol/high; tokens/quota unknown (null). Read the complete
Opus/high R7 reading report. All33 R6 hashes matched before editing; exact R6
archive /tmp/school-notes-app-v1-r6-frozen.tar preserved. Only temporary app
source/docs/tests changed. No provider/subagent, original/ops/VM/shared helper,
auth/scope/ACL/permission or runtime proof change.

| ID | Verified disposition and limits | Evidence |
| --- | --- | --- |
| N7-01 | Confirmed/fixed. Drive helper construction/token refresh HTTPException maps to bounded Blocked. Both writer and optional inherited readonly path use this catch; no credential change, fallback login or token-content logging. | test_N701_constructor_refresh_interruption_writer_and_reader_bounded uses a controlled temporary helper whose constructor raises IncompleteRead. Synthetic proof only in offline fixture; production proof flags untouched. |
| N7-02 | Confirmed/fixed. OwnerPolicyViolation is separate from CandidateViolation: inherited filter/encoding policy and exact copied-source normalization require owner maintenance, observed external range and exact acknowledge-maintenance before rebase. Durable owner_policy_failure makes same-ack refusal happen before old candidate access or retry allocation, including metadata drift. Current acknowledged policy is preflighted using immutable captured source bytes before any new worktree. After corrected changed ack, old ordinary snapshot/capture/receipts remain and a fresh candidate renews gates. Agent protected writes and agent text normalization retain finite same-ack snapshot repair. | test_N702_owner_filter_same_ack_refuses_no_budget_then_maintenance_completes checks three refusals with unchanged payload/worktree count even after real Git config drift, then actual owner attribute commit/push, exact direct-admin maintenance ack, rebase and complete; old source hashes intact. test_N702_inherited_attributes_owner_error_agent_policy_write_candidate_error distinguishes actual inherited encoding attrs from protected agent policy writes. |
| N7-03 | Qualified deployment-only attribute risk; no broad LFS/encoding support added. Root reports actual attribute audits: Barna894 and Benedek1373 tracked files, no filter/working-tree-encoding/ident transformation. These are root observations, not author-executed native proofs. Any inherited unsupported transformation still blocks explicitly. | Root owns actual receipt and deployment verification; app tests prove conservative policy gate, not production checkout audit. |
| N7-04 | Root selected documented behavior (c). Trusted interactive metadata drift is recorded; later fresh jobs use updated owner Git configuration. Older pinned candidates reject drift. README states this accurately. No imposed owner approval or new permission flow. | Existing R6 real interactive config-change receipt test retained unchanged. |
| N7-05 | Qualified exact-byte claim to private ingest/metadata and external manifest commits. Public supervisor writes use their existing LF JSON/readback/approval gates; no public feature expansion or false claim of new public index gate. README now names the actual paths. | Prior R6 all-blob index/commit/reconcile tests retained; no new public gate proof claimed. |
| N7-06 | Root-owned provenance correction. No launcher/ops file edited by app author. | Root owns actual launcher path/hash and review receipt. |
| N7-07 | Confirmed/fixed with N7-02. Exact source normalization error never says write LF; requires owner Git policy repair and explicitly preserves original bytes. Agent-written text still gets LF guidance. | test_N707_source_normalization_owner_policy_never_suggests_rewrite checks synthetic text-like source PDF bytes unchanged before/after owner binary policy correction; this is a Git byte test, not valid PDF/vision evidence. |

All four corrected new regressions fail against exact R6 (one assertion failure,
three errors; /tmp/school-notes-r7-exact-r6-before.log). Final targeted includes
these plus retained source-index, same-ack deletion and agent-text LF repair
regressions. Older R4 source normalization test now expects OwnerPolicyViolation
at the early gate, then still bypasses only that gate to prove the independent
final staged-source blob refusal. No byte-preservation assertion was weakened.

D1 owner-decision requirement is review inference, not author-verified runtime
behavior. Inherited lock FD and all17 controls remain; none skipped or stripped.
Actual Drive visibility, runtime model/effort/schema/isolation/vision/FD,
renderer/browser/resource pilot and optional public proofs remain deployment
gates. Independent review does not replace them.

Final verification: all166 tests pass in 51.751s
(/tmp/school-notes-r7-final-tests.log). Seven targeted cases pass in 3.194s
(/tmp/school-notes-r7-targeted-expanded.log). Exact R6 before run: four failures
(one assertion, three errors) in 0.250s. AST21 Python files, JSON2 and CLI help
pass. Final hashes accompany the write-stop handoff; no native proof inferred.
