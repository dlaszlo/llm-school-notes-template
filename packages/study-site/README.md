# Study site — local Markdown preview

An optional, shared Astro + Starlight renderer for existing school-note Markdown. It does not rewrite the source or ingest lessons. Source files, personal settings and publication configuration stay in the learner's private repository; this package stays in the template checkout. Do not copy it into a harness or install a global agent skill.

**Version 0.1.0 is a local preview milestone, not a public publishing pipeline.** The exporter rejects `mode: public`. Private preview pages may include source summaries, dates and explicitly configured links to private archive files. Bind the preview to localhost. `noindex` is an additional hint, not access control. There is no VM installation, scheduler, Drive move or paid generation in this package.

## Install from Git

Use Node 22.12+ (tested with Node 24.12.0), npm, and an installed Chromium compatible with the pinned Playwright. On the same machine, the existing page-check browser can be reused by passing its executable path. No browser is downloaded automatically.

```sh
git clone <template-repository> template
git -C template checkout <reviewed-template-commit>
cd template/packages/study-site
npm ci --ignore-scripts
npm test
```

All direct dependencies and the transitive lock are committed. `npm ci` writes only this package's dependencies. Astro telemetry is disabled for the CLI build. The package is versioned by its template Git commit; it is not part of the shared-file set copied into learner repositories. The existing `AGENTS.md` and shared policy release are unchanged.

## Input configuration

Keep `publication/pilot.json` in the private learner repository. This is a deliberately explicit, hash-bound manifest, not automatic publication permission. Ordered `pages` define previous/next order. The sidebar contains only the home page (`wiki/index.md`) and subject indexes (`wiki/<subject>/index.md`); topics remain accessible through those indexes and search. Topic pages include a link back to their subject. Only referenced, allowlisted assets are copied.

```json
{
  "version": 1,
  "mode": "private-preview",
  "title": "Saját jegyzetek",
  "base": "/sample/",
  "pages": [
    {"path": "wiki/index.md", "sha256": "<64 lowercase hex characters>"},
    {"path": "wiki/subject/index.md", "sha256": "<64 lowercase hex characters>"}
  ],
  "assets": [
    {"path": "wiki/assets/header.webp", "sha256": "<64 lowercase hex characters>"}
  ],
  "privateLinks": {},
  "collections": [
    {"id": "subject", "title": "Tanulási jegyzet", "pages": ["wiki/subject/index.md"]}
  ]
}
```

`privateLinks` maps an explicit repository-relative path to an HTTPS GitHub archive URL, preferably pinned to a full commit. Only ordinary links may use this mapping, never images. The rendered link gains “(privát forrás)”. An unlisted dependency, changed source hash or invalid formula stops the build; it is not silently omitted. Review a source change before updating its manifest hash. An index-only book stays index-only.

## Build and inspect

```sh
node cli.mjs build \
  --repo /path/to/private-notes \
  --config /path/to/private-notes/publication/pilot.json \
  --output /path/to/private-builds/unique-build-name \
  --browser /path/to/chromium

node cli.mjs serve \
  --directory /path/to/private-builds/unique-build-name/site \
  --base /sample/ --port 4321
```

Open `http://127.0.0.1:4321/sample/`. Stop the foreground server with Ctrl+C. Choose a new output directory per build; an existing directory is never overwritten. Keep the build directory outside the input repository. No source repository is used as Astro's content/public directory: the renderer receives only the exported payload and selected assets. The build output includes:

- `payload.json`: generated title/body/routes/print content, with private frontmatter and HTML comments removed. It is still **private-preview** content.
- `public/media/`: copied approved images with content-addressed names, plus locally rendered Mermaid SVGs. Original input files remain unchanged.
- `receipt.private.json`: input hashes, source paths, formulas, labels and asset transformations for review. Never publish this file.
- `site/`: generated static HTML, CSS/JS, images and Pagefind index. Not committed to the learner repository.

