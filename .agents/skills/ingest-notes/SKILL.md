---
name: ingest-notes
description: Incorporate notebook pages or teaching materials of a school-notes run into the wiki, with source and visual evidence checks.
---

# Ingest notes

If `.school-notes/fetch.json` exists, you are in a school-notes run: work by the fixed prompt in [the run module](../../../instructions/school-notes-run.md). The mechanical steps (check, images, fetch, finish) are MCP tools; the tool files the sources, writes the machine fields and indexes, commits and publishes. If `fetch.json` has `"mode": "interactive"`, call `finish` at the end and report its outcome. Without `fetch.json`, ingest is not possible here: learner work runs only through `school-notes chat`.

Read [AGENTS.md](../../../AGENTS.md) and [PROFILE.md](../../../PROFILE.md), then follow **Ingest**, **Reading handwritten sources** and the **Self-check**. Read the pages of `fetch.json` in their order, split them into lessons, and do not replace an uncertain reading with a plausible invention. Follow **Visual evidence checks** and describe each image-dependent check in `result.json` `checks`.

Use **Curriculum-aware learning** to select relevant depth. Write and propagate the source-supported lesson using [note formatting](../../../instructions/note-formatting.md); preserve classroom diagrams and their instructional meaning. When an authored visual helps, use the [learning-visuals entry](../learning-visuals/SKILL.md). Report unresolved readings as open questions; a blocking problem is a `question` in `result.json`.
