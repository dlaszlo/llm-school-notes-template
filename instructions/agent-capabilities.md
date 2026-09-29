# Repository skills and optional bot capabilities

This guide connects the shared workflows to agents with different jobs. It is an optional deployment design, not a prerequisite for maintaining a wiki with one capable agent. The skills and programs travel with the complete Git checkout; no project code belongs in an agent's installed or bundled skill directories.

## Task entry points

| Task | Repository entry | Detailed policy owner |
|---|---|---|
| Understand or practise existing material | [study-notes](../.agents/skills/study-notes/SKILL.md) | [Query](wiki-workflows.md) and [Curriculum-aware learning](content-and-curriculum.md) |
| Incorporate supplied teaching material | [ingest-notes](../.agents/skills/ingest-notes/SKILL.md) | [Sources / Visual evidence checks](sources-and-evidence.md) and [Ingest](wiki-workflows.md) |
| Produce a requested learning medium | [learning-media](../.agents/skills/learning-media/SKILL.md) | Media workflows, prompt stages and handoff contract |
| Select, render and check an authored visual | [learning-visuals](../.agents/skills/learning-visuals/SKILL.md) | Technical visuals and image/renderer execution guides |

Use skill discovery when the agent supports repository skills; otherwise read the entry file directly. Resolve its relative links from the file's directory. These short entries do not duplicate the policies or override the learner's profile. Only load the relevant workflow, lesson and requirement passages.

## Role allocation

The familiar names below are deployment examples. A different installation may combine roles or use other names. Grant capabilities by responsibility, not by display name.

| Role | Relevant entries | Needed access | Outside that role's normal work |
|---|---|---|---|
| Groot: tutor | study-notes | Read the selected learner's notes and necessary evidence | Ingest, repository writes, paid generation, Drive mutation |
| Drax: ingest | ingest-notes; learning-visuals when useful | Selected learner's sources and working checkout; authorized rendering, generation and Git publication | Other learners' repositories, host administration |
| Mantis: media | learning-media; learning-visuals | Selected lesson/evidence, media work area, configured provider and destination; scoped publication | General lesson rewriting or unrestricted repository mutation |
| Rocket: general conversation | None required from this project | Conversation and separately chosen general tools | School repositories, school media credentials and learner memory |

Nightly corrections are an independent writer with the reviewed-source workflow and their own model/effort. Sharing the ingest code does not change their schedule or review authority. Preserve job IDs during migration and coordinate concurrent writers.

## Instructions are not access controls

Skills route work; tool configuration makes operations available; filesystem, execution and service boundaries enforce access. Verify all three. Hiding an ingest skill does not prevent a terminal from writing a repository. A read-only bind mount prevents modifying that mount, but does not restrict host-side tools or credentials. A profile separates configuration and memory; it does not by itself isolate the operating system.

Use a fresh Git checkout for a read-only tutor snapshot, not an operational checkout containing ignored `.env`, provider configuration or upload state. Do not embed credentials in the snapshot's Git remote. Inspect tracked contents too, and share only material appropriate to that learner. Updates happen outside the tutor session through Git. Bind only the approved snapshot into its execution environment; keep other checkouts, host home, provider secrets and the container-engine socket out.

Check native file tools, image reading, subprocesses, project skill discovery, memory, MCP tools and delegation as separate paths. A sandboxed terminal does not prove that another tool runs in the same sandbox. If the installed agent cannot enforce a required boundary, record that limitation and keep that profile disconnected until a supported configuration or separately approved change addresses it.

The image CLI's local counters and the Drive CLI's destination checks help ordinary authorized execution. An unrestricted host terminal can bypass them. Do not describe a media profile as limited to link insertion or a hard spending cap until its actual writer/provider access enforces that claim. A separate scoped publisher remains a deployment requirement for that stronger boundary; it is not supplied by these skills.

## Hermes: verify installed behavior before configuring

Read [Hermes and bots](hermes-and-bots.md) for profiles, routing, identities and scheduled work. Inspect the installed version and effective configuration, rather than copying a web example unchecked. Specifically:

* Project skill trust and per-profile skill selection affect discovery. No trust operation is part of renderer installation. A skill can also be read directly through an allowed file reader.
* Inspect individual resolved tools, not just group names. In the audited upstream implementation, `file` includes write/patch operations and `skills` includes `skill_manage`. The `safe` group includes generation and is not a school-tutor read-only preset.
* Do not assume `custom_toolsets` or an arbitrary tool name is a supported configuration key. Verify registration and selection against the installed code. Configuration menus may enable newly shipped tool groups; repeat effective-tool checks after changes and upgrades.
* Start a new profile without copying the existing profile's memory, sessions, credentials or global skills. Configure supported shared authentication explicitly where needed; never copy token files to make an example work.
* Choose the minimum tested tools for the pilot. If skill-management tools cannot be separated from skill readers through supported configuration, keep that group off and use the repository entry through file reading. Do not patch Hermes or add a global skill to work around the group.

