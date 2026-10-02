import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkRehype from 'remark-rehype';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import rehypeStringify from 'rehype-stringify';
import rehypeMathjax from 'rehype-mathjax/svg';
import { visit } from 'unist-util-visit';
import { toText } from 'hast-util-to-text';
import GithubSlugger from 'github-slugger';
import { parse as parseYaml } from 'yaml';

export function splitMarkdown(source) {
  const match = source.match(/^\uFEFF?---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);
  const metadata = match ? parseYaml(match[1], { maxAliasCount: 0 }) : {};
  const body = match ? source.slice(match[0].length) : source;
  const ast = unified().use(remarkParse).parse(body);
  const firstHeading = ast.children.find(n => n.type === 'heading');
  const headingText = firstHeading?.children?.map(n => n.value || '').join('');
  return { metadata: metadata || {}, body, title: String(metadata?.title || headingText || 'Jegyzet') };
}

const schema = structuredClone(defaultSchema);
schema.tagNames.push('sub', 'sup', 'dl', 'dd', 'dt');
schema.attributes.code = [...(schema.attributes.code || []), ['className', /^language-/, 'math-inline', 'math-display']];
schema.attributes.div = [...(schema.attributes.div || []), ['className', 'math', 'math-display']];
schema.attributes.span = [...(schema.attributes.span || []), ['className', 'math', 'math-inline']];
schema.attributes.details = ['open'];
// The input never supplies executable HTML, CSS, embeds or arbitrary IDs/classes.
// Footnote IDs are prefixed by rehype-sanitize, including their references.

const el = (tagName, properties = {}, children = []) => ({ type: 'element', tagName, properties, children });
const isElement = (n, tag) => n.type === 'element' && (!tag || n.tagName === tag);

