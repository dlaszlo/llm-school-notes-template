# R8 author disposition — School Notes V1

Author fixed gpt-6.1-sol/high; token/quota data unknown (null). Read full
independent Opus/high R8 reading report. All35 R7 hashes matched before edits;
exact /tmp/school-notes-app-v1-r7-frozen.tar retained. Only temporary app files
changed. No subagent, provider/network, original/ops/VM/auth/shared policy,
permission/scope/public/proof/FD change.

| ID | Independently verified disposition | Regression |
| --- | --- | --- |
| N8-01 | Confirmed/fixed. changes() takes exact supervisor-acquisition source name/SHA bindings, validates every bound ordinary copy and rejects every changed unbound sources/ path as CandidateViolation before normalization. Bound copies edited/deleted/symlinked by agent also refuse before source review. OwnerPolicyViolation normalization applies only to exact bound original copies; inherited filter/encoding policy remains owner policy. Prompt forbids all agent sources/ acquisition or edits. Production candidate/commit/rebase callers and controlled transport fixtures pass actual bindings; source-unit tests explicitly bind original names/hashes rather than treating directory prefix as ownership. | test_N801_unbound_agent_crlf_source_is_candidate_repair: actual unbound CRLF note, blocked without owner flag, same-ack snapshot rebase, fresh complete; old bytes retained. test_N801_agent_altered_bound_source_stops_before_review_and_repairs: altered acquired bytes block at candidate before source review, same-ack fresh complete, altered old snapshot retained. |
| N8-02 | Confirmed/fixed. Admin checks current policy using exact immutable captured bytes before checking stale owner flag. Still-bad policy refuses without allocation/budget. Same-ack repaired-owner rebase requires nonempty exact source evidence and successful current policy preflight; repair reason/prior failure retained. Successful candidate source+ordinary-change guards move stale flag into owner_policy_recoveries before the next agent call. Recovery audit survives rebase; old source/candidate files remain. No fake external commit or proof/memory/permission change. | test_N802_info_policy_same_ack_repaired_preflight_allows_fresh_rebase: real noncommitted common info/attributes filter, repeated refusals with identical payload/worktree count, actual owner repair, fresh same-ack rebase and complete. test_N802_resume_clears_stale_owner_flag_before_later_agent_violation: repaired old candidate resumes, clears flag into audit before real tracked-page deletion, then same-ack fresh repair and complete retaining audit. |
| N8-03 | Root owns ops use-doc maintenance sequence. App README now names committed maintenance/ack and verified noncommitted repair paths, and supervisor-only acquisition. | No new CLI/approval workflow or author ops edit. |

Before run /tmp/school-notes-r8-before.log was executed while all35 original R7
source/support-test hashes matched, before adapting old controlled helpers. Four
new cases fail (three assertions, one error, 1.041s). It is the exact guarded R7
evidence; no later run with an incompatible new helper signature is claimed as
historical proof. R7 bound synthetic source test and R4 bound source/index test
retain original-byte/no-rewrite and final commit refusal assertions. Changes to
old controlled helpers only supply supervisor acquisition bindings; they do not
supply native proof or auto-review acceptance.

Owner source bytes are never rewritten to appease Git. Same-ack fresh-worktree
repair copies no violating agent file forward. Acquisition SHA/index/commit
checks, finite rebase/effect/attempt gates and all inherited lock-FD/native
controls remain. Root separately owns deployment/pilot data migration and runtime
proof procedure. No code acceptance replaces those production gates.

First-handoff full suite passed all170 in 45.162s
(/tmp/school-notes-r8-first-handoff-tests.log). Expanded targeted nine cases pass in
5.981s (/tmp/school-notes-r8-targeted-expanded.log); four new alone pass in
3.685s. AST22 Python files, JSON2 and CLI help pass. Final hashes accompany the
write-stop handoff; native/runtime acceptance remains unready.

Pre-R9 root edge confirmed independently: a wiki-only inherited filter leaves
the immutable-source policy preflight passing, but candidate.changes still
raises OwnerPolicyViolation. Same-ack refusal in that exception is now
unconditional; a source-only success cannot prove a wiki policy repaired.
test_N802_wiki_owner_filter_source_preflight_passes_no_same_ack_retry proves
actual source-policy success and three unchanged payload/worktree refusals.
It failed before the one-line correction (Blocked not raised, 0.389s;
/tmp/school-notes-r8-wiki-owner-before.log). The first37-file R8 handoff is
preserved in /tmp/school-notes-app-v1-r8-first-handoff-frozen.tar; its170-test
result above is superseded by the final171-test result in the updated handoff.

Updated final full suite passes all171 in 56.061s
(/tmp/school-notes-r8-final-tests.log). Final targeted ten cases pass in 5.788s
(/tmp/school-notes-r8-targeted-final.log): five new R8 cases and five retained
source/recovery cases. These results cover the wiki-only owner-policy correction.
All original receipts and the first handoff remain preserved; updated exact
hashes accompany the final write-stop handoff. Actual tokens/quota are unknown.
