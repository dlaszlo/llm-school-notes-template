# LLM school notes - wiki template

Photograph your notebook, and an AI agent turns it into clear, curated study pages.

This is a template for a knowledge base (an "LLM wiki") built from one student's school notes. You drop in photos of exercise-book pages, downloaded notes, or voice notes; an LLM agent - [Claude Code](https://code.claude.com/), [Codex](https://developers.openai.com/codex/), or any agent that can read `AGENTS.md` (e.g. Hermes Agent) - files them, reads them, and maintains a wiki: one directory per subject, one page per topic, plus a page per set of lesson notes. The storage format is the [Open Knowledge Format 0.2](SPEC.md): plain markdown with YAML frontmatter, readable on GitHub, in Obsidian, or with `cat`.

The template contains no names, school, subjects, textbooks, or notes - everything specific is set up by the LLM on the first run.

## What the pages look like

* **Faithful and curated at the same time.** A lesson-notes page records exactly what the notebook says. The topic pages teach: they explain terse notes, redo worked problems step by step, fill gaps, and fix errors - every addition visibly marked as *not from the notebook* (colored callouts: 💡 explanation, ➕ addition, ⚠️ correction).
* **Two layers.** Every topic page opens with a ⚡ *In short* box for the evening before a test; chapters get a summary page; the full detail stays on the topic pages.
* **🧠 Test yourself** questions with hidden answers at the end of each topic page.
* **Plain language** at the student's level (ISO 24495-1 principles), phone-friendly tables, LaTeX math, Mermaid diagrams, and colorful header banners (`tools/banner.py`).
* **Catch-up support**: notes copied from a classmate's notebook are marked 🤒 until the student has caught up; homework from the e-diary goes into a 📌 table.
* **Textbook references**: textbooks (converted to text) in `references/` are used to check readings and cite printed page numbers - never copied.

## Getting started

1. Click **Use this template** on GitHub and create a **private** repository (notebook photos and textbooks are private working copies - see below). A repository created from a template starts with a clean history.
2. Clone it and open it in your agent (Claude Code reads `CLAUDE.md`, Codex reads `AGENTS.md`).
3. Say *"Initialize the wiki"*. The agent asks for the student's first name, grade and school year, the wiki language, the audience, and which standing authorizations you want (e.g. automatic ingest and push), then sets everything up. English and Hungarian wording ship ready; other languages are translated at bootstrap.
4. Drop notes into `sources/` under any name and ask the agent to ingest them (or let it do so automatically if you allowed that). Subjects appear with the first notes.

Daily use: ask questions (useful answers can be filed back as pages), report homework, and request a lint pass now and then. Read the wiki from `wiki/index.md`.

## Privacy

* `wiki/` never contains grades, test results, names of private individuals (classmates, teachers), opinions about teachers, health or family data, or the name of the school, its town, or the class. The student's first name is the only personal name.
* `sources/` (notebook photos, raw notes) and `references/` (textbooks) are private working copies: never publish them. If you ever make a copy of the wiki public, publish only `wiki/`.
* No secrets anywhere - git history is forever.

## Layout

```text
AGENTS.md           The complete operating manual (rules, page templates, workflows).
CLAUDE.md           Thin Claude Code adapter importing AGENTS.md.
SPEC.md             Pinned OKF 0.2 specification.
llm-wiki.md         Original idea document, preserved as background.
tools/banner.py     Page-header banners; subjects and labels in tools/subjects.json.
sources/            Immutable source material (private).
references/         Converted textbooks for checking and citing (private).
wiki/               Knowledge bundle, index, and update log.
```

There is one operating manual, so Claude Code and Codex do not maintain conflicting copies. Automatic loading is documented by [OpenAI](https://developers.openai.com/codex/guides/agents-md/) and [Anthropic](https://code.claude.com/docs/en/memory).

## Credits

* The LLM-wiki pattern is by [Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), preserved in [llm-wiki.md](llm-wiki.md).
* The OKF specification is from [Google Cloud Platform knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog), pinned in [SPEC.md](SPEC.md).
