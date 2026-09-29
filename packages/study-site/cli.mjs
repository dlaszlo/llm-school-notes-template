#!/usr/bin/env node
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { exportSite } from './lib/export.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const [command, ...args] = process.argv.slice(2);
const options = {};
for (let i = 0; i < args.length; i += 2) {
  if (!args[i].startsWith('--') || !args[i + 1]) throw new Error('Expected --option value pairs');
  options[args[i].slice(2)] = args[i + 1];
}
if (command === 'build') {
  if (!options.repo || !options.config || !options.output) throw new Error('build --repo PATH --config FILE --output NEW_DIRECTORY [--browser CHROMIUM]');
  const output = path.resolve(options.output);
  const config = JSON.parse(await fs.readFile(options.config, 'utf8'));
  const { payload } = await exportSite({ repo: options.repo, config, output, browserPath: options.browser || process.env.STUDY_BROWSER });
  const child = spawn(process.execPath, [path.join(root, 'node_modules/astro/bin/astro.mjs'), 'build'], {
    cwd: root, stdio: 'inherit',
    env: { ...process.env, ASTRO_TELEMETRY_DISABLED: '1', STUDY_PAYLOAD: path.join(output, 'payload.json'), STUDY_OUTPUT: path.join(output, 'site') }
  });
  const code = await new Promise(resolve => child.on('exit', resolve));
  if (code !== 0) throw new Error(`Astro build failed: ${code}`);
  console.log(`Built ${payload.pages.length} pages: ${path.join(output, 'site')}`);
} else if (command === 'serve') {
  const directory = await fs.realpath(options.directory);
  const base = options.base || '/';
  const port = Number(options.port || 4321);
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript', '.mjs': 'application/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.wasm': 'application/wasm' };
  createServer(async (req, res) => {
    try {
      const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
      if (!pathname.startsWith(base)) throw new Error('wrong base');
      let file = path.resolve(directory, './' + pathname.slice(base.length));
      if (!file.startsWith(directory + path.sep) && file !== directory) throw new Error('outside root');
      if ((await fs.stat(file)).isDirectory()) file = path.join(file, 'index.html');
      file = await fs.realpath(file);
      if (!file.startsWith(directory + path.sep)) throw new Error('outside root');
      res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store' });
      res.end(await fs.readFile(file));
    } catch { res.writeHead(404); res.end('Not found'); }
  }).listen(port, '127.0.0.1', () => console.log(`Local preview: http://127.0.0.1:${port}${base}`));
} else {
  console.log('study-site: build --repo PATH --config FILE --output NEW_DIRECTORY; serve --directory SITE [--port 4321] [--base /]');
  process.exitCode = command ? 1 : 0;
}
