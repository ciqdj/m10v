import { createHash } from 'node:crypto';
import { lstat, readFile } from 'node:fs/promises';
import path from 'node:path';

const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');
export async function verifyGr4Provenance(root) {
  const manifest = JSON.parse(await readFile(path.join(root, 'PROVENANCE.json'), 'utf8'));
  if (manifest.schema_version !== 1 || manifest.license !== 'GPL-2.0-only' ||
      !/^[0-9a-f]{40}$/.test(manifest.source_commit)) throw new Error('invalid GR IV provenance');
  for (const [relative, expected] of Object.entries(manifest.included_files)) {
    const target = path.resolve(root, relative);
    if (!target.startsWith(`${path.resolve(root)}${path.sep}`)) throw new Error('unsafe provenance path');
    const info = await lstat(target);
    if (!info.isFile() || info.isSymbolicLink()) throw new Error(`unsafe vendored file: ${relative}`);
    if (digest(await readFile(target)) !== expected) throw new Error(`vendored file differs: ${relative}`);
  }
  for (const relative of manifest.excluded_roots) {
    try { await lstat(path.join(root, relative)); throw new Error(`excluded path present: ${relative}`); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return manifest;
}
