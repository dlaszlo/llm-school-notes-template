# Curriculum references

This directory can hold a private, locally installed collection of curriculum and examination requirements. The uninitialized public template ships the navigation tool and these instructions, not a student's references, family settings or converted source documents. An initialized private wiki may hold its own authorized collection; its `index.md`, `catalog.json` and optional `collection.md` describe that local installation. Requirements guide relevant depth and prerequisites; they are not lessons to ingest or a checklist to impose on every topic. See *Curriculum-aware learning* in [AGENTS.md](../../AGENTS.md).

## Installing a collection

Install only an explicitly supplied and authorized collection into a private learner repository. Keep exact source bytes and SHA-256 hashes; never modify external supplied directories or symlink targets. Each document directory contains `document.md`, `manifest.json`, `provenance.json` and a derived `index.md`. The local `catalog.json` records document IDs, titles, the three file hashes, source PDF hash and document categories; its `index.md` is a compact navigation aid. The source PDF hash is conversion metadata unless the PDF itself was checked. This tool currently requires both metadata files for an installed curriculum snapshot; the general image-review rules still accept other source conversions without a manifest.

Use common examination references where relevant, and only the professional package for the learner's declared training. Do not copy another learner's professional requirements. PTT syllabi and KKK qualification outcomes are different document kinds, not automatically successive versions. Record the declared training and uncertain cohort applicability in the learner's `PROFILE.md`; a source filename or date alone does not establish compulsory hours or examination obligations.

If no collection is installed, do not invent one or block supported lesson work. The `check`, `search`, `read` and `build` commands require an installed catalog. A public template must not acquire private reference contents merely to make those commands run.

## Bounded reading

1. Read the learner's settings and the local collection's compact index. Start with at most two relevant documents and four passages, totaling about 12000 characters of requirement text. One reasoned expansion may reach four documents and 24000 characters; these are working bounds, not measured tokens.
2. Search one selected document with at most eight initial matches. Follow its element IDs and derived index; previews locate evidence but do not establish an expectation.
3. Read complete relevant elements with their level headers, table rows, inherited cells and continuations. Distinguish examination levels explicitly. Try a synonym or connected subject before reporting an unsuccessful search; no match does not establish absence.
4. Keep the taught core, prerequisite bridge and optional enrichment distinct. At the bound, record unresolved alignment and continue the supported lesson. Never load the whole collection into the model's context.

Run from the repository root:

```sh
uv run tools/curriculum.py check
uv run tools/curriculum.py search --document <document-id> --query '<topic>' --limit 8
uv run tools/curriculum.py read --document <document-id> --element <element-id>
uv run tools/curriculum.py build
```

`read` defaults to a 12000-character limit and refuses oversized output rather than silently truncating. Use `--lines START:END` for an explicitly labeled partial read while separately inspecting the necessary headers and continuations. `search` and `read` verify source hashes and index freshness. `build` writes derived indexes only. A changed source requires a new version and targeted review, not overwriting the evidence. Do not claim official curriculum compliance without verifying applicability.

Private learner repositories must make the references used by a cloud reviewer available through their authorized checkout or equivalent protected access. Public exports omit private references. Exclude local collections and family planning from commits to this public template; check actual Git visibility rather than assuming a directory named `docs` or `references` is private.
