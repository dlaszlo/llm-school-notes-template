# Template changelog

Newest first. Each entry says what changed in the shared files and what an existing wiki must do when it applies the update (see *Template updates* in [AGENTS.md](AGENTS.md)). A wiki records the version it is on in `PROFILE.md`.

## 1.6.1 - 2026-09-27

* *Teacher materials*: images from material to learn may be used where they teach and our own drawing could not replace them (maps, experiment photos, artworks, cross-sections); never decorative, never from the textbook or background material. They go to `wiki/assets/orai/` with the *class-image caption*; for maps a freely licensed map (Wikimedia Commons) is preferred.
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
