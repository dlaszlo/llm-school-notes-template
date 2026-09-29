# Reusable local page checks

Use this repository-owned renderer for Markdown layout and structural checks. It renders local images, GitHub-style alerts, footnotes, details, MathJax and Mermaid at phone (390 px) and desktop (1100 px) widths. It is a local approximation, not proof of exact GitHub, Obsidian or PDF rendering. Actual subject-matter and visual review remain separate. This is a private local diagnostic, not a public exporter or privacy filter. The current HTML language is Hungarian (`hu`); rendering another language is supported visually, but language-specific accessibility validation must use an appropriate target renderer.

## One-time setup

Requires Node.js 20+ and an available Chromium browser. Install only on an authorized machine, from the Git checkout:

```sh
npm ci --prefix tools/page-check --ignore-scripts --no-audit --no-fund
```

Dependencies are locked in `tools/page-check/package-lock.json`. They live in the ignored repository-local `node_modules`; no global skill or agent program changes. The lock includes an explicit patched XML dependency override. `npm audit --prefix tools/page-check` checks current published advisories separately from rendering.

Prefer an already installed compatible browser using `--browser /absolute/path/to/chromium`. If none is available, agree the browser installation with the operator, then install the Playwright-pinned browser:

```sh
cd tools/page-check
npx --no-install playwright install chromium
```

Playwright stores browsers in its user cache by default; document that path/version in the deployment record. If OS libraries are missing, use the documented system package installation with the operator; do not download random binaries or hide installation inside a note task. The runner never installs dependencies or a browser.

## Ordinary operation

From the checkout, run either a subject or selected pages:

```sh
node tools/page_check.mjs --subject wiki/example
node tools/page_check.mjs --pages wiki/example/topic.md wiki/example/index.md
```

Optional `--repo PATH` checks another local checkout with this same versioned renderer. `--browser PATH` selects an existing compatible browser; `--force` discards cache reuse for this run. Output stays below `.visual-runs/page-check/`, ignored by Git.

The JSON report links full-page screenshots, legible phone tiles for long pages, open/closed disclosure views and individual page receipts. Errors include missing local links/images, invalid formulas or Mermaid, horizontal page overflow and detected diagram text clipping. Not every visual flaw can be detected: inspect the images. An intentionally unresolved knowledge link still needs a documented disposition under the wiki link rule; a failure report must not silently become a pass. Record a justified knowledge-link exception separately; missing images, malformed formulas and broken rename links are not such exceptions.

The browser serves only explicitly selected pages and their registered local images over loopback, and blocks external network requests. Raw page HTML is sanitized; source JavaScript is not executed. External images must first follow the source acquisition rules. This tool is not a sandbox for arbitrary programs or a renderer for hostile files supplied outside the authorized checkout.

Cache reuse requires unchanged page/local-link/asset bytes, renderer, dependency lock, browser version and view settings, plus intact output hashes. Local links are checked again. OS/font changes can alter layout; use `--force` after those changes and record the environment. The cache records rendered output, **not** a semantic review or human approval. External reference changes and changed learning scope must be considered by the agent even when a render is reusable.

## Verification

```sh
node --test tools/page-check/test.mjs
PAGE_CHECK_BROWSER=/absolute/path/to/chromium node --test tools/page-check/test.mjs
```

The first command checks parsing and local dependencies; the second also exercises a real browser, disclosure states, cache reuse/invalidation and deliberately broken Mermaid. A skipped browser test is not a successful browser proof. Preserve compact final receipts and actual review findings in the existing evidence record. Do not claim that snapshots alone complete a subject review.
