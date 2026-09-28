# Install learning images from Git

Repository content is deployed **only through Git**, including code, rules, jobs, notes and accepted assets. Do not copy working-tree payloads through terminals, base64, temporary HTTP bridges or independent script copies. Prepare and commit a reviewable change, push the authorized branch, and fetch/check out that revision on the executor. Unfinished pilots may use an explicitly recorded work branch; do not present them as completed main-branch work.

The exception is **Hermes-local configuration outside our repositories**: credentials, machine paths, active-policy settings and the skill binding. Runtime output and spending ledgers are generated state, not substitute source code. Preserve them when updating. A repository artifact generated on the executor is committed and pushed there before another machine receives it through Git.

## 1. Restore the code

Prerequisites: Git, working authentication to the selected repository, Python 3.10+ and uv on Linux. Record their versions in the private deployment inventory. Hermes itself is installed separately; see [installation](install.md).

Set the following values to the operator-approved repository, directory and exact published commit. These are shell variables, not files to copy between machines:

```sh
school_repo_url='https://github.com/OWNER/REPOSITORY.git'
school_repo='/absolute/path/to/learner-repository'
school_revision='FULL_PUBLISHED_COMMIT_HASH'
school_hermes_home='/absolute/path/to/hermes-home'

git clone "$school_repo_url" "$school_repo"
cd "$school_repo"
git checkout --detach "$school_revision"
uv sync --locked
uv run python -m unittest discover -s tools -p 'test_*.py'
```

For an existing checkout, inspect `git status --short` first. Preserve unfinished work through an intentional commit/work branch or scoped stash; never silently discard it. Fetch the authorized branch and fast-forward it; verify `git rev-parse HEAD` against the recorded revision. The detached checkout above pins a read/test deployment; a bot that commits notes instead needs the authorized writable branch at the checked revision.

## 2. Bind the Hermes skill

Run the versioned installer from that checkout:

```sh
uv run python tools/install_hermes_images.py --hermes-home "$school_hermes_home"
uv run python tools/install_hermes_images.py --hermes-home "$school_hermes_home" --check
```

It creates exactly one binding: `<Hermes home>/skills/learning-images/SKILL.md` points to `<repo>/integrations/hermes/learning-images/SKILL.md`. It verifies the source matches the committed Git file, is idempotent for the same link, and refuses to overwrite a different file/link. It does not install a daemon, change bots, touch credentials, alter a budget or generate an image. The checkout must remain at its recorded absolute path. Shared files are identical across learners, so select one maintained checkout as the binding source and record it.

For an old copied skill, inspect/compare it with the committed source, move it to a private configuration backup outside the skill-discovery directory, then run the installer. Keep the backup until the new binding passes checks. Do not automate replacement of an unexplained differing skill.

## 3. Supply Hermes-local configuration

Follow the complete policy example in [learning-image execution](learning-image-execution.md). Outside Git, create an owner-only credential file containing only `OPENROUTER_API_KEY=...`, using a local editor or secret manager. Do not place the key in a command argument, terminal transcript, documentation or repository.

Create the private policy with actual absolute repo, credential and persistent-state paths. Its authorized page list, learner cap, request cap and attempt bound come from explicit authorization. No installed default grants spending. Create `~/.config/school-media/active.json`, for example:

```json
{
  "requests": [{
    "request_id": "AUTHORIZED_REQUEST_ID",
    "policy": "/absolute/private/path/policy.json",
    "learners": ["CONFIGURED_LEARNER"],
    "scope": "The exact authorized pages and operation"
  }]
}
```

The skill currently discovers this index under the service user's home. Selecting a different Hermes home does not relocate this index. Record both paths. A new machine needs a newly supplied secret or protected secret restore; Git cannot and must not reconstruct the secret itself.

For a resumed request restore the policy, ledger and attempt artifacts together, correcting machine-specific artifact paths with an explicit migration record. Never start an empty ledger for an already-spent request. Alternatively freeze the old executor and allocate only the verified unspent remainder, as described in the execution guide. A backup with an older cap is not an active policy. Preserve provider-side limits separately; the CLI's reservation is not a provider billing guarantee.

## 4. Check without spending, then test an authorized job

From the Git checkout run the skill check above, the unit tests, then `validate` and `prompt` with the documented CLI. The job and its source files must have arrived through Git and match the recorded hashes. Check skill discovery with the installed Hermes runtime; checking a symlink alone is not proof of runtime discovery.

Only then run one explicitly authorized `generate`, visually inspect its actual image and record the hash-bound review. Accepted image and evidence are repository changes: commit and push from the executor, then fetch on the editing machine. Do not copy generated assets through terminal encodings. A live CLI test and a Discord conversation test are separate results.

Record exact commits, installed link, config/secret locations (not values), ledger backup/restore location, validations, actual cost and remaining limitations. For rollback return the checkout to the previously approved revision and restore the former skill binding if necessary; preserve all spending state. No full-system rebuild is claimed until it has been tested from an empty machine.