The responsive layout uses equal 16rem navigation rails, a central content area up to 60rem and paragraphs up to 78ch. Screen banners fill the content width and keep their original aspect ratio without cropping or distortion. Their height follows the source image ratio (no independent screen height cap); the central column remains bounded at 60rem. Print banners retain a 35mm height cap. GitHub-only spacer paragraphs are hidden; web heading margins provide section separation. The shared book mark and subtle header colours require no external image or font.

The UI includes search, light/dark/system theme, a single H1, a semantic heading outline, source footers, keyboard-native answers and full-size image links. Large formulas/tables scroll within their region. Technical SVGs retain geometry and colours on a light panel; no colour inversion or diagram replacement takes place. A real chemical/math `<sub>` is preserved; only recognized source labels become small footers. The original Mermaid text and formulas are recorded in the private receipt.

The print collection uses the same rendered material, with complete self-test answers moved to its final section and page-local footnote IDs namespaced. It excludes duplicate search results. A4 CSS and a print button are included; **a final, page-by-page reviewed PDF is a separate deliverable**, not something certified by a successful HTML build. Screen-reader testing of the formulas also remains a separate acceptance check: the current SVG has the original TeX as an accessible label, not a claim of full spoken-math support.

## Verification

```sh
npm test
node check-browser.mjs \
  http://127.0.0.1:4321 \
  /path/to/private-builds/unique-build-name/payload.json \
  /path/to/chromium \
  /path/to/private-builds/unique-build-name/browser-report.json \
  "a known search term"
```

The tests cover comments/frontmatter, paths and symlinks, source hashes, asset allowlists, HTML/SVG active content, formulas, true subscripts, duplicate headings, Mermaid line breaks and print footnote references. The browser check visits every page in both themes at desktop, mobile and 320px widths, opens all answers, checks images/anchors/overflow, and exercises Pagefind. Visually inspect representative pages, exact diagrams, expanded answers, and print output too; these tests do not prove pedagogical correctness or WCAG conformance. Receipts and real-corpus screenshots belong in private storage.

## Restoring archived source data

An initial migration may keep notebook originals in an immutable private archive instead of duplicating their binary history. This requires a retained, accessible archive, independent backup, `ingest-manifests/archive-sources.json` with exact file hashes, and tracked ignore entries at the original data paths. The normal relative source paths can then be hydrated for a reviewer:

```sh
git clone <private-archive-repository> /path/to/archive
git -C /path/to/archive checkout <recorded-archive-commit>
node hydrate-archive.mjs /path/to/private-notes /path/to/archive
```

The helper restores only `sources/` and `references/` data, checks every SHA-256 and never overwrites a different existing file. It is not code deployment and needs no copied credentials. Do not delete the archive or its backup until the later Drive archive and reviewer access are proven. This transitional archive mechanism is not the planned final Drive integration.

## Basis and next boundary

The layout uses the documented [Starlight custom-page component](https://starlight.astro.build/guides/pages/#using-starlights-design-in-custom-pages), its [configuration](https://starlight.astro.build/reference/configuration/) and [search](https://starlight.astro.build/guides/site-search/). The adapter processes syntax trees; generated HTML is an expendable derivative, not a second authored lesson.

Before public release: approve page/asset rights, handle private sections and source links, scan the complete output including metadata/search/assets, complete accessibility and print acceptance, and implement the separately authenticated Release → Pages deployment and rollback. Do not enable public export by simply removing the pilot guard.

## Optional site identity

The learner publication configuration can supply `branding.light` and `branding.dark`, each with a `path` (a PNG directly inside `publication/assets/`) and SHA-256 `sha256`. Both are required if branding is configured. The exporter verifies and copies them as content-addressed assets; it does not fetch remote logos. Use small square PNGs (128px is sufficient; each must be below 1 MiB). The header icon and favicon follow the selected site theme. Without branding, the neutral book mark remains. Organization-specific artwork belongs in the site configuration, not in this reusable template.
