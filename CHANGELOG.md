# Template changelog

Newest first. Each entry says what changed in the shared files and what an existing wiki must do when it applies the update (see *Template updates* in [AGENTS.md](AGENTS.md)). A wiki records the version it is on in `PROFILE.md`.

## 1.11.9 - 2026-09-28

* Open questions are always sequential numbered Markdown items, each grouping its own context, concrete uncertainty, relevant alternatives/explanation and recommendation or next step. Depth is proportional; no artificial alternatives or empty sections.
* Added a reusable open-question example. Continue the two-page preview; no bulk rewrite or changes to learning facts.

## 1.11.8 - 2026-09-28

* Added one opening break and two closing breaks inside expandable answers, following the user's GitHub preview feedback. Closed questions remain compact; spacing within multi-part answers stays unchanged.
* **Migration**: synchronize the shared rule and examples, then update only the two authorized preview pages. No teaching content or image changes.

## 1.11.7 - 2026-09-28

* Clarified that image generation is not itself an agent-added explanation. Replaced the blanket image author footer from 1.11.6 with scoped content provenance; technical maker credits stay in evidence/comments.
* Source labels now explicitly attach to the affected passage or named image content. Mixed-source images identify the reference-only contribution rather than labeling the entire image indiscriminately.
* Indented expandable answers with the shared HTML wrapper and reduced spacing inside mixed answers to ordinary paragraph gaps. Only the end of an answer gets the optional extra break.
* **Migration**: synchronize shared rules/examples and apply to the same two-page preview only. Keep existing sources, assets and teaching facts unchanged; no new paid generation or bulk migration.

## 1.11.6 - 2026-09-28

* Restored explicit semantic icons beside machine-authorship labels: `💡 Drax🤖 magyarázata`, `➕ Drax🤖 kiegészítése`, `⚠️ Drax🤖 javítása`, using the actual author and localized role. Textbook/background labels keep 📗 and their sources; lesson content remains the unlabeled default.
* Replaced the mandatory bold label at the start of a callout with a small trailing label. This intentional layout change preserves the distinction between explanation, addition, correction and reference content; it does not erase provenance or rename earlier authors.
* Added shared note-formatting examples for small metadata, spacious sections, image captions and mixed expandable answers. Self-tests keep their spacing inside the disclosure and do not acquire an author label for ordinary answers.
* **Migration**: synchronize shared files, localized Wording and the root legend. Apply the page layout only to requested pages; the first preview covers Mezopotamia and Hammurapi. Existing other pages remain valid during staged migration. No new ingest, image generation, bulk rewrite or PDF build is triggered. Keep the template uninitialized.

## 1.11.5 - 2026-09-28

* Added an open, learning-task-led visual repertoire and explicit OTHER/ELSE path, including custom/mixed forms, reuse and no new image. Topology applies only when relationships matter; reciprocal flows are not automatically a cycle.
* Added the requested Astra xhigh research rationale and revised planning, generation, review and role-handoff prompts. Rich meaningful illustrations remain supported.
* Made the existing arrow review explicit per edge: source, arrowhead/direction, target, label and condition, compared with evidence rather than only the prompt.
* **Migration**: synchronize shared files and local template references. Apply to authorized generation/review; no new generation is triggered by this update.

## 1.11.4 - 2026-09-28

* Historical notes and standalone media establish verified time and geographical context at the beginning. A readable banner may repeat it; the body must retain it.
* Infographic planning now chooses composition by semantic structure, compares accepted relevant examples, and checks whole-system understanding separately from individual arrows. Record prompt-design failures and learner feedback before retrying; preserve budget and orientation rules.
* **Migration**: synchronize the shared set and record the template commit in local profiles. Apply on new or revisited content; no bulk rewrite, banner regeneration or additional paid run is authorized by this release. Keep the template uninitialized.

## 1.11.3 - 2026-09-28

