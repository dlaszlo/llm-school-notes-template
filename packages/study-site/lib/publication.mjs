import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import { splitMarkdown } from './markdown.mjs';

// Review decisions are exact, hash-bound configuration, never inferred by the build.
export function publicSource(source, page) {
  const { metadata } = splitMarkdown(source);
  const index = /^wiki\/(?:[^/]+\/)?index\.md$/.test(page.path);
  if (!['topic', 'chapter-summary'].includes(metadata.type) && !index && page.navigation !== 'info') {
    throw new Error(`Private or unrecognized page type: ${page.path}`);
  }
  if (['source', 'source-summary', 'lesson-notes'].includes(metadata.type)) throw new Error('Source notes are private');
  let result = source;
  for (const edit of page.publicEdits || []) {
    if (!edit.reason || typeof edit.before !== 'string' || !edit.before || typeof edit.after !== 'string') throw new Error('Invalid reviewed public edit');
    if (result.split(edit.before).length !== 2) throw new Error(`Public edit must match exactly once: ${page.path}`);
    result = result.replace(edit.before, () => edit.after);
  }
  const { body } = splitMarkdown(result);
  const nodes = unified().use(remarkParse).use(remarkGfm).parse(body).children;
  const cuts = [];
  for (const heading of page.omitSections || []) {
    const matching = nodes.filter(n => n.type === 'heading' && n.children.map(c => c.value || '').join('') === heading);
    if (matching.length !== 1) throw new Error(`Public section must match exactly once: ${heading}`);
    const node = matching[0]; const i = nodes.indexOf(node);
    const end = nodes.slice(i+1).find(n => n.type === 'heading' && n.depth <= node.depth);
    // Footnote definitions can follow the last section; preserve them as bibliography.
    const definitions = nodes.slice(i+1).filter(n => n.type === 'footnoteDefinition');
    const endOffset = end?.position.start.offset ?? body.length;
    cuts.push([node.position.start.offset, endOffset, definitions.filter(n=>n.position.start.offset<endOffset).map(n=>body.slice(n.position.start.offset,n.position.end.offset)).join('\n\n')]);
  }
  // Preserve YAML until renderMarkdown reads the title; it never reaches HTML.
  let filtered=body;
  for(const [start,end,replacement] of cuts.sort((a,b)=>b[0]-a[0])) filtered=filtered.slice(0,start)+replacement+filtered.slice(end);
  return result.slice(0,result.length-body.length)+filtered;
}
