import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const payloadFile = process.env.STUDY_PAYLOAD;
if (!payloadFile) throw new Error('Use node cli.mjs build; no private repository is mounted in the renderer');
const payload = JSON.parse(readFileSync(payloadFile, 'utf8'));
const root = fileURLToPath(new URL('.', import.meta.url));
export default defineConfig({
  root,
  base: payload.base,
  trailingSlash: 'always',
  publicDir: path.join(path.dirname(payloadFile), 'public'),
  outDir: process.env.STUDY_OUTPUT,
  cacheDir: path.join(path.dirname(payloadFile), '.astro'),
  integrations: [starlight({
    title: payload.title,
    ...(payload.branding ? { favicon: "/" + payload.branding.dark.slice(payload.base.length) } : {}),
    defaultLocale: 'root',
    locales: { root: { label: 'Magyar', lang: 'hu' } },
    customCss: ['./src/styles.css'],
    expressiveCode: false,
    disable404Route: true,
    components: { Head: './src/components/Head.astro', SiteTitle: './src/components/SiteTitle.astro', TwoColumnContent: './src/components/TwoColumnContent.astro' },
    sidebar: payload.pages.filter(p => p.navigation).map(p => ({ label: p.navigationLabel || (p.navigation === 'home' ? 'Kezdőlap' : p.title), link: '/' + (p.route ? p.route + '/' : '') })),
    tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
    social: [],
  })],
});
