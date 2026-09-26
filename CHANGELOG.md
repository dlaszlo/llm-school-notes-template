# Template changelog

Newest first. Each entry says what changed in the shared files and what an existing wiki must do when it applies the update (see *Template updates* in [AGENTS.md](AGENTS.md)). A wiki records the version it is on in `PROFILE.md`.

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