export async function renderMarkdown(source, { resolveUrl, mermaid, pageId = '', footnoteLabel = 'Források' } = {}) {
  const { metadata, body, title } = splitMarkdown(source);
  const headings = [];
  const sanitizedIds = new Map();
  const audit = { title, formulas: [], mermaid: [], labels: [], links: [], images: [] };
  const processor = unified().use(remarkParse).use(remarkGfm).use(remarkMath)
    .use(remarkRehype, { allowDangerousHtml: true, footnoteLabel })
    .use(rehypeRaw)
    .use(() => tree => {
      // Markdown inside an HTML summary is raw text; recover its inline formulas.
      visit(tree, 'element', node => {
        if (node.tagName !== 'summary') return;
        visit(node, 'text', (text,index,parent) => {
          const matches=[...text.value.matchAll(/(?<!\\)\$([^$\n]+)\$/g)];
          if(!matches.length) return;
          const children=[];let offset=0;
          for(const match of matches){
            children.push({type:'text',value:text.value.slice(offset,match.index)});
            children.push(el('code',{className:['language-math','math-inline']},[{type:'text',value:match[1]}]));
            offset=match.index+match[0].length;
          }
          children.push({type:'text',value:text.value.slice(offset)});
          parent.children.splice(index,1,...children);
          return index+children.length;
        });
      });
    })
    .use(() => tree => {
      visit(tree, 'element', node => {
        if (node.properties.id) sanitizedIds.set(node.properties.id, 'user-content-' + node.properties.id);
      });
    })
    .use(rehypeSanitize, schema)
    .use(() => async tree => {
      const slugger = new GithubSlugger();
      let seenBody = false;
      // Remove only a leading heading repeating the page title. Keep its fragment.
      for (let i = 0; i < tree.children.length; i++) {
        const n = tree.children[i];
        if (!isElement(n)) continue;
        // A leading banner does not make the following repeated page title body content.
        if (!seenBody && isElement(n, 'p') && n.children.some(c => isElement(c, 'img')) && !toText(n).trim()) continue;
        if (/^h[1-6]$/.test(n.tagName) && !seenBody && toText(n) === title) {
          tree.children[i] = el('span', { id: slugger.slug(toText(n)), className: ['heading-alias'] });
        } else { seenBody = true; }
      }
      const jobs = [];
      let imageCount = 0;
      visit(tree, 'element', (node, index, parent) => {
        const text = toText(node);
        for (const prop of ['ariaDescribedBy', 'ariaLabelledBy']) {
          if (Array.isArray(node.properties[prop])) node.properties[prop] = node.properties[prop].map(id => sanitizedIds.get(id) || id);
        }
        if (/^h[1-6]$/.test(node.tagName) && node.properties.id !== 'user-content-footnote-label') {
          const depth = Math.min(6, Number(node.tagName[1]) + 1);
          node.tagName = `h${depth}`;
          node.properties.id = slugger.slug(text);
          headings.push({ depth, slug: node.properties.id, text });
        }
        if (node.tagName === 'blockquote') {
          const p = node.children.find(n => isElement(n, 'p'));
          const first = p?.children[0];
          const match = first?.type === 'text' && first.value.match(/^\[!(TIP|NOTE|WARNING|IMPORTANT|CAUTION)\](?:\s|$)/);
          if (match) {
            first.value = first.value.slice(match[0].length);
            if (!toText(p).trim()) node.children.splice(node.children.indexOf(p), 1);
            node.tagName = 'aside';
            node.properties = { className: ['study-callout', `study-${match[1].toLowerCase()}`], 'aria-label': ({ TIP: 'Magyarázat', NOTE: 'Megjegyzés', WARNING: 'Figyelmeztetés', IMPORTANT: 'Fontos', CAUTION: 'Figyelem' })[match[1]] };
          }
        }
        if (node.tagName === 'sub' && /^(?:💡|➕|⚠️|📗|🗓️|🔖|🤖)/u.test(text.trim())) {
          node.tagName = 'small'; node.properties.className = ['study-label']; audit.labels.push(text);
        }
        if (node.tagName === 'p' && node.children.every(n => (n.type === 'text' && !n.value.trim()) || isElement(n, 'br'))) {
          node.properties.className = ['study-spacer'];
        }
        if (node.tagName === 'details') node.properties['data-pagefind-ignore'] = '';
        if (node.tagName === 'a' && node.properties.href) {
          jobs.push((async () => {
            let href = String(node.properties.href);
            if (href.startsWith('#') && sanitizedIds.has(href.slice(1))) href = '#' + sanitizedIds.get(href.slice(1));
            const resolved = await resolveUrl(href, false);
            if (resolved.citationOnly) { node.tagName='span'; node.properties={}; node.children.push({type:'text',value:' (nem nyilvános forrás)'}); return; }
            node.properties.href = typeof resolved === 'string' ? resolved : resolved.url;
            if (resolved.private) { node.children.push({ type: 'text', value: ' (privát forrás)' }); }
            audit.links.push(node.properties.href);
          })());
        }
        if (node.tagName === 'img') {
          // Decided in document order, before any await: the output must not depend on which
          // asset resolves first, or unchanged pages would differ between builds.
          const order = imageCount++;
          node.properties.loading = order ? 'lazy' : 'eager';
          jobs.push((async () => {
            node.properties.src = await resolveUrl(String(node.properties.src), true);
            node.properties.decoding = 'async';
            audit.images[order] = node.properties.src;
            node.properties.className = [node.properties.src.includes('/banner-') ? 'study-banner' : 'study-figure'];
          })());
        }
        if (node.tagName === 'pre') {
          const code = node.children.find(n => isElement(n, 'code') && n.properties.className?.includes('language-mermaid'));
          if (code) jobs.push((async () => {
            const graph = code.children.map(n => n.value || '').join(''); audit.mermaid.push(graph);
            const image = await mermaid(graph);
            parent.children[index] = el('p', {}, [el('img', { src: image, alt: graph.match(/accTitle:\s*(.+)/)?.[1] || 'Kapcsolati ábra', className: ['study-figure'], loading: 'lazy' })]);
          })());
        }
      });
      await Promise.all(jobs);
    })
    .use(() => tree => {
      audit.formulas=[];
      visit(tree, 'element', node => {
        if(node.tagName==='code' && node.properties.className?.some(c=>c==='language-math'||c==='math-inline'||c==='math-display')) audit.formulas.push(toText(node));
      });
    })
    .use(rehypeMathjax, { svg: { fontCache: 'none' }, tex: { packages: ['base', 'ams', 'newcommand', 'configmacros', 'boldsymbol', 'textmacros'] } })
    .use(() => tree => {
      let formulaIndex = 0;
      visit(tree, 'element', node => {
        if (node.tagName === 'mjx-container') {
          node.properties.role = 'math';
          node.properties['aria-label'] = audit.formulas[formulaIndex++];
        }
        if (node.properties?.['data-mjx-error']) throw new Error(`Math rendering failed: ${node.properties['data-mjx-error']}`);
        if (node.properties?.dataMmlNode === 'merror' || node.properties?.['data-mml-node'] === 'merror') throw new Error('Math rendering failed');
        if (node.properties?.className?.includes('mjx-merror')) throw new Error('Math rendering failed');
      });
    })
    .use(rehypeStringify);
  const result = await processor.process(body);
  return { title, html: String(result), headings, audit, metadata };
}

