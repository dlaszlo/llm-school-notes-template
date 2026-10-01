# R10 disposition — fixed author gpt-6.1-sol/high

Scope only packages/school-notes. All39 exact R9 file hashes were verified and
preserved in /tmp/school-notes-app-v1-r9-frozen.tar before implementation edits.
No shared policy, original roots, production, auth, public, native proof or
inherited lock-FD changes. Actual tokens/quota unknown.

| ID | Verified disposition | Regression |
|---|---|---|
| N10-01 | Confirmed/fixed. Shared agent_manifest validates merge constraints, private mode and every proposed contained file before source review, mapping invalid proposals to CandidateViolation. Supervisor persists raw proposal and result path first. Admin rechecks that proposal inside the candidate violation/snapshot guard even when Git.changes passes, enabling actual same-ack fresh recovery. Old proposal/result path are retained in history; invalid proposal does not pass into renewed payload. | Three cases: missing page, non-wiki entry, existing tracked symlink proposed as a page. Each blocks at candidate before any source-review call, explicit same-ack rebase and fresh completion succeeds, old candidate/result bytes and raw proposal remain. The symlink fixture is existing owner content outside the valid prior selection, isolating proposal validation rather than an agent symlink-write violation. |
| N10-02 | Confirmed/fixed. For owner-policy blockers, fresh pinned main inventories the old base tree and compares raw ordinary candidate blobs without executing old candidate Git. Current main attributes are checked at all changed ordinary paths, plus recorded failing path and immutable bound source preflight, before snapshot/allocation. Executable filters/encoding are rejected by attribute inspection without execution. Remaining failing path appears in the refusal. | Actual wiki-wide filter, only first failed path repaired in noncommitted owner info/attributes, real common config drift, three unchanged payload/worktree/model-call refusals; full owner repair then same-ack fresh completion. |
| N10-03 | Legacy path-less same-ack owner refusal already implemented; verified with three unchanged refusals after config drift. README now states all affected paths and invalid-proposal recovery. Existing identity condition on resume remains; root owns use.md qualification. | test_N1003_legacy_pathless_same_ack_refuses_without_allocation passes before and after. |

Before /tmp/school-notes-r10-before.log:5 tests,4 assertion failures,1.754s,
exact R9 implementation plus new R10 tests; legacy case already passes.
Initial fixture diagnostic is retained separately: an unsupported title field
and agent-added symlink tested different gates; corrected before implementation
edits to valid schema and existing owner symlink, without historical source
changes. Reviewer did not execute these tests; before/after evidence is author
execution. No older test file or expectation changed in this round.

All existing source byte gates, protected owner config rules, finite five-rebase
limit, preserved snapshots/answers/reviews and production proof gates remain.
The conservative N4-01 commit-effect nit remains outside this focused fix scope.
External deployment/probe assertions in the review are conditional observations;
no local passing test is a live provider or Drive proof.

Final targeted17/17 pass11.846s (/tmp/school-notes-r10-targeted.log):5 R10,
3 R9,5 R8,4 R7. Final full179/179 pass64.183s
(/tmp/school-notes-r10-final-tests.log). AST24 Python files and JSON2 parse pass.
Exact final hashes accompany stable write-stop handoff; quota/tokens unknown.
