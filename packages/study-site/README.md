# Study site — reviewed Markdown publication

An optional, shared Astro + Starlight renderer for existing school-note Markdown. It does not rewrite the source or ingest lessons. Source files, personal settings and publication configuration stay in the learner's private repository; this package stays in the template checkout. Do not copy it into a harness or install a global agent skill.

The renderer supports separate `private-preview` and explicitly reviewed `public` builds. Private preview pages may include source summaries, dates and explicitly configured links to private archive files. Bind the preview to localhost. `noindex` is an additional hint, not access control. There is no VM installation, scheduler, Drive move or paid generation in this package.

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

Keep `publication/pilot.json` in the private learner repository. This is a deliberately explicit, hash-bound manifest, not automatic publication permission. Ordered `pages` define previous/next order. The sidebar contains only the home page (`wiki/index.md`) and subject indexes (`wiki/<subject>/index.md`); topics remain accessible through those indexes and search. Topic pages include a link back to their subject. Only referenced, allowlisted assets are copied. Approved GIF images (such as unchanged official hazard pictograms) are supported alongside SVG, PNG, JPEG and WebP.

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

The responsive layout uses equal 16rem navigation rails, a central content area up to 60rem and paragraphs up to 78ch. Screen banners fill the content width and keep their original aspect ratio without cropping or distortion. Their height follows the source image ratio (no independent screen height cap); the central column remains bounded at 60rem. Print banners use the available width with a 65mm height cap, preserving their ratio without cropping. GitHub-only spacer paragraphs are hidden; web heading margins provide section separation. The shared book mark and subtle header colours require no external image or font.

The UI includes search, light/dark/system theme, a single H1, a semantic heading outline, source footers, keyboard-native answers and full-size image links. Large formulas/tables scroll within their region. Technical SVGs retain geometry and colours on a light panel; no colour inversion or diagram replacement takes place. A real chemical/math `<sub>` is preserved; only recognized source labels become small footers. The original Mermaid text and formulas are recorded in the private receipt.

The print collection uses the same rendered material, with complete self-test answers moved to its final section and page-local footnote IDs namespaced. It excludes duplicate search results. A4 CSS and a print button are included; **PDF generation and page-by-page inspection are separate from HTML build success**; use the cached PDF workflow below. Screen-reader testing of the formulas also remains a separate acceptance check: the current SVG has the original TeX as an accessible label, not a claim of full spoken-math support.

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

The tests cover comments/frontmatter, paths and symlinks, source hashes, asset allowlists, HTML/SVG active content, formulas, true subscripts, duplicate headings, Mermaid line breaks print footnote references, formulas inside HTML question summaries, figure-caption grouping and dependency-specific PDF cache invalidation. The browser check visits every page in both themes at desktop, mobile and 320px widths, opens all answers, checks images/anchors/overflow, and exercises Pagefind. Visually inspect representative pages, exact diagrams, expanded answers, and print output too; these tests do not prove pedagogical correctness or WCAG conformance. Receipts and real-corpus screenshots belong in private storage.

## Topic PDFs and incremental reuse

Add `"pdf": true` to each collection that should have a downloadable PDF. A collection may contain one topic or a deliberately ordered group of pages. It uses the same Markdown and assets as the website; no LLM rewrites the material. The subject index automatically lists its PDF collections, and a topic offers its own download. Set a topic collection’s optional `group` to its summary collection’s `id` to nest the topic under that summary in the download list. Groups are one level deep, explicitly configured, and must reference an existing top-level PDF collection; they are not guessed from titles. Grouping changes navigation only and does not invalidate the PDFs. Self-test questions stay in the lesson; complete answers and explanations follow at the end.

```sh
node cli.mjs build \
  --repo /path/to/private-notes \
  --config /path/to/private-notes/publication/pilot.json \
  --output /path/to/private-builds/new-build \
  --browser /path/to/chromium \
  --pdf-cache /path/to/private-builds/pdf-cache
```

PDF typography uses the bundled Adobe Source Sans 3 (regular, italic, semibold, bold and bold italic). The unchanged WOFF2 files, OFL license, upstream commit and SHA-256 values are in `src/fonts/source-sans-3/`; cloning this repository is sufficient for the text fonts. No OS font installation or runtime network font request is needed. Keep Fontconfig and Noto Color Emoji available for the existing emoji support. Chromium 131+ is required for page-margin headings/footers. Bundled font bytes, print CSS, browser version and the resolved emoji font file are part of the cache fingerprint.

Body and explanations use 11.5 pt with 1.45 line spacing; headings use semibold at 22/16/13 pt; source/author labels are 9 pt dark gray. Source Sans also typesets the 9 pt running title, date and page numbers. A generated topic PDF puts the title in every page's top margin; its banner stays in the content, without an additional oversized title above it. The HTML print view retains its ordinary H1; browser-managed printing may have different margin support. Mathematical SVGs and code typefaces are unchanged. Verify accent coverage and actual embedding, then render and inspect changed PDFs.

The **SHA-256 cache key** includes the collection's source hashes, rendered text/answers, content-addressed image URLs, title, base URL, print renderer code/CSS, dependency lock, Node/Chromium versions and fonts. Thus:

- Changing a topic or one of its images regenerates only PDFs depending on that content.
- A shared print style, renderer or font change correctly invalidates all affected PDFs.
- An unchanged build copies the existing PDF without invoking PDF rendering or an LLM.
- A missing or corrupt cached PDF is regenerated; the cached PDF's own SHA-256 is checked before reuse.

