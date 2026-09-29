#!/usr/bin/env node
// Restore original DATA from an explicit immutable Git archive revision.
// No credentials are copied and no runtime, program or skill is deployed.
import fs from 'node:fs/promises';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { relativeFile, sha256 } from './lib/paths.mjs';
const [repoArg, archiveArg] = process.argv.slice(2);
if (!repoArg || !archiveArg) throw new Error('hydrate-archive.mjs ACTIVE_REPO ARCHIVE_CHECKOUT');
const repo = await fs.realpath(repoArg);
const archive = await fs.realpath(archiveArg);
const manifest = JSON.parse(await fs.readFile(path.join(repo, 'ingest-manifests/archive-sources.json'), 'utf8'));
if (!/^[a-f0-9]{40}$/.test(manifest.archive_commit)) throw new Error('Invalid archive commit');
let restored = 0;
for (const entry of manifest.files) {
  const file = relativeFile(entry.path);
  if (!/^(sources|references)\//.test(file)) throw new Error('Only original source/reference data may be restored');
  const dest = path.join(repo, file);
  await fs.mkdir(path.dirname(dest), { recursive: true });
  const parent = await fs.realpath(path.dirname(dest));
  if (!parent.startsWith(repo + path.sep)) throw new Error('Symlink escapes target');
  try {
    const current = await fs.readFile(dest);
    if (sha256(current) !== entry.sha256) throw new Error(`Existing different file left untouched: ${file}`);
    continue;
  } catch (e) { if (e.code !== 'ENOENT') throw e; }
  const bytes = execFileSync('git', ['show', `${manifest.archive_commit}:${file}`], { cwd: archive, maxBuffer: 100 * 1024 * 1024 });
  if (sha256(bytes) !== entry.sha256) throw new Error(`Archive hash mismatch: ${file}`);
  await fs.writeFile(dest, bytes, { flag: 'wx', mode: 0o600 }); restored++;
}
console.log(`Verified ${manifest.files.length} original files; restored ${restored}.`);
