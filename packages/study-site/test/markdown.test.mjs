import test from 'node:test';
import assert from 'node:assert/strict';

test('an empty jump-target anchor keeps its plain id for links from other pages', async () => {
  const { renderMarkdown } = await import('../lib/markdown.mjs');
  const out = await renderMarkdown('# T\n\nSzöveg.\n\n<a id="pdf-13-oldal"></a>\n\n## 13. oldal\n\n[ugrás](#pdf-13-oldal)\n', { resolveUrl: async h => h });
  const html = out.html ?? String(out);
  assert.ok(html.includes('id="pdf-13-oldal"'), html);
  assert.ok(html.includes('href="#pdf-13-oldal"'), html);
});