The static HTML site still rebuilds; this incremental cache applies specifically to PDFs. The cache directory must be private and outside the input repository and renderer package. Generated PDFs belong to build/media storage, **not Git history**. The reusable cache is safe to remove when unused; losing it only costs another rendering pass. No automatic Drive upload, remote deletion or retention cleanup is implemented here.

Outputs are `site/pdf/<collection>-<hash-prefix>.pdf` plus `pdf-receipt.private.json` outside the site, recording full keys, file hashes, inputs, timestamps and reuse decisions. A PDF shows its creation date in the footer; the exact version is in its title metadata, content-addressed filename and private receipt. A reused file keeps its original date. Source footnotes and internal references remain; relative website links are plain text in PDFs to avoid embedding a temporary localhost address. Explicit HTTPS references remain clickable.

PDFs use A4 portrait, 16mm margins, selectable body text, vector formulas and diagrams where the source allows, page numbers and separate answer sections. Images and their immediate small/italic captions stay together; headings, callouts and answer blocks receive page-break constraints. The generation check rejects oversized figures/tables/formulas, but cannot prove every page is well composed. **After a changed PDF, render and inspect every page**, e.g. with Poppler's `pdftoppm`; check clipping, formulas, captions, tables, legibility and answer placement. An unchanged PDF with the same verified file hash can reuse its earlier visual review. Do not certify a new PDF solely because the browser returned success.

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

## Public feedback

Optional `feedbackRepository: "owner/public-site-repo"` adds a footer report link with the stable GitHub Pages page URL prefilled. Install the generic form from `templates/site-feedback` into that repository and enable Issues. The link never includes localhost, a private input path or a source filename. This is a reporting destination, not automatic issue ingestion. Omit the setting when no public destination is configured. Local previews must not be described as already published Pages sites.

Teacher-image copies in the legacy `wiki/assets/orai/` directory are rejected in every export mode. This path guard is a backstop, not license recognition: reviewers must also verify independently acquired images and visible, exportable credits under the shared sources/evidence policy.

### Content license and project menu

The template does not choose a license for learner content. After owner approval, set `license` in the local publication configuration, for example `{ "id": "CC BY-NC-SA 4.0", "attribution": "Project name" }`. Supported identifiers: CC BY 4.0, CC BY-SA 4.0, CC BY-NC-SA 4.0. Attribution and license changes affect PDF cache keys. Print pages include a closing notice with third-party exceptions; generated PDFs also carry the short identifier in each footer. Preserve asset-level attribution independently.

An explicitly allowlisted Markdown page with `navigation: "info"` appears in the site menu. Use it for the project introduction, approved terms and feedback links; no family-specific content belongs in the template.

For consistent sidebar icons, supply `navigationLabel` for every menu entry in local publication configuration. Use the learner repository’s `tools/subjects.json` names and emoji for subjects; include home and project information entries consistently. This overrides only the sidebar label, without changing lesson titles or PDF inputs.


## Public release (School Notes v2)

The public site is the wiki 1:1 (plan D83): every wiki page of every type (topics, lesson notes, reviews, indexes) goes out with all its sections. There is no per-page review flag, no `omitSections` and no `publicEdits`; a page still carrying a non-empty one of these fails the build, so a stale configuration cannot pretend to filter. Files under `sources/` (notebook photos, teacher material) and `references/` (textbooks) never go out: the tool builds from a `git archive` of the commit without these folders, and every link to them is listed in `citationOnlyLinks`, which public mode turns into a plain "(nem nyilvános forrás)" quote. Any other unknown link or image fails. Frontmatter, HTML comments and executable source HTML never reach the output.

`publication/public.json` is generated by the tool. Required: `mode: "public"`, an HTTPS `site` origin, the ordered `pages` with hashes, and every asset with a `rights` class (authored/generated/licensed/public-domain/standard). `publicationApproved`, `reviewRecord`, `publicationReviewed` and `rightsEvidence` are accepted for compatibility but no longer required.

`--last-updated FILE` gives the per-page "Utoljára frissítve" dates: a JSON object mapping wiki paths to ISO dates (the tool uses the page's last commit, and the latest one for the home page). Pages without a date show none. The dates are shown in Europe/Budapest and do not affect PDFs or their cache keys.

When rendering fails on a page, `cli.mjs build` prints `study-site-page-error {"file": …, "message": …}` on stderr and exits with code 3, so the caller can send the writer back to that page; every other failure exits with 1.

`check-browser.mjs ORIGIN PAYLOAD CHROMIUM REPORT [QUERY] [ONLY.json]`: with `ONLY.json` (a JSON list of wiki paths, normally the changed pages and their indexes) only those pages are visited; the search and print checks still run. Report entries carry the page's wiki `path`.

`check-public.py BUILD` is the last gate: no secret and no machine path in any rendered file, including decompressed search data and PDF text. The patterns are in `public-patterns.json`; the tool's Markdown check reads the same file (`secrets` and `machine_paths`; `output_only` holds what Markdown legitimately keeps in comments). Source footnotes and `sources/` link texts are allowed, because the wiki goes out 1:1.

Publishing to the `gh-pages` branch (only changed files, `publish.json` with the source commit) is done by the School Notes tool, not by this package. `release-bundle.py` belongs to the v1 release flow and is not used by v2.
