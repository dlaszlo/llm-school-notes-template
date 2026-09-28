# Note formatting and provenance labels

Use the localized strings in [PROFILE.md](../PROFILE.md) and the content rules in [AGENTS.md](../AGENTS.md). These examples implement the compact label layout without changing source categories, content authorship or the learning content. Existing pages are migrated only in the authorized scope; a rule update does not trigger a whole-wiki rewrite. Apply to the current user-authorized migration scope; the earlier two-page pilot does not restrict a later explicitly requested subject-wide migration.

## Meaning before styling

| Marker | Meaning |
|---|---|
| 💡 | Explanation of the taught content |
| ➕ | An addition beyond the supplied lesson |
| ⚠️ | A correction, with the original source claim and reason preserved |
| 📗 | Textbook-only or background material, as specified by the label |
| 🤖 | Machine authorship; combine with the relevant role icon, never a quality or verification badge |

Use the role icon, one space, the author with `🤖` attached directly, then one space and the role: `💡 Drax🤖 magyarázata`, `➕ Drax🤖 kiegészítése`, `⚠️ Drax🤖 javítása`. These names are examples, not defaults. Preserve the actual author (such as Codex, Opus, Drax or a documented combination); a formatting pass does not transfer authorship. If evidence cannot establish the author, use the localized generic machine label, not an invented name. Do not attribute text to an image-generation model. Pure notebook or teacher material to learn needs no redundant notebook label. Preserve citations everywhere, including mixed-source passages.

## A block and its small footer

```markdown
> [!TIP]
> Az állatok is kommunikálnak. A kutya a farkcsóválással jelez.<br /><sub>💡 Drax🤖 magyarázata</sub>

<br />

> [!NOTE]
> A tankönyvből származó, pontos forrással hivatkozott kiegészítés.<br /><sub>📗 Tankönyvből</sub>
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
