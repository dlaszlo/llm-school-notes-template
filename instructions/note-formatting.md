# Note formatting and provenance labels

Use the localized strings in [PROFILE.md](../PROFILE.md) and the content rules in the [content rules](content-and-curriculum.md). These examples implement the compact label layout without changing source categories, content authorship or the learning content. Existing pages are migrated only in the authorized scope; a rule update does not trigger a whole-wiki rewrite. Apply to the current user-authorized migration scope; the earlier two-page pilot does not restrict a later explicitly requested subject-wide migration.

## Meaning before styling

| Marker | Meaning |
|---|---|
| 💡 | Explanation of the taught content |
| ➕ | An addition beyond the supplied lesson |
| ⚠️ | A correction, with the original source claim and reason preserved |
| 📗 | Textbook-only or background material, as specified by the label |
| 🤖 | Machine authorship; combine with the relevant role icon, never a quality or verification badge |

Use the role icon, one space, the author with `🤖` attached directly, then one space and the role: `💡 Drax🤖 magyarázata`, `➕ Drax🤖 kiegészítése`, `⚠️ Drax🤖 javítása`. These names are examples, not defaults. Preserve the actual author (such as Codex, Opus, Drax or a documented combination); a formatting pass does not transfer authorship. If evidence cannot establish the author, use the localized generic machine label, not an invented name. Do not attribute text to an image-generation model. Pure notebook or teacher material to learn needs no redundant notebook label. Preserve citations everywhere, including mixed-source passages.

## Compact textbook label

Use exactly the localized textbook label from PROFILE, in Hungarian `📗 A tankönyv alapján`. Do not append boilerplate such as `(a füzetben nincs)` or `saját megfogalmazás`, or turn the label into an editorial explanation. The root legend explains the source category once. Put precise book/page locations in citations or the existing textbook metadata line, not inside the label. Independently necessary explanation/correction labels retain their actual authorship and scope. Keep pedagogically relevant source limitations in the teaching prose. This compact wording does not relax independent wording, citation, no-copy or source-verification requirements; apply it consistently to topic pages, recaps, glossary cells, captions and answers.

## Context before the learner needs it

The learner should understand what each passage concerns, why it belongs here and what can be concluded, without reconstructing the editor's thinking. Introduce the necessary concepts and notation before using them. Connect a new step to what has already been explained; make a change of example, convention, source or assumption explicit when it matters. For a diagram, supply the task and how to read unfamiliar marks before expecting a conclusion. An independently usable recap, caption or expanded answer needs its own short bridge when the surrounding context is insufficient. Do not force every passage into a fixed multi-heading template or repeat already established context. Match support to prerequisites established in the reading sequence or explicitly supported by the lesson and profile; age, grade and the existence of an earlier note do not prove understanding. Supply a short local bridge for an essential prerequisite that has not been established. Adapt depth and explanation, never disciplinary accuracy. A prerequisite bridge may revisit simpler earlier material; that does not authorize an unrelated expansion ahead of the lesson. A summary-first layout remains valid: give its unfamiliar symbols or conventions a short local explanation without moving the whole course above the summary.

Use the subject's established terminology consistently; explain it without replacing it with an ambiguous everyday near-synonym. Distinguish the concept from the property being discussed. For example, a scalar torque calculation reads "a forgatónyomaték nagysága = az erő nagysága × az erőkar hossza"; define the moment-arm length as the perpendicular distance to the force's line of action. This is one example of a cross-subject rule, not a physics-only exception. Where meaning depends on a model, analysis convention, historical context, interpretive framework or religious tradition, identify the relevant frame. Examples include word class versus sentence function, author versus narrator, historical event versus a source's account, and a religious teaching versus an interpretation of it. These illustrate the principle; they are not a closed subject list or compulsory caveats for every sentence. Do not infer a learner's personal belief from the subject studied. Keep the relevant convention and conditions visible; do not introduce false precision beyond the evidence.

Use precise referents: "the length of the moment arm" rather than an unexplained "dimension"; "the date of this event" rather than a bare "date". Do not leave a reader wondering whether missing information is a deliberate puzzle. Distinguish:

* **Source omission:** say which source lacks which detail. If context resolves it, give the basis immediately and distinguish the completion from what is actually written. If it cannot be resolved, explain the consequence for this task; raise a numbered open question only if a material uncertainty remains.
* **Unreadable or incomplete capture:** say that the photograph/crop does not show the detail clearly. This does not establish that the notebook or original document omitted it.
* **Exercise unknown:** name what the learner must determine and the available information. Do not call an intentionally unknown result a source defect.
* **Chosen simplification or optional omission:** explain the relevant modeling limit or scope, without attributing an unverified intention to the source author.

