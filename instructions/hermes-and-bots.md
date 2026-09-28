# Hermes, bots and scheduled work

This is an optional deployment example, not a prerequisite or a statement about a new user's installation. Read it as part of the [system handbook](system-guide.md). It explains the proposed role model and the known deployment baseline separately. Actual settings, routes and access tests belong in the private deployment inventory; this public template contains no configured child identities or channel IDs.

## What each component does

* A **Discord bot identity** is an application/bot token and visible sender. A display name does not grant authority.
* A **Hermes profile** holds an agent's configuration, model/provider, effort, tools, memory and session context. Merely creating a profile does not prove filesystem isolation.
* The **gateway** receives platform messages and selects the profile using trusted routing metadata. User/channel allowlists decide admission; profile routing does not replace admission checks.
* A **skill** supplies task-specific instructions and helpers. Our optional media tools run directly from the repository through the terminal; no global skill or additional MCP server is required.
* A **scheduler job** is an independent invocation with its own model/effort, repository, timezone, instructions and delivery target. It need not be a fifth conversational bot.

## Roles and intended model allocation

### Repository skills and profile capabilities

Keep three layers separate: `AGENTS.md` contains daily invariants, `instructions/` owns detailed workflows, and a repository-owned skill is a short task-specific entry point. The first such entry is [learning-visuals](../.agents/skills/learning-visuals/SKILL.md); it is usable by both ingest and media roles. A skill name describes a reusable task, not a bot identity. The installed renderer is a fourth, executable layer: a skill describes when/how to use it, and does not install or authorize it.

Current upstream Hermes supports project skills under `<checkout>/.agents/skills/`. From the selected profile and checkout, `hermes skills trust <checkout>` records an explicit project trust decision; verify this command and behavior against the installed version first. For gateway/cron jobs, verify the resolved repository working directory too. Do not enable trust or alter a profile as a side effect of installing a renderer. The full checkout travels through Git; do not copy this skill into a global Hermes skill directory. Directly reading the linked instructions remains a usable path in an agent without skill discovery.

Configure model/effort, gateway identity/routing, enabled skills, toolsets, MCP connections, credentials and execution boundaries per profile. Groot needs learning-material read access; Drax needs scoped ingest/write access; Mantis needs authorized generation and scoped media insertion/delivery; Rocket needs no school checkout. Sharing a renderer installation does not require exposing execution to every bot. Skill filtering controls discovery, not security: an unrestricted terminal can still execute an installed program or read writable external skill files. Enforce read-only and learner-specific access in the execution/filesystem layer and test denied operations. A profile's separate memory alone is not a sandbox.

