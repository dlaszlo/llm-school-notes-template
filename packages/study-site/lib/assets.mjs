import { DOMParser, XMLSerializer } from '@xmldom/xmldom';
import { chromium } from 'playwright';
import { createRequire } from 'node:module';
import path from 'node:path';

export function safeSvg(bytes) {
  // Matplotlib/Graphviz emit this standard declaration. Remove it before parsing,
  // without loading a DTD; all other declarations and every entity remain rejected.
  const text = bytes.toString().replace(/<!DOCTYPE svg PUBLIC "-\/\/W3C\/\/DTD SVG 1\.1\/\/EN"\s+"http:\/\/www\.w3\.org\/Graphics\/SVG\/1\.1\/DTD\/svg11\.dtd">/g, '');
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error('SVG declarations/entities are not supported');
  const doc = new DOMParser({ onError: (level, message) => { throw new Error(`Invalid SVG: ${message}`); } }).parseFromString(text, 'image/svg+xml');
  if (doc.documentElement.localName !== 'svg') throw new Error('Not SVG');
  function clean(parent) {
    for (const child of [...Array.from(parent.childNodes || [])]) {
      if (child.nodeType === 8 || child.nodeType === 7 || child.localName === 'metadata') {
        parent.removeChild(child); continue;
      }
      if (child.nodeType === 1) {
        if (['script', 'foreignObject', 'iframe', 'image', 'animate', 'set', 'a'].includes(child.localName)) throw new Error(`Unsupported active SVG element: ${child.localName}`);
        for (const attr of Array.from(child.attributes || [])) {
          if (/^on/i.test(attr.name) || (/href$/i.test(attr.name) && !attr.value.startsWith('#'))) throw new Error('Active SVG reference');
          if (/url\(\s*['"]?(?!#)/i.test(attr.value) || /@import/i.test(attr.value)) throw new Error('External SVG style');
        }
        if (child.localName === 'style' && /@import|url\(\s*['"]?(?!#)/i.test(child.textContent)) throw new Error('External SVG CSS');
        clean(child);
      }
    }
  }
  clean(doc);
  return Buffer.from(new XMLSerializer().serializeToString(doc));
}

export async function mermaidRenderer(executablePath) {
  let browser, page;
  let queue = Promise.resolve();
  async function render(code, id) {
      if (!page) {
        browser = await chromium.launch({ executablePath, headless: true });
        page = await browser.newPage();
        await page.route('**/*', route => route.abort());
        await page.setContent('<!doctype html><html><body></body></html>');
        const require = createRequire(import.meta.url);
        const entry = require.resolve('mermaid');
        await page.addScriptTag({ path: path.join(path.dirname(entry), 'mermaid.min.js') });
      }
      const svg = await page.evaluate(async ({ code, id }) => {
        window.mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral', htmlLabels: false, deterministicIds: true, deterministicIDSeed: id, flowchart: { htmlLabels: false }, themeVariables: { fontFamily: 'Arial, sans-serif' } });
        return (await window.mermaid.render(id, code)).svg;
      }, { code, id });
      return safeSvg(Buffer.from(svg));
  }
  return {
    render(code, id) {
      const result = queue.then(() => render(code, id));
      queue = result.catch(() => {});
      return result;
    },
    async close() { await queue; await browser?.close(); }
  };
}