For example, replace "The value is missing; see below" with "The notebook leaves the force magnitude blank in the data row, but uses 80 N for that force in the calculation. We use that stated value here." Replace an unexplained "There is no unit" with "The notebook does not give a unit for these position coordinates. They locate the force in the sketch; this calculation uses the force magnitude and angle, so no position unit is needed." These are example patterns, not facts to copy into a lesson. A parenthetical such as "(the notebook also leaves this blank)" can identify the source of a gap, but is insufficient if the learner still cannot tell what the gap changes.

Keep source-omission commentary beside the relevant diagram, not printed on it. Retain necessary symbols, intentionally unknown quantities and uncertainty indicators that carry subject meaning. Do not silently insert an inferred value into a faithful source reconstruction. An interpreted/completed diagram must be identified as such in adjacent prose. Keep the source summary faithful; the topic page teaches the supported completion with the appropriate existing label. Do not hide a limitation that affects learning in an HTML comment. Technical extraction and generation notes that do not affect learning stay in comments/evidence.

**Reading-order check:** read the finished passage as a learner who has the stated prerequisites but has not seen the source or the editing conversation. At each new statement, symbol, visual or result, check: can I name what this refers to, understand why it appears, follow the reasoning so far, and distinguish given facts, derived results and remaining unknowns? Can I understand the main point without following a link merely to obtain a missing prerequisite? Repair the first confusing point where it occurs, not only in a later FAQ. This is a semantic review, not a keyword lint or a claim that every reader has understood the page. Apply it to teaching prose, summaries, captions, diagrams and expanded answers, including editorial clarification beside a literal transcription. Report an imprecise term, ambiguous referent, missing condition, unsupported source completion or prerequisite introduced too late when it could change understanding. For each finding give **exact location and quoted passage → ambiguity or missing bridge → likely learner misunderstanding → smallest supported correction**. Distinguish a confirmed error, unresolved source reading and optional improvement; an explicitly stated valid convention is not an error merely because another convention is familiar. Check the source/evidence before alleging an omission. Apply *Reading handwritten sources* in [Wiki workflows](wiki-workflows.md) as well: use the whole relevant topic, calculations, units, diagrams, parallel source passages and disciplinary knowledge to resolve a suspected typo. An unambiguous supported resolution is a labeled correction/completion; several plausible readings remain an uncertainty, not a fabricated certainty. This applies to the first notebook in a new subject as well as ongoing corrections and reviews. Do not mechanically replace every short expression once its meaning is unambiguous.

## A block and its small footer

```markdown
> [!TIP]
> Az állatok is kommunikálnak. A kutya a farkcsóválással jelez.<br /><sub>💡 Drax🤖 magyarázata</sub>

<br />

> [!NOTE]
> A tankönyv megértése alapján, saját szavakkal készített, pontos forráshellyel jelölt kiegészítés.<br /><sub>📗 A tankönyv alapján</sub>
```

Keep GitHub's generated TIP/NOTE/WARNING heading; do not repeat it with a large manual heading. The role and author appear once, in the small footer after the content. A multiline list or table gets one footer after the block, separated by a quoted blank line where Markdown needs it. For a simple paragraph, keep the `<br /><sub>...</sub>` suffix on the same Markdown source line as the text; a separate quoted line can produce a second break in GitHub. Do not introduce an empty paragraph between a simple sentence and its label. Never collapse different source categories into one footer that falsely applies to the whole block. Split passages when needed. A list item, recap bullet or table cell can end with its own `<br /><sub>...</sub>` label.

## Metadata and breathing room

Use a small metadata line. When lesson date and textbook location apply to the same section and are adjacent, combine them in lesson-first order with a middle dot; do not move a date across unrelated material simply to combine labels.

```markdown
<sub>🗓️ Óra: 2026-09-11 · 🔖 Tankönyv: 1. lecke, 12-13. oldal.</sub>
```

Use one standalone `<br />` between substantial sections or adjacent callout blocks where needed for the agreed spacious layout. Avoid stacked breaks and a break immediately after a heading. Place a passage's label before the larger gap so it remains visibly attached to that passage. Do not shrink teaching prose, use custom CSS/colors or replace searchable labels with badge images. Rendered size and theme remain the viewer's choice.

## Expandable self-tests

