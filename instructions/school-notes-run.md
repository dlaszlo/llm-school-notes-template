# Working in a school-notes run

Shared operating rules, loaded through [AGENTS.md](../AGENTS.md). Learner work happens only inside a run of the `school-notes` tool: hourly (cron) or in the owner's session (`school-notes chat`). A harness started directly on the host is never used for learner work.

## Who does what

The tool does everything that can be computed: Drive download and filing into `sources/`, hashes, duplicate detection, page order, machine frontmatter, index blocks, `publication/public.json`, review-file state, evidence records, image generation and insertion, `check`, commit, rebase, push and the public site. The writer (you) reads the sources and writes the wiki: transcription, interpretation, placement, prose, diagrams, the image plan and image judgement, the evidence description, the `wiki/log.md` entry, review fixes. Do not do the tool's bookkeeping by hand; it would be overwritten or refused.

## Run files (`.school-notes/`, never committed)

* `fetch.json`: the run: `packages` (Drive folder, subject, role `fuzet`/`tanari`, new subject), `pages` in their fixed order (`seq`, the stored `sources/...` path, `duplicate_of`), the `range` of pages this call covers, the `open_review_items` to fix, the `pending_images` to produce, and `conflict_files` while resolving a conflict.
* `changes.json`: files already changed in this run; continue from there, do not redo them.
* `check.json`: problems the tool found; fix them first.
* `result.json`: your output (schema below), written at the end of the work.

## Fixed prompt

Read `AGENTS.md`, `PROFILE.md` and the rules the rule map requires for ingest, in that order. Read `fetch.json`; if `changes.json` or `check.json` is not empty, continue from there. Do the work, write `result.json`, then call the MCP `check` and fix what it reports.

## result.json

```json
{"status": "done | question",
 "questions": [{"text": "..."}],
 "notes": [{"file": "wiki/<subject>/<date>-<topic>-jegyzet.md", "pages": [1, 2]}],
 "new_subjects": [{"subject": "<short-name>", "emoji": "...", "color": "#rrggbb"}],
 "review_closure": [{"file": "docs/review/...", "item_id": "R3", "status": "fixed | disagree | open", "note": "..."}],
 "checks": [{"page": "wiki/...", "image": 3, "locator": "page, figure, exercise", "observed": "...", "decision": "changed | confirmed | unresolved", "note": "..."}]}
```

* `notes`: every non-duplicate page of the range belongs to a lesson-notes page; you name the page `<date>-<topic>-jegyzet.md`. The tool writes its machine fields from this.
* `question`: only for a blocking problem (not a notebook, a textbook page, unreadable, a subject other than the Drive folder's). A non-blocking uncertainty goes under the page's open questions.
* `review_closure`: at most 20 closed items per run. Never edit a review file.
* `checks`: what you looked at, what you saw and what you decided for each image-dependent claim (see *Visual evidence checks*). `image` is a page `seq` or a repository path under `sources/` or `wiki/assets/`.

## Where you may write

`wiki/**` (except generated blocks and machine frontmatter keys) and `wiki/assets/**`; in the owner's session also `references/**`; while resolving a conflict also the conflicting files. A file that existed before the run is never renamed or deleted; a file created in this run may be deleted. No symlinks, no dotfiles under `wiki/`. The tool's path guard refuses everything else.

## MCP tools

`check` (call it at the end; it also reports files you may not touch), `image_generate(plan_id, repair_note?)`, `image_accept(plan_id, review)`, `wait(job_id)`, `status`; in the owner's session also `fetch` and `finish`. Long operations return a job id: call `wait` until the job is done. In a session started with `fetch.json` `mode: interactive`, call `finish` at the end and report its outcome. There is no Git in the container and no web access: a fact that needs an outside source becomes an open question.

## Visual engines

Every engine of `tools/visual_tools.py` works in the container: Python with matplotlib and numpy (plots, measured data, constructions), Graphviz (graphs, trees, flowcharts), PlantUML (process, state and sequence diagrams), POV-Ray (3D scenes, also animations rendered to MP4 with a static poster) and FreeCAD (exact technical drawings, parts, sections). Mermaid works directly in the Markdown; illustrations come from the image tools above. Choose the engine that best supports understanding of the figure, following [technical visuals](technical-visuals.md); render with `uv run tools/visual_tools.py render …` into `wiki/assets/`.

## Stable order

The order of existing lists, sections, links, chapters, lessons and topics never changes between runs. A new item goes to its fixed place: chapters in the syllabus/notebook order, lessons by date, topics in the order the lesson treats them, list items where the existing order puts them. Re-ordering is done only on the owner's request in a session. The tool's `check` refuses a cron run that re-orders existing `chapters`, `lessons`, `topics` or a page's `order`.
