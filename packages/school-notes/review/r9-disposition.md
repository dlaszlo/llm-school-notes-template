# R9 disposition — fixed author gpt-6.1-sol/high

Scope: packages/school-notes only. Exact37 R8 hashes were checked before edits
and preserved in /tmp/school-notes-app-v1-r8-frozen.tar. No production, credentials,
shared policy, permissions, native proof or public gate changes. Tokens/quota unknown.

| ID | Disposition and evidence | Regression |
|---|---|---|
| N9-01 | Confirmed by execution. Wiki-only inherited filter plus common Git config drift bypassed the old candidate guard and allocated a retry. OwnerPolicyViolation now carries its exact relative path; the supervisor persists it. Fresh pinned main checks current attributes at that path before any old candidate Git, drift snapshot or retry. Exact immutable-source policy preflight remains required. A legacy same-ack owner marker lacking its failing path refuses conservatively pending acknowledged maintenance. Existing candidate Git identity is never silently trusted after drift. | test_N901_wiki_filter_config_drift_refuses_before_retry_then_repair: actual committed wiki filter, blocked candidate, real common config drift, three refusals with unchanged payload/worktree count/model-call count; actual noncommitted wiki attribute override then fresh same-ack completion, one retained history. Failed before: Blocked not raised. |
| N9-02 | Confirmed by execution for missing page and branding. Existing private manifest schema, page/asset containment and bytes, branding path/signature/bytes are validated before candidate directory/worktree/model. Stored hashes are refreshed only in the validation copy; no equality demand or owner manifest mutation. Failure is explicit Blocked requiring owner maintenance. Root owns initial private migration/deployment sequence. | test_N902_missing_existing_page_blocks_before_worktree_or_model and test_N902_missing_existing_branding_blocks_before_worktree_or_model: real owner manifest commits and exact baseline ack; blocked at candidate, no candidate/source-review call, no worktree or owner manifest changes. Both failed before at source_review. |
| N9-03 | README corrected: current failing-path attributes plus immutable-source checks decide repaired-owner same-ack rebase; resume remains available with matching candidate metadata identity and existing question/quota/current-revision gates. Root owns use.md. | Existing R8 resume/recovery tests retained unchanged and passing. |
| N9-04 | Qualified boundary observation, not a new fix: sources are writable within the candidate workspace; supervisor acquisition bindings and post-call CandidateViolation enforce the existing integrity gate. No unmeasured native sandbox enhancement or claim. | Existing R8 unbound/modified-source cases retained unchanged. |

Before: /tmp/school-notes-r9-before.log,3 tests,3 assertion failures,1.081s,
against the exact preserved R8 implementation plus new test file. Reviewer did
not execute tests; this before/after evidence is author execution, not reviewer
execution. Targeted /tmp/school-notes-r9-targeted.log:12/12,9.682s (3 new R9,
5 R8,4 R7). Source byte preservation, no filter execution before rejection,
finite rebase limits and inherited lock-FD/proof gates remain unchanged.

The N4-01 deterministic commit-effect nit remains: conservative unknown effect
on refusal is preserved rather than expanded in this focused scope. Review
statements about root-owned deployment/native proof procedure are conditional
review observations; app acceptance does not certify those external gates.

Final verification:14 targeted cases pass in7.953s
(/tmp/school-notes-r9-targeted-final.log), all174 tests pass in74.096s
(/tmp/school-notes-r9-final-tests.log), AST23 Python files and JSON2 parse pass.
The first full run exposed an introduced variable collision: the existing source
lookup reused the earlier loaded manifest variable on repeated-source cases.
It is corrected with a dedicated existing_manifest binding for validation,
merge and manifest diff. The failed full receipt (4 failures,3 errors,68.159s)
is retained in /tmp/school-notes-r9-first-full-failed.log; old metadata-update and
public recovery tests detected it without weakening expectations. No old test
files changed in this round. Final exact hashes accompany the write-stop handoff.