* Added *Ask self-contained, useful questions*: context, concrete uncertainty/problem, genuine alternatives where helpful, and an evidence-based recommendation or next step. Applies to conversation, note questions, review and handoff; self-tests keep their solutions hidden.
* Reconciled the previously authorized 1.11.2 handwriting rule into the template without removing the index-only or evidence safeguards.
* **Migration**: synchronize the full shared set and record this release and exact template commit in local profiles. Apply the question rule when creating or revisiting relevant questions; this does not authorize a bulk content rewrite or change every page's label layout. Keep the template uninitialized.

## 1.11.2 - 2026-09-27

* *Reading handwritten sources*: readings are resolved from context and subject knowledge before they become open questions, in every subject (recalculation, unit conversion, arrows and later steps, table and sign patterns, sentence meaning, textbook and standard facts). Visible slips stay visible on the Source summary and get a *correction* or *addition* label on the topic page; open questions remain only for doubts that change what is learned. Reviewers apply the same test.
* **Migration**: copy the shared set. Existing open questions may be re-examined under the new rule during the next review; resolved ones move to labeled content, never silently.

## 1.11.1 - 2026-09-27

* Restored the accidentally removed *Index-only books* rule verbatim. Existing index-only restrictions and profile decisions remain in force.
* Clarified that textbook-only labels exclude content also present in teacher material to learn, and that apparent source contradictions require reopening the original notebook photo before treating its earlier transcription as evidence.
* Added a shared review-closure workflow for correcting agents and reviewers, with archived reports, correction commits, evidence and separately recorded unresolved questions. Added explicit semantic-removal and profile-reference checks to template migration.
* **Migration**: copy the full shared set, update the applied release and exact template commit in local profiles, and preserve each learner's settings. Do not mark an old report resolved without performing its relevant checks. The template remains uninitialized; it receives no learner evidence or review index.

## 1.11.0 - 2026-09-27

* Added the system handbook for learning, blog preparation, operating lookup and full-system reconstruction, including Hermes roles/routing, repositories, media, Drive and scheduled review. Distinguish live components from plans and retain private deployment facts separately.
* Added the reproducible Drive OAuth helper, bounded media uploader and Hermes skill. Uploads use configured learner destinations/outboxes, private durable request records, preallocated Drive IDs, resumable transfers and complete SHA-256 readback. Sharing and deletion are not implemented; shared-user shell access is not OS isolation.
* **Migration**: synchronize the complete shared set; configure credentials, actual folder IDs and outboxes outside Git; install both skill and script following `instructions/install-drive.md`. Never overwrite an existing token/config/ledger during an update. Preserve the template's uninitialized profile. Run unit tests and destination checks before enabling the skill; intended-reader access and separate bot executors remain independent checks.

## 1.10.0 - 2026-09-27

* Shared files are strictly identical and listed once in `shared-files.json`; `tools/check_shared.py` reports missing or divergent files against a local template checkout. Local configuration never belongs in shared policy or code.
* Reusable media planning, prompt and handoff instructions now live in `instructions/` and ship to every linked wiki. Family deployment records remain private and do not imply installed tools or spending authority.
* Banner wording, colors, currency mark and optional decorative symbols live in `tools/subjects.json`. Reference-index wording lives in `tools/book-index.json`. The common indexer preserves checked README overrides (`--readme` or the existing marker) and both English/Hungarian offset recognition.
* **Migration**: preserve existing configuration, source data, evidence and generated assets. Extract local hard-coded banner settings before replacing the tool; move local reference listings out of shared README files into local indexes. Copy every file listed by the manifest, record the same canonical template URL/version/commit structure in each profile and template link in each README, then run the shared-file checker and relevant tool regression tests. Do not regenerate teaching pages or assets merely to synchronize tools. The template remains uninitialized with empty subjects and no tracked learner references.

## 1.9.0 - 2026-09-27

