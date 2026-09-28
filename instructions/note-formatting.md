# Note formatting and provenance labels

Use the localized strings in [PROFILE.md](../PROFILE.md) and the content rules in [AGENTS.md](../AGENTS.md). These examples implement the compact label layout without changing source categories, content authorship or the learning content. Existing pages are migrated only in the authorized scope; a rule update does not trigger a whole-wiki rewrite. During the two-page preview, leave other topic pages as they are.

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

Az egyszerű, forráshű válasz itt áll, robotcímke nélkül.

A válaszhoz szükséges külön magyarázat.
<br /><sub>💡 Drax🤖 magyarázata</sub>

<br />

A forrásban szereplő hiba helyesbítése, az indokával és hivatkozásával.
<br /><sub>⚠️ Drax🤖 javítása</sub>

<br />

</details>

<details><summary>2. Mi a következő fogalom jelentése?</summary>

A rövid válasz.

<br />

</details>
```

The questions remain compact when closed; the spacing is inside the opened answer. A question does not acquire an agent label merely because it was generated. Do not put alert syntax inside the disclosure. Preserve the distinction between the taught answer and a separate optional explanation or correction.

## Explanatory images and exports

For an agent-authored teaching diagram or infographic, place a small role/authorship label immediately below its Markdown embed, for example `<sub>💡 Codex🤖 magyarázata</sub>`. The author's name identifies who prepared the explanation; references identify what supports it. Retain a textbook-only qualifier where a particular part comes only from the textbook. Do not add a robot to a teacher photograph or a book-source label merely because an agent embedded it. Banners do not need visible generator credits. Exact model, prompt, cost, hashes and visual observations stay in comments and evidence records, not learner-facing prose.

Keep the teaching content and source markers as ordinary text so non-GitHub viewers and future PDF rendering retain their meaning. An export may style the small labels consistently, but cannot remove their meaning or use color alone to distinguish provenance. This document defines Markdown layout, not an implemented PDF pipeline.
