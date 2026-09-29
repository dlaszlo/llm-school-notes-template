import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { renderMarkdown, printSection } from '../lib/markdown.mjs';
import { exportSite } from '../lib/export.mjs';
import { sha256, readInside } from '../lib/paths.mjs';
import { safeSvg } from '../lib/assets.mjs';
const fixture = fileURLToPath(new URL('./fixtures/', import.meta.url));
const resolveUrl = async s => s;
async function settings() {
  return {
    title: 'Minta', mode: 'private-preview', base: '/pelda/',
    pages: await Promise.all(['wiki/index.md', 'wiki/tema.md'].map(async p => ({ path: p, sha256: sha256(await fs.readFile(path.join(fixture, p))) }))),
    assets: [{ path: 'wiki/assets/diagram.svg', sha256: sha256(await fs.readFile(path.join(fixture, 'wiki/assets/diagram.svg'))) }],
    collections: [{ id: 'minta', title: 'Minta', pages: ['wiki/index.md', 'wiki/tema.md'] }]
  };
}
test('Markdown source remains untouched; metadata/comments do not reach the payload', async () => {
  const config = await settings();
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'study-export-'));
  try {
    const { payload, receipt } = await exportSite({ repo: fixture, config, output: path.join(tmp, 'build') });
    const serialized = JSON.stringify(payload);
    assert.ok(!serialized.includes('CANARY'));
    assert.ok(!serialized.includes('private_path'));
    assert.ok(!serialized.includes('/private/'));
    assert.match(payload.pages[0].html, /href="\/pelda\/tema\/#azonos-c%C3%ADm"/);
    assert.match(payload.pages[1].html, /href="\/pelda\/"/);
    assert.equal(payload.pages[0].headings.filter(h => h.text === 'Azonos cím').length, 2);
    assert.ok(payload.pages[0].headings.some(h => h.slug === 'azonos-cím-1'));
    assert.match(payload.pages[0].html, /H<sub>2<\/sub>O/);
    assert.match(payload.pages[0].html, /<small class="study-label">💡 Példa🤖 magyarázata<\/small>/);
    assert.doesNotMatch(payload.pages[0].html, /\[!TIP\]|<h1/);
    assert.match(payload.pages[0].html, /<mjx-container/);
    assert.equal(receipt.pages[0].audit.formulas.length, 2);
    const svg = await fs.readFile(path.join(tmp, 'build/public', receipt.assets[0].output), 'utf8');
    assert.ok(!svg.includes('CANARY'));
    assert.match(svg, /Balról jobbra/);
    assert.match(svg, /M 10 30 L 110 30/);
    for (const p of config.pages) assert.equal(sha256(await fs.readFile(path.join(fixture, p.path))), p.sha256);
  } finally { await fs.rm(tmp, { recursive: true, force: true }); }
});
test('source hashes, asset allowlists and unsupported publication fail closed', async () => {
  const config = await settings();
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'study-boundary-'));
  try {
    await assert.rejects(exportSite({ repo: fixture, config: { ...config, mode: 'public', publicationApproved: true }, output: path.join(tmp, 'public') }), /not enabled/);
    await assert.rejects(exportSite({ repo: fixture, config: { ...config, assets: [] }, output: path.join(tmp, 'missing') }), /Unapproved image/);
    await assert.rejects(exportSite({ repo: fixture, config: { ...config, pages: [{ ...config.pages[0], sha256: '0'.repeat(64) }] }, output: path.join(tmp, 'changed') }), /Changed input/);
    await assert.rejects(exportSite({ repo: fixture, config, output: fixture }), /outside/);
    await assert.rejects(readInside(fixture, '../outside'), /Unsafe/);
    await fs.symlink('/etc/hosts', path.join(tmp, 'escape'));
    await assert.rejects(readInside(tmp, 'escape'), /escapes/);
  } finally { await fs.rm(tmp, { recursive: true, force: true }); }
});
test('active HTML and SVG never survive; real subscript and details do', async () => {
  const r = await renderMarkdown('# Test\n\n<script>alert(1)</script><iframe src="https://example.com"></iframe><img src="image.svg" onerror="alert(1)"><sub>2</sub>', { resolveUrl });
  assert.doesNotMatch(r.html, /script|iframe|onerror|alert/);
  assert.match(r.html, /<sub>2<\/sub>/);
  assert.throws(() => safeSvg(Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"><script>oops</script></svg>')), /active/);
  assert.throws(() => safeSvg(Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"><use href="https://example.com/x"/></svg>')), /reference/);
});
test('Mermaid graph line breaks and relationship source are preserved', async () => {
  const graph = 'flowchart TD\n A --> B\n B --> C\n';
  let observed;
  await renderMarkdown('```mermaid\n' + graph + '```', { resolveUrl, mermaid: async code => { observed = code; return '/diagram.svg'; } });
  assert.equal(observed, graph);
});
test('an invalid or HTML-producing formula cannot become a silently wrong page', async () => {
  await assert.rejects(renderMarkdown('$\\thisMacroDoesNotExist{a}$', { resolveUrl }), /Math rendering failed/);
  await assert.rejects(renderMarkdown('$\\href{javascript:alert(1)}{x}$', { resolveUrl }), /Math rendering failed/);
});
test('print moves complete answers and prefixes footnote IDs without losing references', async () => {
  const source = await fs.readFile(path.join(fixture, 'wiki/index.md'), 'utf8');
  const r = await renderMarkdown(source, { resolveUrl });
  const print = await printSection(r.html, 'chapter-');
  assert.doesNotMatch(print.html, /<details|2F/);
  assert.match(print.answers, /2F/);
  const combined = print.html + print.answers;
  const ids = [...combined.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]);
  for (const [, href] of combined.matchAll(/href="#([^" ]+)"/g)) assert.ok(ids.includes(href), `Missing print anchor ${href}`);
});