* Added direct visual-evidence checks, optional conversion diagnostics, notebook-first image ordering, shared reviewer evidence and learning-value selection of teacher images. Original teaching files receive visible links; dated source filenames no longer imply completed ingest.
* Added curriculum-aware scope and bounded reference navigation, selective SVG/raster visuals with actual-image descriptions, bounded ingest-time infographic generation and printable A4 study notes. Existing precise diagrams remain valid; no blanket replacement or automatic paid batch is implied.
* Added optional media environment placeholders and standard-library curriculum tools with synthetic regression tests. The public template includes no private source collections, family plans or media-trial evidence.
* **Migration**: merge these shared rule changes with local school rules rather than replacing local profiles or teaching pages. Copy `tools/curriculum.py`, `tools/test_curriculum.py`, `references/curriculum/README.md` and the updated source-status guidance. Configure learner-specific requirements and any media access explicitly in `PROFILE.md`; retain existing subject/banner settings. Do not copy another learner's professional package or create empty evidence indexes. No existing notes or assets need rewriting solely to adopt this version.

## 1.8.0 - 2026-09-27

* The tools became a uv project: `pyproject.toml` and `uv.lock` (shared files) list their Python dependencies (Pillow, python-pptx, python-docx), and every tool runs with `uv run tools/<name>.py` - no `pip install` or system packages. New *Tools* rule under *Sources*; all tool commands in `AGENTS.md` now use `uv run`. `.venv/` is gitignored.
* *Teacher materials*: a teacher's material may be uploaded pre-converted - a dated `sources/` directory with the original file, `document.md`, and `figures/`; the conversion stays next to the original (the original is authoritative and hashed). When a book's `figures/` are missing, the description is only a guide and a doubtful reading needs *Requesting a page*.
* **Migration**: copy `AGENTS.md`, `pyproject.toml`, and `uv.lock`; add `.venv/` to `.gitignore`; make sure `uv` is installed where the agent runs. In agent prompts and scheduled jobs, replace `python3 tools/...` with `uv run tools/...`.

## 1.7.1 - 2026-09-27

* *Reading a book*: book figures are opened only for a specific check and only when `document.md` describes them; figures without any description or printed text, and image files `document.md` does not reference (barcodes, logos, QR codes, decoration), are never opened.
* **Migration**: copy `AGENTS.md`.

## 1.7.0 - 2026-09-27

* New *Sources* rule: photos are filed with the new shared tool `tools/prepare_photo.py` - same resolution, upright, JPEG quality 90, all metadata (GPS, device, date) removed; the stored copy is the source (read at ingest, checked by the review, hashed). Keeps the repository growing several times slower and strips location data.
* **Migration**: copy `AGENTS.md` and `tools/prepare_photo.py` (needs Pillow; `pillow-heif` optional for iPhone HEIC). Existing photos stay as they are - their hashes are recorded. If an agent's channel prompt says to copy incoming files into `sources/`, change it to file photos with the script.

## 1.6.1 - 2026-09-27

* *Teacher materials*: images from material to learn may be used where they teach and our own drawing could not replace them (maps, complex diagrams, historical objects and artworks, buildings, sites and rooms, experiment photos, cross-sections); never decorative, never from the textbook or background material. They go to `wiki/assets/orai/` with the *class-image caption*; for maps, objects, artworks and places a freely licensed image (Wikimedia Commons) is preferred.
* **Migration**: copy `AGENTS.md`; add the *class-image caption* key to the *Wording* table in `PROFILE.md` (translated).

## 1.6.0 - 2026-09-27

* New *Teacher materials* rule under *Sources*: material a teacher shares (pptx, pdf, docx, photo of a handout) is either *to learn* - a source like the notebook, its content on the topic pages with lesson lines and footnotes, no label - or *background* - a reference with its map, labeled with the new *background label*. The student names the kind with one word when sending; if it is missing, the LLM asks before ingesting, even under automatic ingest, and offers its own guess. The notebook itself is always material to learn.
* **Migration**: copy `AGENTS.md`; add the *background label* and *teacher-material words* keys to the *Wording* table in `PROFILE.md` (translated); add the background label to the *legend* section of the root index. If an agent's channel prompt says that every file sent is a source, add: "except teacher materials - follow the Teacher materials rule of AGENTS.md (ask before ingesting when the kind is not given)".

## 1.5.0 - 2026-09-26

