# Optional images: run everything from your repository

Ordinary wiki initialization, ingest and precise SVG diagrams require no image account or global agent skill. This optional feature runs on Linux with Python 3.10+ and uv. Any agent with file access and a terminal can use it by reading the repository's AGENTS.md, PROFILE.md and linked instructions. No agent installation is modified.

## Fresh checkout

Create your own private repository from the template, clone it and open a terminal in that checkout. Install uv separately if needed, then run:

```sh
uv sync --locked
uv run python -m unittest discover -s tools -p 'test_*.py'
uv run tools/learning_image.py check
```

The final command reports `not-configured`. This is normal: no key, spending permission, global HOME configuration or Hermes directory is assumed. Ask your agent to initialize the wiki and process a supplied note before enabling optional media.

## Enable one authorized image request

1. Copy `learning-images.example.json` to `learning-images.json` in your own repository. Keep the example unchanged. Choose a new request ID, use a local learner key that matches your jobs, list the exact authorized wiki pages under `targets`, and set both explicit USD limits. The example has no targets and zero limits. The current executor supports `openai/gpt-image-2.5-sunburst`; it does not silently substitute models. `reservation_usd` is a local estimate, not a provider billing guarantee; configure a separate provider key cap too.
2. Create `.env` locally from `.env.example` and fill in your own OpenRouter key with an editor or secret manager. Never put the key in Git, messages or echoed commands. Before an agent transfers any existing `.env`, token or key, it must disclose the exact source, destination and purpose and obtain explicit approval; general task authorization does not cover secret transfer.
3. `learning-images.json` is nonsecret, repository-specific configuration: review and commit it in your private wiki. The default paths are relative to that configuration file. `.env` and `.learning-images-state/` are ignored. Never copy a different learner's sources or configuration to bootstrap yours.
4. For a genuinely **new** authorized request, initialize its persistent state explicitly:

```sh
uv run tools/learning_image.py init-state
uv run tools/learning_image.py check
```

For a resumed request, restore the complete existing state instead; a clone does not restore spending history. Never initialize a fresh balance for an already-spent request.

After installing the approved credential, verify authentication without generating an image:

```sh
uv run tools/learning_image.py check --provider
```

This explicitly calls OpenRouter's [current-key endpoint](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key). It reports authentication and numeric key limits/usage only; no key, label, provider error body, learning content or image is sent to output. Ordinary `check` remains offline. A successful provider check does not test image generation, model availability, an agent's visual inspection or Discord delivery. A null provider limit means no key-specific cap was returned; keep the authorized local cap and configure the provider ceiling separately. No limit is raised by this check.

An already configured key may live in a protected per-user file outside every checkout, such as `~/.config/school-notes/openrouter.env`, containing only `OPENROUTER_API_KEY=...`. Set `env_file` to that exact path. Directory permissions should be 700 and the file 600. The existing explicit transfer-approval rule still applies; this is an example path, not automatic secret discovery.

For a newly authorized batch of incoming lessons, record its combined budget, separate learner allocations if applicable, the active executor machine and initially empty exact-page allowlists in the private profiles/configuration. Add the actual page path only when that lesson is requested and exists; keep the same request ID, state directory, cumulative budget and repair counts across lessons. Do not refresh the balance for each upload. Archive the superseded nonsecret request configuration as historical evidence and retain its original state. A Git clone does not migrate earlier spending history. Empty target lists allow setup checks, not generation.

5. Have the agent prepare the source-checked job described in [execution](learning-image-execution.md), including output language and exact visible text. Then run:

```sh
uv run tools/learning_image.py validate --job docs/evidence/media/YOUR-JOB/job.json
uv run tools/learning_image.py prompt --job docs/evidence/media/YOUR-JOB/job.json
```

Review the prompt before the authorized paid `generate` call. Open the actual result, complete the documented hash-bound `review`, then embed the accepted image and update evidence. The CLI does not replace human/agent visual inspection. Technical SVG diagrams remain precise SVGs.

## Other machines and agents

Programs, instructions, jobs and repository configuration arrive through Git checkout/update only. Record the source revision; do not transfer executable payloads, base64 scripts, temporary HTTP bundles or uncommitted source copies. Run the checked-in commands directly. Account identifiers, model defaults and routing are host configuration; program and skill contents are not configuration exceptions.

For Hermes or another agent, point it at the checkout and ask it to read AGENTS.md and PROFILE.md. Its existing file and terminal tools are sufficient for executing these programs; image QA additionally requires direct image viewing. No global skill installation, agent-code patch or daemon restart is part of this setup. Never claim a bot's actual tools/access are enabled until checked in that deployment.

Keep one active executor per request. On relocation, restore state before generation and stop the previous executor. Use `--config /explicit/policy.json` for a reviewed existing deployment; no home-directory active index is read implicitly. This compatibility path lets existing credentials remain where they already are, without moving them.

## Removal, rollback and recovery

Stopping use requires no agent uninstallation: stop issuing these commands. Preserve pending jobs, cost/upload state and accepted artifacts. Do not delete or move credentials as part of code cleanup.

Update or revert code through Git and retain the exact revision in deployment records. Back up state separately from code. See the execution guide's state-format compatibility note before rolling back across 1.13. A clean checkout plus configuration/secret/state restoration is the rebuild procedure; a successful mock test is not a successful provider or Discord test.

Legacy global image skills from earlier releases are unnecessary. Only after checking the exact existing binding, remove our obsolete binding using explicit, readable host commands. Preserve unrelated skills, accounts and settings. Do not restore a previously copied skill just because a backup exists: it may itself be the unwanted integration.
