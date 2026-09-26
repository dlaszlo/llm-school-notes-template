# Sources

(This file is directory documentation, not a source - it is never ingested.)

Drop source documents here under any name - this directory is the wiki's inbox and archive. Full rules live in [AGENTS.md](../AGENTS.md).

* At ingest the agent renames each file to `YYYY-MM-DD-short-title.<ext>` (acquisition date). A date-prefixed name therefore means the file has been ingested; any other name means it is still pending.
* URL-only sources are materialized: the agent fetches the content and saves it here before ingesting, so this directory stays complete.
* Only drop material meant to be ingested - a file shared just as context for a discussion does not belong here.
* Never drop a file containing live secrets (passwords, keys, tokens): provide a redacted copy instead - secrets never get committed, and a flagged file blocks all commits until resolved.
* Recordings (audio/video): if the platform produced a transcript (e.g. a Teams/Zoom export), drop it alongside the recording - it is part of the source.
* Images (screenshots, figures) live in `assets/`, named after the source they belong to.
* The authoritative record of what has been processed is the wiki itself: every ingested source has a Source summary page in `wiki/` and an entry in `wiki/log.md`.
* Files here are content-immutable: never edited, never deleted, never overwritten. A newer version of a document is a new dated file.
* Obsidian-managed attachments live in `assets/`.
* Everything here is a private working copy - do not republish it; check licenses before making this directory public.
