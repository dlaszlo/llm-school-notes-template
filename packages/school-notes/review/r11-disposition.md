# R11 disposition — fixed author gpt-6.1-sol/high

Scope packages/school-notes only. All41 exact R10 hashes were checked and
preserved in /tmp/school-notes-app-v1-r10-frozen.tar before implementation edits.
No production, permissions, shared policy, native proof, public or lock-FD changes.
Actual tokens/quota unknown.

| ID | Disposition and actual evidence | Regression |
|---|---|---|
| N11-01 | Confirmed/fixed at actual Agent.call validation boundary. Only bounded manifest-string parse/schema failures raise InvalidManifestProposal after envelope/review/context validation. Bound-input immutability checks run first. Agent.call preserves failed attempt/result hash and carries exact result path/id; candidate retains raw string and failed-attempt binding, then raises CandidateViolation. Shared agent_manifest parses the raw string within its own guard, so admin can revalidate and renew same-ack without accepting invalid content. Failed attempt remains counted in its original phase; existing finite rebase/new-phase design applies, no limit exception or quota reset. | Actual Agent.call transport tests for unknown page field and malformed manifest JSON: blocked at candidate, no source-review, failed attempt hash matches retained raw result, explicit same-ack preserved rebase and fresh completion, original failed and new complete phases retained. Actual wrong hash/context and mutated trusted-policy transport controls remain plain blocked with no invalid-proposal persistence. Standalone wrong review/context/hash validation remains plain Blocked. Gate/transport mocks are synthetic offline tests, not live provider evidence. |
| N11-02 | Confirmed/fixed. New unsafe candidate names absent from the owner base become CandidateViolation; inherited unsafe names remain explicit owner-maintenance Blocked. Fresh-main ordinary owner preflight skips only unrepresentable new names that the preserved snapshot/fresh rebase quarantines; inherited unsafe names still refuse. No filename normalization, old Git trust or source-byte rewrite. | New backslash filename blocks then same-ack fresh completion; original bytes/name/hash retained in history, absent from fresh candidate. Same preservation/recovery after real owner filter repair plus common Git config drift. Inherited unsafe owner filename refuses both candidate and preflight and preserves owner bytes. |
| N11-03 | Strengthened R10 partial-policy assertion from generic wiki/ to next wiki/math/ path and explicitly excludes the first repaired log path. README names manifest-only adapter recovery and unsafe-name ownership distinction; root owns use.md. | Existing R10 behavior test strengthened; no prior expectations weakened. |
| N11-04 | Optional batching deferred. Current attribute checks are bounded subprocesses under existing run window; few actual changed pages. No correctness or proof claim added. | Existing affected-path and no-allocation coverage retained. |
| N11-05 | Root owns cleanup receipts/use docs/journal. Exact app freezes, hashes, review receipts and author logs preserved. No author cleanup. | No app behavior change. |

Before /tmp/school-notes-r11-before.log:9 cases,6 failures,2 errors,1.871s
against an isolated exact41-hash R10 extraction, corrected new R11 tests and
byte-identical prepare_photo support. Wrong envelope already passes. Initial
fixture diagnostic retained separately: its mutated-policy control lacked a
trusted policy file. Corrected control commits real synthetic owner AGENTS and
acknowledges that fixture before the actual call; initial IndexError is not
claimed as app evidence. Reviewer executed no tests; author before/after checks
are not independent reviewer execution.

Targeted26/26 pass21.393s (/tmp/school-notes-r11-targeted.log):9 new R11,
5 R10,3 R9,5 R8,4 R7. R10 test modification tightens the next-path refusal
assertion only. Source/bundle integrity, public approvals, raw private context
separation, finite attempt/quota/rebase gates and original receipts remain.
The conservative N4-01 effect nit remains outside this focused scope.

Final full188/188 pass67.835s (/tmp/school-notes-r11-final-tests.log).
AST25 Python files and JSON2 parse pass. Exact final file hashes accompany
stable write-stop handoff; no production gates are certified by these checks.
