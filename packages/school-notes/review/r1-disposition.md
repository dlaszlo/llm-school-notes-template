# R1 disposition and offline evidence

2026-10-01. Author fixed `gpt-6.1-sol/high`; independent R1 review fixed
`claude-opus-5-5/high`, canonical `gl-reviewer`, 701.44 seconds. No new live
provider/service actions in this fix round. Only the sanitized `/tmp` source
snapshot was edited. Original worktree, shared policy and ops files unchanged.

Every accepted finding below has an implementation change and a regression
reference. Test names are in `tests/test_review_r1.py` unless marked `test_app`.
Local fixtures with synthetic capability booleans are unit-test fixtures,
never provider or deployment proofs. The test command is in README.

| ID | Disposition / concrete change | Regression evidence |
|---|---|---|
| SN-01 | Accepted. Metadata-only requires latest completed same-byte revision; baseline_pending stays pending. | `test_SN01_baseline_description_cannot_create_job`, `test_SN01_metadata_uses_last_closed_revision_not_superseded`; ABA test_app |
| SN-02 | Accepted. notebook/teacher_learn only; configured role mismatch asks a question; whole package gate precedes writes. | `test_SN02_background_and_role_mismatch`; mixed-book test_app |
| SN-03 | Accepted. WindowExhausted queues without retry; EffectPending schedules reconciliation without repeat; ack wakes waiters. | `test_SN03_window_queues_phase_without_retry`, `test_SN03_unknown_receipt_is_retry_pending_and_cannot_fabricate_success`, `test_SN03_ack_wakes_waiting_jobs`; public async test |
| SN-04 | Accepted API contract, no live proof. Persist draft POST ID; GET by ID or full authenticated paginated release list; missing draft remains unknown. | `test_SN04_draft_404_is_unknown_paginated_list_and_saved_id_reconcile`, full public crash test |
| SN-05 | Accepted. Package format/size/empty/changed/loose blockers preserve inventory/staging; other packages and baseline continue. Unsupported repeated capture reuses preserved bytes. Survey transport failure remains incomplete. | `test_SN05_bad_package_does_not_block_good_package_or_baseline`, `test_SN05_repeated_unsupported_capture_reuses_preserved_bytes`; paginated failure test_app |
| SN-06 | Accepted unnecessary full corpus/cache issue. Bounded durable chunks; reuse only unchanged accepted visual closure hashes. Affected explicit Source-summary links, mapped YAML content hashes and ignored local source rehydration; PDF evidence covers all pages. | `test_SN06_chunk_union_resumes_reuses_only_accepted_visual_hashes`, `test_SN06_external_follows_affected_summary_and_rehydrates_ignored_sources`; full source PDF page test_app |
| SN-07 | Accepted. Concrete public build/privacy/review/bundle verification precedes admin approval. Approval binds HEAD, full manifest, artifact inventory, bundle/extraction and reviewer hashes; all frozen bytes rechecked. | `test_SN07_21_25_public_preview_bound_before_approval_and_full_recovery`, `test_SN07_bundle_mutation_invalidates_approval_before_writes` |
| SN-08 | Accepted. New external range is ack..HEAD; finalize requires exact current ack base. | `test_SN08_ranges_always_begin_at_ack_and_old_finalize_blocks` |
| SN-09 | Accepted. Classification has empty isolated cwd; immutable archive originals and staged read bytes bound before all copy/upload effects. | `test_SN09_mutated_prepared_bytes_block_all_archive_writes`; source staging test_app |
| SN-10 | Accepted. Raw classify envelope lives outside candidate readable scope; no broad job_dir permission. Reader uses empty cwd plus explicit input/own-attempt dirs. | `test_SN10_19_32_permission_tables_zero_one_many_and_role_body`, builder regression, metadata-context test_app |
| SN-11 | Accepted. Per-learner status PDF/JSON filters observations, jobs, question job IDs and effects; aggregate stays local. | `test_SN11_12_semantic_report_filters_and_ignores_observation_noise` |
| SN-12 | Accepted. Semantic projection ignores survey UUID/time and job update time, excludes own report receipts. | `test_SN12_actual_repeat_run_zero_duplicate_status_upload`, semantic report test |
| SN-13 | Accepted. Separate stderr; stream all JSONL events with individual event bound, require final successful event and schema result. | `test_SN13_stream_large_stdout_separate_stderr_SN19_model_usage_required` (10MB stdout plus harmless stderr) |
| SN-14 | Accepted. Kill and verify child group after success/error/timeout, wait leader before accepting output. | `test_SN14_successful_child_cannot_leave_group_descendant`; timeout/group and inherited lock test_app |
| SN-15 | Accepted. Same terminal session, separate child group, foreground tty transfer/restore; kill/wait before receipt on every exit. | `test_SN15_interactive_tty_works_and_child_cleanup_before_receipt`, `test_SN15_real_terminal_ctrl_c_stops_child_before_receipt` (real pty), inherited-lock test_app |
| SN-16 | Accepted. Reconcile unknown own push before external observation; known push receipt can finish despite newer Drive revision. Clean unambiguous behind checkout can ff-only. | `test_SN16_unknown_push_with_newer_revision_reconciles_before_source_gate`; dirty/diverged/push crash test_app |
| SN-17 | Accepted. Explicit cumulative-base declaration and existing cumulative changes in writer envelope; full diff checked in every fix round. | `test_SN17_fix_round_cumulative_changes_and_SN24_source_paths` |
| SN-18 | Accepted. Quoted JSON secret fields, access/refresh/client/API tokens, ya29/1//github_pat/JWT, private-key patterns; authhome not granted reads. | `test_SN18_quoted_json_and_provider_secrets`, builder TOML test |
| SN-19 | Partially accepted. Claude safe-mode/restricted, Read only, explicit actual system-role body; missing/different modelUsage blocks. Codex explicit supported feature disables. No auth relocation. R1 hook claim was not verified: restricted already ignores user/project/local settings. New argv boundary behavior remains a VM probe gate. | `test_SN13_stream_large_stdout_separate_stderr_SN19_model_usage_required`, `test_SN10_19_32_permission_tables_zero_one_many_and_role_body` |
| SN-20 | Accepted. Preserve pages, options and collection members; only addition/order/membership changes automatic. License/base/branding/other config human-only. Review receives exact old/new manifest; branding path/hash checked. | `test_SN20_manifest_preserves_pages_and_blocks_configuration`; private pilot test_app |
| SN-21 | Accepted. Fresh independent public job from current clean acknowledged HEAD; historical ingest remains closed. | full public test includes later private HEAD and new public job |
| SN-22 | Accepted. Embedded Unicode TTF, hmtx-based 523pt wrapping including long words/URLs, no truncation. | `test_SN22_unicode_longword_width_and_full_text` uses real Poppler extraction and bbox (150 W characters, Hungarian accents) |
| SN-23 | Accepted resumable/memory issue. Stable preallocated ID, 8MiB chunks, persisted session/offset and frozen input checks, exact hash readback; expired session replace only after exact file absence plus readable parent. No midrun refresh capability invented. | `test_SN23_resumable_chunks_checkpoint_and_resume_exact_id`, `test_SN23_expired_session_retains_id_and_unknown_cannot_restart`; archive readback test_app |
| SN-24 | Accepted. Supervisor uses sources/YYYY-MM-DD-subject-package-ID/hash/relative-name; date is registration, not lesson date. Writer may not move originals. | `test_SN17_fix_round_cumulative_changes_and_SN24_source_paths` |
| SN-25 | Accepted. Separate public_review phase and independent job; concrete scoped attempt proposal and direct-admin exact-hash finite approval. No automatic counter reset. | full public test; `test_SN26_scoped_attempt_and_quota_recovery_rejection` |
| SN-26 | Accepted verified dead ends. Commands for quota reset evidence, bounded attempts, new-subject config, fresh partial render/photo, reject/close, unknown effects, stale-job reconciliation; old work/answers preserved as evidence. | scoped quota/attempt/rejection test, `test_SN26_stale_reconciliation_preserves_answers_without_authorization`, `test_SN26_unknown_local_commit_reconciles_readonly_when_source_is_stale`, `test_SN26_new_subject_exact_config_applied_supervisor_then_reviewed`, partial renderer test_app, partial-photo test |
| SN-27 | Accepted. Unique temporary photo output, completed hash plus atomic rename; existing unbound partial never adopted. | `test_SN27_partial_photo_not_adopted_and_retry_preserves_it` |
| SN-28 | Accepted. Family PDF names include their content hash; identical artifact reuses effect receipt. | `test_SN17_fix_round_cumulative_changes_and_SN24_source_paths`; unchanged private pilot test_app |
| SN-29 | Accepted. UV_PROJECT_ENVIRONMENT points to explicit preinstalled Python environment, UV_NO_SYNC=1, UV_OFFLINE=1 for every adapter child. | builder TOML/environment regression |
| SN-30 | Accepted. Worktree disk estimate uses actual ordinary checkout file sizes and configured minimum, not a 256MB assumption. | `test_SN30_worktree_estimate_includes_real_tree`; disk reserve test_app |
| SN-31 | Accepted. Before exclusive DB creation, actual clean HEAD/origin SHA must match configured initial observed SHA; existing DB fails before observation. | `test_SN31_wrong_initial_head_does_not_create_database`; exclusive init test_app |
| SN-32 | Accepted. Load and hash actual role body; Claude combines verbatim immutable canonical gl-reviewer with explicit narrower app role. Shared proof-free build_command bootstrap API uses identical production argv/envelope/isolation. Production still requires real measured capabilities. | `test_SN32_builder_no_bootstrap_false_proof_actual_role_and_isolation`, TOML/role regression; finite adapter wrapper test_app |

