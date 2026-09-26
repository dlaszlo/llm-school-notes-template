# Template changelog

Newest first. Each entry says what changed in the shared files and what an existing wiki must do when it applies the update (see *Template updates* in [AGENTS.md](AGENTS.md)). A wiki records the version it is on in `PROFILE.md`.

## 1.1.0 - 2026-09-26

* The wiki-specific sections moved out of `AGENTS.md` into a new `PROFILE.md`: *Setup*, *Standing authorizations*, *Wording*, plus new *Template* and *Local decisions* sections. `AGENTS.md` is now the same in every wiki; bootstrap fills `PROFILE.md` instead of editing `AGENTS.md`. `CLAUDE.md` imports both files.
* New rule *Template updates*: updating is opt-in, only on the user's instruction; local changes to shared files are shown and never overwritten silently.
* **Migration** (for a wiki bootstrapped from 1.0.0): create `PROFILE.md` from the template's, move the filled-in *Setup*, *Standing authorizations*, and *Wording* sections from the wiki's `AGENTS.md` into it (keeping their content), record the version; then replace `AGENTS.md` and `CLAUDE.md` with the template's.

## 1.0.0 - 2026-09-26

* First version of the template.
