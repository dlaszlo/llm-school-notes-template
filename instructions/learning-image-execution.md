# Learning-image execution: one path for Codex, Hermes and other agents

This is the runnable banner/infographic path. The author reads the relevant [workflow](media-workflows.md), [prompt stage](media-prompts.md), profile and evidence, writes a compact checked plan, then calls `tools/learning_image.py`. The CLI does not decide facts or visually review an image. Its inputs and receipts are portable across roles; no full curriculum corpus or private learner profile goes to the image provider.

## Install and configure

From the configured repository, run `uv sync --locked`. Python 3.10+, Pillow and Linux `flock` are sufficient. Keep the OpenRouter key in a protected file outside Git or the environment. The selected provider/model is `openai/gpt-image-2.5-sunburst`, fixed in the executor; no silent provider fallback. The [OpenRouter image API](https://openrouter.ai/docs/guides/overview/multimodal/image-generation) returns an inline raster and usage metadata. A missing cost or interrupted response is unresolved, not free.

Create a trusted private policy, for example `~/.config/school-media/history.json`, with owner-only permissions. Configure actual absolute paths and an explicitly authorized request scope; these placeholders are not an initialized template:

```json
{
  "request_id": "authorized-request-id",
  "env_file": "/private/path/openrouter.env",
  "state_dir": "/private/persistent/state/authorized-request-id",
  "max_total_usd": "3.00",
  "reservation_usd": "0.25",
  "max_attempts": 3,
  "learners": {
    "configured-learner": {
      "repo": "/private/path/learner-repository",
      "targets": ["wiki/subject/topic.md"],
      "max_usd": "3.00"
    }
  }
}
```

The whole-request cap includes every image and repair executed with that state, across roles and sessions. The learner cap is an additional bound within the request. Keep an externally configured provider-key ceiling too: a reservation is a conservative local allowance, not a provider guarantee of maximum billing. Do not reset state or choose a new request ID to evade limits. If separate requests run concurrently, deployment-level period/key limits must also constrain their combined spending; this CLI does not claim a cross-account budget service.

## The job file

Store a reviewed job in the learner repository's private `docs/evidence/media/<id>/job.json`. Use a stable ID and one logical page/role; distinct second infographics use `infographic-2`. `sources` includes the target page and the exact supporting files actually relied on, hashed after content editing and before generation. References remain read-only.

```json
{
  "id": "topic-banner-v1",
  "request_id": "authorized-request-id",
  "learner": "configured-learner",
  "target": "wiki/subject/topic.md",
  "role": "banner",
  "sources": [{"path": "wiki/subject/topic.md", "sha256": "actual-sha256"}],
  "plan": {
    "goal": "The concrete learner task",
    "scope": "Relative scope-record reference and selected depth",
    "decision_reason": "Why this image helps",
    "context": "The necessary visible introduction",
    "visible_text": ["Exact title", "Exact contextual subtitle"],
    "claims": [{"text": "A checked visual assertion", "source": "Exact evidence location"}],
    "composition": "Reading order and meaningful arrangement",
    "style": "Visual style appropriate to the task",
    "aspect_ratio": "21:9",
    "constraints": "Only the accuracy constraints relevant to this image"
  }
}
```

Conditional plan fields are `relationships`, `sequence`, `comparison`, `metaphor`, `example` and `optional`. Do not fill them merely to satisfy a checklist. The compiler omits source paths, hashes and private scope metadata from the provider prompt. Only `visible_text` is eligible for printed labels: composition, constraints and review instructions must not become image captions. Put every learner-facing contextual sentence into that list explicitly. Banners use 21:9; infographics normally use landscape 3:2 or 4:3, with portrait only when requested. A4 fit preserves aspect ratio and safe margins, without pretending the generated pixel count is 300 dpi.

## Execute, inspect, accept

Commands are identical for an interactive author and a Hermes shell tool. Substitute the trusted policy path and job path:

```sh
uv run tools/learning_image.py --config /private/policy.json validate --job docs/evidence/media/topic-banner-v1/job.json
uv run tools/learning_image.py --config /private/policy.json prompt --job docs/evidence/media/topic-banner-v1/job.json
uv run tools/learning_image.py --config /private/policy.json generate --job docs/evidence/media/topic-banner-v1/job.json
uv run tools/learning_image.py --config /private/policy.json status
```

Read the compiled prompt before paying. `generate` makes ONE request, never automatic retries. A persistent reservation precedes network activity. The JSON result identifies the candidate folder, size, hash, cost and request total. Directly open `image.png` with the agent's image-reading tool, inspect the whole image and relevant details, compare the checked sources and apply the form-specific QA. Use phone and print placement checks, not OCR alone.

Write a review JSON with `verifier`, actual `checked_at`, exact `sha256`, `observed` semantic description, `decision` (`accepted`/`rejected`), `material_defects` (list), and `checks` for `sources`, `context`, `text`, `visual_claims`, `arrows`, `learning_goal`, `phone`, `a4`. Each is `pass` when inspected; only `arrows` may be `not-applicable`. Record actual arrows, limitations, phone zoom needs and A4 placement in additional fields; a checkbox is not evidence by itself.

```sh
uv run tools/learning_image.py --config /private/policy.json review --job docs/evidence/media/topic-banner-v1/job.json --report /private/review.json
```

Acceptance rechecks sources and output hash, copies a versioned final PNG to `wiki/assets/` (banners to `wiki/assets/banner/`), and retains the plan, exact prompt, review and cost receipt in `docs/evidence/media/<id>/`. It never overwrites differing bytes. The author then inserts the accepted image with accurate alt text, scoped source caption and an observed hash-bound `image-description` comment, updates evidence/index and commits. Do all images for a page before editing its embeds; otherwise its source hash changes and the second job correctly stops as stale. The same applies to source-summary pages used by several jobs.

Review rejection permits one targeted repair with `generate --repair /private/repair.txt` on the SAME job. It regenerates from the checked plan plus the concrete correction; it is not an edit API or a promise to preserve pixels. Each repair needs full-image review. At three attempts use the best acceptable candidate by its hash, or keep a suitable old image/text and record the precise unresolved question. A new filename never resets attempts.

## Recovery, checks and limitations

* Repeating a generated job returns its pending review; repeating an accepted job with still-current sources returns the accepted receipt, without spending. Renaming the job for the same page/role is rejected.
* A provider interruption, malformed result or unknown cost blocks further request spending. `reconcile --job ...` can recover from the exact saved provider response after an interrupted local save, without any network call. If no complete response exists, obtain provider billing/output evidence and resolve the recorded attempt; do not invent a zero cost or retry blindly.
* One lock serializes the ledger and spending; a concurrent process fails clearly. Source versions are checked before generation and acceptance. An out-of-band repository writer must still be coordinated by the caller; the CLI does not lock other agents' git processes.
* No automatic publication, sharing changes, raw-source upload or paid QA call occurs. Small inline wiki images remain in Git; larger standalone media uses the separately configured Drive delivery path.
* The path/target and spending checks are cooperative guardrails. An unrestricted shell user with the key can bypass them. This is not OS isolation or proof that separate Hermes role profiles are deployed.
* Run `uv run python -m unittest discover -s tools -p test_learning_image.py` after executor changes. The synthetic suite exercises retries, unknown charges, bounds, changed sources, path/learner rejection, concurrency and review-hash checks. A live job additionally proves the configured provider path; it does not prove future error-free outputs or Discord routing.

For Hermes, install the [thin skill entrypoint](../integrations/hermes/learning-images/SKILL.md) into the selected profile's skills directory (copy the file into a `learning-images` directory). Configure the trusted policy location in private deployment settings. Keep the repository tools current; do not duplicate the CLI into another unversioned script. The generic template supplies no credentials, child IDs or private references.