```markdown
<details><summary>1. Mit állít a tanult anyag?</summary>

<dl><dd>

<br />

Az egyszerű, forráshű válasz itt áll, robotcímke nélkül.

A válaszhoz szükséges külön magyarázat.<br /><sub>💡 Drax🤖 magyarázata</sub>

A forrásban szereplő hiba helyesbítése, az indokával és hivatkozásával.<br /><sub>⚠️ Drax🤖 javítása</sub>

<br /><br />

</dd></dl>

</details>

<details><summary>2. Mi a következő fogalom jelentése?</summary>

<dl><dd>

<br />

A rövid válasz.

<br /><br />

</dd></dl>

</details>
```

The questions remain compact when closed. The `<dl><dd>` wrapper indents only the opened answer using ordinary HTML, without a code block, visible bullet or quote color. Preserve blank lines so the answer remains Markdown. Exact indentation is viewer-dependent. Within one answer use ordinary paragraphs, not an extra standalone `<br />` between explanation and source passage; use one standalone `<br />` before the first answer paragraph and `<br /><br />` after the last paragraph, inside the wrapper. These boundary spacers are the explicit exception to avoiding stacked breaks elsewhere. Both are inside `<details>`: when closed, neither affects the spacing between questions. A question does not acquire an agent label merely because it was generated. Do not put alert syntax inside the disclosure. Preserve the distinction between the taught answer and a separate optional explanation or correction.

## Numbered open questions

Always number unresolved questions consecutively in Markdown, even if there is only one. Give each a concrete title and enough context to understand the uncertainty without searching the page. Keep the problem, relevant alternatives, their explanation and the recommendation/next step within that same numbered item. Scale detail to need: omit artificial alternatives and unnecessary subheadings, but never omit the context or what would resolve the question. Do not turn an established correction into a choice between equally valid answers. Use explicit `1.`, `2.`, `3.` markers in the file and indent continuation paragraphs by three spaces. This section is separate from self-tests; it records unresolved issues, not quiz answers.

```markdown
# Nyitott kérdések

1. **A konkrét tisztázandó kérdés?**

   **Kontextus:** melyik témáról, állításról vagy feladatról van szó.

   **Probléma:** mi bizonytalan, miért számít, és mit tudunk biztosan.

   **Lehetőségek:** a valóban szóba jövő változatok, indoklással és következményeikkel, ha vannak ilyenek.

   **Javaslat:** az indokolt következő lépés; milyen válasz vagy bizonyíték oldaná fel a kérdést.

2. **Egy másik, önálló kérdés?** A szükséges kontextus, bizonytalanság és következő lépés röviden is elférhet egy bekezdésben.
```

## Explanatory images and exports

Distinguish **what the content is based on** from **who generated the image**. An agent arranging textbook or teacher facts visually has not thereby added a new explanation. Do not label every generated image with "Codex's explanation" or the equivalent. Keep the maker, image model and prompt in comments/evidence. A visible role/author label is for a substantive agent-added explanation, addition or correction, attached only to that contribution. This applies equally to prose and images.

Source labels must have a clear scope. Attach a paragraph's small label to that paragraph; a NOTE block can enclose a longer reference-only explanation. For a source-based image, name the relevant content in a short caption when needed: for example, identify the two clauses being compared and which reference supports each. For a mixed-source image, identify the textbook-only part rather than tagging the whole image as textbook-only. Do not leave a generic source label floating between prose and an image, and do not use a machine label to replace factual attribution. References and prose retain the teaching meaning. Teacher photos keep their class-material attribution. Decorative banners need no maker credit; exact model, prompt, cost, hashes and observations stay in comments/evidence. A caption-only correction does not authorize regeneration.

Keep the teaching content and source markers as ordinary text so non-GitHub viewers and future PDF rendering retain their meaning. An export may style the small labels consistently, but cannot remove their meaning or use color alone to distinguish provenance. This document defines Markdown layout, not an implemented PDF pipeline.

## Authorized whole-subject maintenance

An explicit request to update a complete subject (in the owner's `school-notes chat` session) applies these rules to its topic pages, source summaries, chapter summaries and subject index. Inventory the scope, examine the source/evidence and relevant bounded curriculum passages, then apply semantic corrections and formatting together. Propagate a correction to summaries, quizzes and affected captions. Preserve faithful source transcription and all precision-dependent teaching diagrams. Select banners and optional visuals by the existing visual workflow. Finish with source coverage, reading-order review, the MCP `check` and `finish`. Do not treat a formatting-only request as authorization for unrelated ingestion or a paid visual batch.
