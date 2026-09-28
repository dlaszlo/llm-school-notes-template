---
name: learning-images
description: Plan, generate and visually verify authorized school-note banners and teaching infographics with the repository's bounded OpenRouter executor. Preserve precise SVG/code diagrams when exact geometry or quantitative meaning is required.
---

# Learning images

Resolve the learner and repository from trusted conversation/profile context. Read that repository's `AGENTS.md`, `PROFILE.md`, relevant evidence index, `instructions/media-workflows.md`, the needed stage in `instructions/media-prompts.md`, and `instructions/learning-image-execution.md`. These versioned repository instructions are authoritative; this entrypoint intentionally does not duplicate prompts or policy.

Read the operator-maintained `~/.config/school-media/active.json` when present to locate the current learner/request policy. Its presence does not authorize additional pages or a new budget. Never fabricate a missing entry or start a new request to bypass a completed/exhausted one.

Use the configured private policy and run `uv run tools/learning_image.py` from that repository. First plan from the supported lesson and current curriculum-aware scope; validate the JSON job and read its compiled prompt. Generate once, open the actual returned image with your image-viewing capability, record a hash-bound review, and accept only a usable candidate. If direct visual inspection is unavailable, leave it awaiting review; do not claim success from a prompt or OCR description.

Use the same stable request/job IDs, source hashes and persistent ledger across Drax, Mantis, Codex and resumed sessions. The same CLI handles banners and infographics. Never copy secrets into a job, prompt, message or repository. Do not change the model or reset counters on failure. Keep technical details in the evidence record and readable meaning in prose/alt text.

After acceptance, insert the asset with its observed description and scoped provenance, update the evidence index and follow existing commit/push authorization. For longer role handoffs use the deployment's existing durable task mechanism and `instructions/media-handoff.md`; this skill is not itself a scheduler. Configuring this entrypoint does not prove bot routing, credentials or role isolation are installed.
