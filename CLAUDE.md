# Claude Code entry point

@AGENTS.md

@PROFILE.md

AGENTS.md routes to the shared policy modules (from the template); this wiki's own settings live in PROFILE.md. Codex and other agents read AGENTS.md, which tells them to read PROFILE.md.

If `.school-notes/fetch.json` exists, you are in a school-notes run: work by the fixed prompt in [the run module](instructions/school-notes-run.md). The mechanical steps (check, images, fetch, finish) are MCP tools. If `fetch.json` has `"mode": "interactive"`, call `finish` at the end of the work and report its outcome.
