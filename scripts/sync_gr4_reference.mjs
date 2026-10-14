import { createHash } from 'node:crypto';
import { cp, mkdir, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const sourceRoot = path.resolve(process.argv[2] || '../gr-custom-tool');
const vendorRoot = path.join(projectRoot, 'vendor', 'gr4');
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');

async function filesBelow(root, relative = '') {
  const rows = [];
  for (const entry of await readdir(path.join(root, relative), { withFileTypes: true })) {
    const next = path.join(relative, entry.name);
    if (entry.isDirectory()) rows.push(...await filesBelow(root, next));
    else rows.push(next);
  }
  return rows.sort();
}

const commit = spawnSync('git', ['-C', sourceRoot, 'rev-parse', 'HEAD'], { encoding: 'utf8' });
if (commit.status !== 0) throw new Error('GR IV reference is not a readable Git checkout');
for (const name of ['gr4_editor', 'tests', 'web', 'LICENSE', 'requirements.txt', 'PROVENANCE.json'])
  await rm(path.join(vendorRoot, name), { recursive: true, force: true });
await mkdir(path.join(vendorRoot, 'gr4_editor'), { recursive: true });
await mkdir(path.join(vendorRoot, 'tests'), { recursive: true });

const included = [];
for (const relative of await filesBelow(path.join(sourceRoot, 'gr4_editor'))) {
  if (relative === 'server.py' || relative.includes('__pycache__') || relative.endsWith('.pyc')) continue;
  const source = path.join(sourceRoot, 'gr4_editor', relative);
  const destination = path.join(vendorRoot, 'gr4_editor', relative);
  await mkdir(path.dirname(destination), { recursive: true });
  await cp(source, destination);
  included.push(path.join('gr4_editor', relative));
}
for (const relative of await filesBelow(path.join(sourceRoot, 'tests'))) {
  if (!relative.endsWith('.py') || relative === 'test_launcher.py') continue;
  const source = path.join(sourceRoot, 'tests', relative);
  const destination = path.join(vendorRoot, 'tests', relative);
  await mkdir(path.dirname(destination), { recursive: true });
  await cp(source, destination);
  included.push(path.join('tests', relative));
}
for (const relative of await filesBelow(path.join(sourceRoot, 'web'))) {
  const source = path.join(sourceRoot, 'web', relative);
  const destination = path.join(vendorRoot, 'web', relative);
  await mkdir(path.dirname(destination), { recursive: true });
  await cp(source, destination);
  included.push(path.join('web', relative));
}
for (const relative of ['LICENSE', 'requirements.txt']) {
  await cp(path.join(sourceRoot, relative), path.join(vendorRoot, relative));
  included.push(relative);
}

const hashes = {};
const sizes = {};
for (const relative of included.sort()) {
  const bytes = await readFile(path.join(vendorRoot, relative));
  hashes[relative] = digest(bytes);
  sizes[relative] = bytes.length;
}
const manifest = {
  schema_version: 1,
  source_repository: 'gr-custom-tool',
  source_commit: commit.stdout.trim(),
  license: 'GPL-2.0-only',
  included_files: hashes,
  included_sizes: sizes,
  excluded_roots: ['data', 'gr4_editor/server.py'],
};
await writeFile(path.join(vendorRoot, 'PROVENANCE.json'), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`Vendored ${included.length} GR IV reference files from ${manifest.source_commit}`);