This is a compatibility checklist, not a claim that the live profiles are already restricted. Official references: [profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles), [configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration), [project skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills), [toolsets](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference). Record the installed commit and any discrepancy in the private deployment inventory.

## First rollout: disconnected tutor pilot

Prepare and review the actual machine-local configuration before applying it. A minimal first step is one learner's CLI-only tutor, with no Discord token, route or scheduled job. The current gateway keeps serving its existing channels while this isolated pilot is checked.

1. Record the baseline: source/version, service status, selected nonsecret configuration, current profiles and job IDs. Keep a private rollback copy of the configuration being changed; do not include credentials in the report.
2. Review any new runtime installation separately. A container backend requires its engine and permissions; installing plotting tools did not install or authorize that engine. Record package versions, service startup, user/group changes, image digest and disk use. Do not expose a container-engine socket inside the agent environment.
3. Create the pilot profile with supported `hermes profile create` options such as `--no-skills --no-alias` after checking the installed help. Select the model/effort, explicit tools, execution backend, read-only snapshot and per-profile skill behavior. Keep all third-party agent code unchanged.
4. Exercise actual tool calls against synthetic canaries: read an allowed lesson; reject writing it; reject sibling-repository and host-secret reads, including via vision; reject host execution and unapproved tools. Check the resolved working directory and that no credential or unintended environment variable enters the sandbox. A temporary scratch write inside a container is distinct from a wiki write.
5. Ask a real study question and a practice question. Confirm useful source-linked answers, appropriate scope and no publication or paid media call. Record exact model/effort behavior rather than relying only on a saved key.
6. Only after acceptance, propose the specific Discord route and fallback changes. Then test authorized and unauthorized channels/users, mention behavior, direct messages and learner separation. Preserve existing nightly jobs until their own migration is verified.

An execution backend such as Docker is one supported isolation option, not a template dependency. Container-network restrictions do not by themselves disable host-side provider calls. Test the chosen configuration end to end before claiming isolation.

### Reproducible access probe

The optional [check_hermes_tutor.py](../tools/check_hermes_tutor.py) runs on the operator's host with the installed Hermes Python runtime. It imports that installation's configuration resolver and actual tool handlers, creates temporary synthetic fixtures, checks them through the configured Docker backend, then removes the fixtures. It does not install software, change configuration, call a model or inspect real secret contents. Read its prerequisites before running it; it deliberately depends on audited Hermes internal interfaces, and an incompatible version requires a fresh audit.

Use a separate, disconnected non-default profile, a fresh learner Git snapshot without `.env`, and a different checkout for the sibling-canary test. The profile must explicitly configure Docker, one snapshot bind mount at the same absolute path with `:ro`, no forwarded environment, no network, and no automatic current-directory mount. Check native profile cache/scratch mounts too. The probe permits its profile's read-only media/skill directories and the native per-task scratch home/workspace; it does not permit mounting the whole Hermes profile or host home. The scratch directories are writable working space, not access to the real host home.

From the Git checkout, substitute the locally discovered paths:

```sh
/path/to/hermes-python -I tools/check_hermes_tutor.py \
  --hermes-root /path/to/hermes-agent \
  --profile-home /path/to/.hermes/profiles/tutor-pilot \
  --snapshot /path/to/readonly/learner-notes \
  --other-repo /path/to/other-notes
```

Use the ordinary Hermes user's Docker permissions, not a root-owned Hermes session. `hermes --print-runtime-command` identifies the runtime in installations that support it. A new login or `sg docker -c '<command>'` activates newly granted group membership for the pilot without restarting the existing gateway. This is an operator action, not a tool exposed to the tutor.

The JSON result records individual checks, resolved tools, mount paths, environment variable **names**, and the configuration hash. It first proves an allowed read works; a broken backend cannot pass merely by denying every operation. Temporary fixtures are created under ignored `.visual-runs/` in the two checkouts and under `/var/tmp` on the host. Hermes may redirect Python's default temporary directory to its own permitted media cache; that cache is not a valid denied-host fixture. The image checks exercise the real image-source resolver without a paid semantic vision call.

After a pass, run a bounded, source-linked study question with the normal profile CLI and verify tool events, answer and unchanged repository state. Confirm selected model/effort through actual execution. A passing probe does not prove all future tools, arbitrary sandbox escapes, Discord routing, semantic image accuracy or a hard disk quota. The native Docker backend may retain its labeled test container and profile-local scratch after the process exits; record and stop that pilot container when done, without touching other containers. A storage-driver warning about missing disk quotas must remain visible in the deployment record.

For rollback, disconnect the new route/profile first, stop its test session/container and restore only the configuration changed in that step. Remove a runtime only after checking that no other service uses it. Leave the existing gateway, learner history, provider state and source repositories intact. Record tests, limits, pending approval and the next stage in the [system inventory](system-guide.md#documentation-contract-for-every-change).