export async function printSection(html, prefix) {
  // Prefix all IDs/references before combining independently rendered pages.
  const answers = [];
  const processor = unified().use(rehypeRaw).use(() => tree => {
    visit(tree, 'element', (node, index, parent) => {
      if (node.properties.id) node.properties.id = prefix + node.properties.id;
      if (String(node.properties.href || '').startsWith('#')) node.properties.href = '#' + prefix + node.properties.href.slice(1);
      for (const prop of ['ariaDescribedBy', 'ariaLabelledBy']) if (node.properties[prop]) node.properties[prop] = node.properties[prop].map(id => prefix + id);
    });
    visit(tree, 'element', (node, index, parent) => {
      if (node.tagName === 'img') node.properties.loading = 'eager';
      if (node.tagName === 'p') {
        let hasImage = false; visit(node, 'element', child => { if (child.tagName === 'img') hasImage = true; });
        if (hasImage) node.properties.className = ['print-figure'];
      }
      if (node.tagName === 'details') {
        const summary = node.children.find(n => isElement(n, 'summary'));
        const question = structuredClone(summary?.children || [{type:'text',value:'Válasz'}]);
        visit({type:'root',children:question}, 'element', n => { delete n.properties.id; });
        answers.push({ question, children: node.children.filter(n => n !== summary) });
        // Preserve the question at its original place; solutions move to the end.
        node.tagName = 'p'; node.properties = { className: ['print-question'] }; node.children = summary?.children || [];
      }
    });
    // Keep a diagram and its immediate small/italic caption on the same sheet.
    const caption = n => isElement(n, 'p') && toText(n).length < 350 && n.children.some(c => isElement(c, 'em') || isElement(c, 'small')) && n.children.every(c => c.type === 'text' ? !c.value.trim() : ['em','small','sup','br'].includes(c.tagName));
    visit(tree, node => {
      if (!node.children || isElement(node,'figure')) return;
      for (let i=0;i<node.children.length;i++) {
        const child=node.children[i];
        if (!isElement(child,'p') || !child.properties.className?.includes('print-figure')) continue;
        let start=i,end=i+1;
        let j=i-1; while(j>=0 && node.children[j].type==='text' && !node.children[j].value.trim()) j--;
        if(j>=0 && caption(node.children[j])) start=j;
        j=i+1; while(j<node.children.length && node.children[j].type==='text' && !node.children[j].value.trim()) j++;
        if(j<node.children.length && caption(node.children[j])) end=j+1;
        child.properties.className=[];
        node.children.splice(start,end-start,el('figure',{className:['print-figure']},node.children.slice(start,end)));
        i=start;
      }
    });
  }).use(rehypeStringify);
  const result = await processor.run({ type: 'root', children: [{ type: 'raw', value: html }] });
  const answerTree = { type: 'root', children: answers.flatMap(a => [el('h3', {}, a.question), ...a.children]) };
  return { html: processor.stringify(result), answers: processor.stringify(answerTree) };
}
