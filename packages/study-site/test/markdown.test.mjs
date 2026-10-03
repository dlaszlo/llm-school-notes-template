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

test('public view: private photo lists, private footnotes and the grade prefix are left out', async () => {
  const { renderMarkdown } = await import('../lib/markdown.mjs');
  const resolveUrl = async h => /(^|\/)(sources|references)\//.test(h) ? { citationOnly: true } : h;
  const source = [
    '---', 'title: Matematika', '---', '# 📘 9. évfolyam: Halmazok', '', 'A [4. füzetfotón](../../sources/a/04.jpg) X áll.[^fuzet] Lásd még.[^web]', '',
    '# Fotók', '', '* [1. fotó](../../sources/a/01.jpg) - Venn-diagram', '* [2. fotó](../../sources/a/02.jpg) - szita', '',
    '<br />', '', '# Kérdések', '', 'Egy kérdés.', '',
    '[^fuzet]: Füzet, 4. fotó, [eredeti](../../sources/a/04.jpg).',
    '[^web]: OpenStax: [Sets](https://openstax.org/sets); [mentett másolat](../../references/b/README.md).', '',
  ].join('\n');
  const out = await renderMarkdown(source, { resolveUrl, publicView: true });
  assert.match(out.html, /📘 Halmazok/);
  assert.doesNotMatch(out.html, /évfolyam|Fotók|1\. fotó|Venn|Füzet, 4\. fotó|nem nyilvános|sources\/|references\//);
  assert.match(out.html, /A 4\. füzetfotón X áll\. Lásd még\./);
  assert.match(out.html, /href="https:\/\/openstax\.org\/sets"/);
  assert.match(out.html, /mentett másolat/);
  assert.equal((out.html.match(/data-footnote-ref/g) || []).length, 1);
  assert.deepEqual(out.headings.map(h => h.text), ['📘 Halmazok', 'Kérdések']);
  assert.equal(out.title, 'Matematika');
  assert.equal((await renderMarkdown('---\ntitle: "📘 9. évfolyam: Halmazok"\n---\nSzöveg.\n', { resolveUrl, publicView: true })).title, '📘 Halmazok');
  assert.equal((await renderMarkdown(source, { resolveUrl, publicView: true })).html, out.html);
  // The private preview keeps everything.
  const preview = await renderMarkdown(source, { resolveUrl: async h => h });
  assert.match(preview.html, /9\. évfolyam: Halmazok/);
  assert.match(preview.html, /1\. fotó/);
  assert.equal((preview.html.match(/data-footnote-ref/g) || []).length, 2);
});