Evidence limits and justified corrections:

- [GitHub Releases API](https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28)
  documents the tag endpoint for published releases and authenticated lists
  including drafts. A tag 404 is not absence proof. No live release was created.
- [Drive upload modes](https://developers.google.com/workspace/drive/api/guides/manage-uploads)
  supports resumable large/interrupted transfer. The legacy helper refreshes
  during construction, not request(); a normal one-hour token exceeds the
  finite 50-minute run. Auth failure preserves effects; no login/scope fallback.
- The previous bwrap RTM_NEWADDR issue was resolved by root's earlier pilot,
  with ten boundary probes. That historical proof does not accept the new argv.
- Codex feature names were read from actual VM 0.159.2 help/list by root.
  Claude safe-mode/restricted are in actual VM help. Configuration and local
  wrapper fixtures do not prove actual provider vision/schema/boundaries.
- Canonical gl-reviewer provenance remains owner wiki commit
  d2c5b45c298af89147068c33746cb08f1192fda4; no claim that narrower reviewer.md is
  a verbatim canonical definition or that native --agent/safe-mode was tested.
- Public offline integration runs real local Git, Unicode PDF/Poppler,
  check-public.py and release-bundle.py with controlled rendered/browser
  receipts and fake provider/Drive/GitHub transports. Real Node/Chromium QA,
  provider model/vision, VM boundaries/resource peaks and GitHub capabilities
  are deployment gates, not inferred successes.
- Existing VM drive.file manual JPG and PDF metadata both returned 404. The
  actual reader gate and timer stay blocked; no ACL/scope changes are made.
- Nonblocking historical learning questions are not silently erased by an
  acknowledgement. Imported closure records must describe their disposition;
  the strict open blocking review/question arrays remain explicit.
- Subscription usage and remaining quota are unknown (`null`).