* New *Reading a book* rule under *References*: a converted book is never loaded whole; its generated `index.md` maps every lesson and printed page to a line range of `document.md` and points to the book's own contents, indexes, and answer key, and only the needed lines are opened. New shared tool `tools/book_index.py` builds the map from the page anchors and the book's own table of contents (README lesson table as fallback).
* **Migration**: copy `AGENTS.md`, `references/README.md`, and `tools/book_index.py`; run `python3 tools/book_index.py references/<subject>/<book-id>` for every converted book (a README without an offset line needs `--offset N`, or add "printed-page offset: N" to it); check a few lesson ranges against the book; commit the `index.md` files. Index-only books need nothing.

## 1.4.0 - 2026-09-26

* *References*: new **index-only books** - a book that may not be converted (e.g. the publisher forbids processing it with AI) gets only a hand-made index in its `README.md` (table of contents and subject index: numbers and titles, no text); textbook lines come from it, with the new *index-based note* when the section is chosen by topic. New **Requesting a page** rule: when the notes cannot be understood or checked without a page of an unconverted book, the LLM names the exact page and asks for a photo; the photo is not a source - used only for the check, never stored in the repository, its chat message deleted afterwards; what comes over gets the *textbook label*.
* **Migration**: copy `AGENTS.md`; add the *index-based note* key to the *Wording* table in `PROFILE.md` (translated). If a book-specific local decision already covers this, keep only its book-specific facts in `PROFILE.md` or the book's reference `README.md`. If an agent's channel or system prompt says that every file sent is a source, add the exception for requested pages (point it at *Requesting a page* in `AGENTS.md`).

## 1.3.0 - 2026-09-26

* Topic pages now show what was taught in class and what only the textbook adds: textbook-only content gets the new *textbook label* (`📗`, a `> [!NOTE]` callout or inline, also in the *in short* box and chapter summaries); a mere confirmation or page reference stays a footnote. New *When was it taught* rule: every topic-page section built from notebook content opens with the *lesson line* (`🗓️` + the lesson date), and the page follows the order of the lessons.
* **Migration**: copy `AGENTS.md`; add the *textbook label* and *lesson line* keys to the *Wording* table in `PROFILE.md` (translated into the wiki language); add 📗 and 🗓️ to the *legend* section of the root index; then go through every topic page and chapter summary: label every textbook-only statement (sections, tables, *in short* bullets, quiz answers), and add lesson lines to the notebook-based sections (dates from the lesson-notes pages and the *lessons* tables).

## 1.2.0 - 2026-09-26

* *Source summary* update semantics clarified: write-once applies to the source's content; a wrong or incomplete *reading* (misread number, skipped line, inferred unit) is fixed in place, and the fix is recorded only in `log.md` and git.
* New content rule *Pages show the current state, not their history*: no remarks about earlier versions, correction appendices, or review rounds on wiki pages.
* New *Reading handwritten sources* rule (transcribe first, zoom, keep the notebook's exact form, uncertain readings to open questions) and a mandatory *Self-check* at the end of every ingest or correction (two-way coverage ledger, provenance on every surface, formulas, drawings, links). The Ingest workflow gained the self-check as a step.
* **Migration**: copy `AGENTS.md`; then search the wiki for correction appendices and history remarks (e.g. "korábban", "korábbi", "helyesbít", "previously", "corrected") and fold their content into the main text of the page, removing the remarks; the history stays in `log.md`. Record the version in `PROFILE.md`.

## 1.1.0 - 2026-09-26

* The wiki-specific sections moved out of `AGENTS.md` into a new `PROFILE.md`: *Setup*, *Standing authorizations*, *Wording*, plus new *Template* and *Local decisions* sections. `AGENTS.md` is now the same in every wiki; bootstrap fills `PROFILE.md` instead of editing `AGENTS.md`. `CLAUDE.md` imports both files.
* New rule *Template updates*: updating is opt-in, only on the user's instruction; local changes to shared files are shown and never overwritten silently.
* **Migration** (for a wiki bootstrapped from 1.0.0): create `PROFILE.md` from the template's, move the filled-in *Setup*, *Standing authorizations*, and *Wording* sections from the wiki's `AGENTS.md` into it (keeping their content), record the version; then replace `AGENTS.md` and `CLAUDE.md` with the template's.

## 1.0.0 - 2026-09-26

* First version of the template.
