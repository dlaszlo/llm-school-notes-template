import test from 'node:test';
import assert from 'node:assert/strict';

test('an empty jump-target anchor keeps its plain id for links from other pages', async () => {
  const { renderMarkdown } = await import('../lib/markdown.mjs');
  const out = await renderMarkdown('# T\n\nSzöveg.\n\n<a id="pdf-13-oldal"></a>\n\n## 13. oldal\n\n[ugrás](#pdf-13-oldal)\n', { resolveUrl: async h => h });
  const html = out.html ?? String(out);
  assert.ok(html.includes('id="pdf-13-oldal"'), html);
  assert.ok(html.includes('href="#pdf-13-oldal"'), html);
});

test('an mp4 image becomes a video with its PNG poster; print keeps only the poster', async () => {
  const { renderMarkdown, printSection } = await import('../lib/markdown.mjs');
  const resolveUrl = async h => h.replace('../assets/', 'assets/');
  const out = await renderMarkdown('# T\n\n![Az inga mozgása](../assets/inga/figure.mp4)\n', { resolveUrl });
  assert.match(out.html, /<span class="study-video"><video controls preload="metadata" playsinline poster="assets\/inga\/figure.png" src="assets\/inga\/figure.mp4" aria-label="Az inga mozgása" class="study-video-player">Az inga mozgása<\/video><img src="assets\/inga\/figure.png" alt="Az inga mozgása" loading="eager" decoding="async" class="study-figure study-video-poster"><\/span>/);
  assert.deepEqual(out.audit.images, ['assets/inga/figure.png']);
  assert.equal((await renderMarkdown('# T\n\n![Az inga mozgása](../assets/inga/figure.mp4)\n', { resolveUrl })).html, out.html);
  const printed = (await printSection(out.html, 'p1-')).html;
  assert.doesNotMatch(printed, /<video/);
  assert.match(printed, /<img src="assets\/inga\/figure.png"[^>]*study-video-poster/);
});