Repository skill discovery and capability filtering are deployment configuration, not changes to Hermes source or bundled skills. This section describes the integration contract; it does not claim that separate profiles, skill filters or isolation have been deployed. See upstream [project-local skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills#project-local-skills) and [profiles versus sandboxing](https://hermes-agent.nousresearch.com/docs/user-guide/profiles#profiles-vs-workspaces-vs-sandboxing).

### Initial allocation

| Role | Responsibility | Proposed initial model/effort | Deployment status |
|---|---|---|---|
| Groot | Explain existing learning material, practice and answer questions; no ingest in the separated design | GPT-6 Sol / medium | Existing shared bot currently also performs ingest; role separation pending |
| Drax | Ingest and verify notes; choose an appropriate visual and request/create an authorized infographic | GPT-6 Astra / medium | Separate role pending |
| Mantis | Plan, create and inspect media; deliver accepted versions and maintain their scoped links | GPT-6 Astra / high | Separate role pending; common repository media instructions and Drive CLI available |
| Rocket | General conversation without school repositories | GPT-6 Sol / medium | Separate role/channel pending |

These are user-discussed starting choices, not a benchmark or a statement of model availability on every account. The audited shared bot used GPT-6 Astra / medium through the existing subscription provider. Verify every model/effort pair in the actual Hermes account before deployment. Image/TTS provider settings are separate from the conversational model; selecting a role model does not configure image or voice generation.

## Routing and learner separation

The design uses one learner-specific profile per school role (conversation, ingest, media), plus a general conversation profile. Multiple visible Discord identities require their own platform credentials; multiple profiles do not automatically create Discord accounts. One adapter owns a bot token, and supported multiplex routing directs the bot/channel combination to the appropriate profile. Keep a restricted fallback for unmatched routes and test direct messages separately.

In the audited baseline, the common-room channel required mentioning the bot, while the private learner channels received replies without a mention. Identity was based on numeric user IDs. The gateway's multiplex capability existed, but separate learner/role routes were not deployed. Existing common-profile memory must not be copied indiscriminately to new child profiles. Current channel membership and invitation acceptance must be rechecked at rollout, not inferred from an old plan.

Test permissions at each layer: Discord visibility/admission; route choice; memory/session ownership; allowed tools; accessible filesystem paths; repository writes; provider credentials and budgets; Drive destination. A prompt saying "only this child's folder" is insufficient if the agent can read all credentials or invoke unrestricted APIs. The Drive CLI currently enforces its own target and input rules; the shared Unix account remains capable of bypassing it.

## Ingest and media cooperation

The ingest role owns the lesson and decides whether a visual helps. It may run the same authorized media workflow or hand a scoped request to the media role using the deployment's existing task mechanism. [The handoff contract](media-handoff.md) specifies identity, source hashes, target/version, attempts, costs, idempotency and publication. It does not prescribe an uninstalled second queue or claim Hermes synchronous delegation is already wired up.

The media role has a narrow reason to write Markdown: insert the accepted artifact link, caption and observed description/provenance. That does not give it general ingest authority. Publication rechecks the lesson version and coordinates with other writers, including the scheduled correction process.

## Nightly review and correction

The existing workflow has two stages. A cloud reviewer checks out the repository and writes findings. A scheduled Hermes correction reads those findings, inspects the underlying evidence, applies only supported changes and records the outcome. The parent reported the reviewer as Claude Opus 5.5; its remote execution configuration was not directly inspected. The audited correction jobs used GPT-6 Astra / high, separately for each learner, preserving that effort independently of ordinary ingest.

The intended local schedule is `45 23 * * *` with IANA timezone `Europe/Budapest`. An audit found the next run stored as 23:45 UTC instead of 23:45 local time; the host timezone and scheduled state were corrected. Hardware clock/UTC timekeeping and NTP were not shifted to fake local time. Store the timezone, cron expression and computed next run together; verify daylight-saving behavior using the scheduler's timezone handling rather than a fixed UTC conversion.

Before migrating jobs, retain their IDs, repository paths, exact instructions, delivery channels, model/effort and authorization. Do not create duplicate jobs. A successful no-work run proves empty-queue handling, not correction accuracy. Review-not-yet-ready differs from completed review with no findings. A local repository lock coordinates local writers, but cannot lock an independent cloud checkout; recheck current commits before publishing.

Reviewers need access to the same evidence, including Drive artifacts when a visual/audio conclusion depends on them. A transcript or image-description comment cannot substitute for hearing/seeing the artifact. If the reviewer lacks access, report an unverified question rather than a confirmed error.

## Operating and changing Hermes

Use the installed `hermes` wrapper and its package manager rather than assuming a virtualenv path. Record the output versions and actual service unit in the private inventory. Read existing settings before altering routing, profiles, credentials or scheduler jobs. Back up the affected configuration, make one bounded change, test normal and rejected routes, and record how to restore it. A gateway restart is a deployment action; do not restart merely because a skill file was copied.

A full rollout still requires explicit credential setup for new bot identities, verified profile/tool/filesystem boundaries, route and mention tests, media-provider/budget enforcement, a real ingest/media pilot, and scheduler coexistence checks. Keep that remaining work visible alongside completed steps.

Upstream references: [profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles/), [multiplex gateways](https://hermes-agent.nousresearch.com/docs/user-guide/multi-profile-gateways), [skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills), [installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation/). Check them against the installed commit before applying version-sensitive configuration.

## Common image executor

Read the checked-in [CLI and setup guide](learning-image-execution.md) directly from the selected repository; no globally installed skill is needed. It can be used by the current ingest bot or a later Drax/Mantis profile with trusted private configuration. The caller plans and directly views the image; the executor enforces local source/target, budget, attempt and review-hash checks. This capability does not require a new bot, and its local CLI test does not establish live gateway routing or OS separation.
