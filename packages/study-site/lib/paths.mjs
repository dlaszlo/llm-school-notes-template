import { readFile, realpath } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';

export const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
export function relativeFile(value) {
  if (typeof value !== 'string' || !value || value.includes('\\') || value.includes('\0') || path.posix.isAbsolute(value) || value.split('/').some(p => p === '..' || p === '.' || !p)) {
    throw new Error(`Unsafe relative path: ${value}`);
  }
  return value;
}
export async function readInside(root, name, expected) {
  relativeFile(name);
  const base = await realpath(root);
  const file = await realpath(path.join(base, name));
  if (!file.startsWith(base + path.sep)) throw new Error(`Path escapes input root: ${name}`);
  const data = await readFile(file);
  if (expected && sha256(data) !== expected) throw new Error(`Changed input; review and update its hash: ${name}`);
  return data;
}
export function routeFor(file) {
  relativeFile(file);
  if (!file.startsWith('wiki/') || !file.endsWith('.md')) throw new Error(`Not a wiki Markdown page: ${file}`);
  return file.slice(5, -3).replace(/(^|\/)index$/, '$1').replace(/\/$/, '');
}
export function urlFor(base, route) { return base + (route ? route + '/' : ''); }
export function normalizeBase(base = '/') {
  if (!/^\/(?:[a-zA-Z0-9_-]+\/)*$/.test(base)) throw new Error('base must be / or /path/');
  return base;
}
