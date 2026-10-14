// Cache the exact public browser-runtime revision used for compatibility tests.
// Third-party source files stay local and are never committed with m10v.
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, rename, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';

const base = 'https://grlife.app/firmware-store/runtime/';
const args=process.argv.slice(2);
if(args.some(arg=>!['--current','--legacy'].includes(arg))||new Set(args).size!==args.length||
  (args.includes('--current')&&args.includes('--legacy')))
  throw new Error('usage: node scripts/sync-grlife-runtime.mjs [--current|--legacy]');
const current = !args.includes('--legacy');
const manifestSha = current
  ? '1dff66f9e243329ed4ab95b9b7bb4bef74846848f62ae29172d8f3c74574688b'
  : 'c42f0caf8163bb4db95bc864befc4d5f9fcaf41ade444bf027863d3574c2938d';
const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const destination = path.join(root, '.runtime', current ? 'grlife-current' : 'grlife');
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const execFileAsync = promisify(execFile);

async function download(url) {
  let lastError;
  for (let attempt=0;attempt<3;attempt++) try {
    const { stdout } = await execFileAsync('curl',
      ['-fsSL', '--proto', '=https', '--max-redirs', '0', url],
      { encoding: 'buffer', maxBuffer: 16 * 1024 * 1024, timeout: 60000 });
    return stdout;
  } catch(error) { lastError=error; }
  throw lastError;
}

const manifestBytes = await download(`${base}generation-manifest.json`);
if (sha(manifestBytes) !== manifestSha) throw new Error('GRLife runtime manifest has changed; review before syncing');
const manifest = JSON.parse(manifestBytes);
if (manifest.schema !== 'grlife-firmware-store-browser-runtime/v1') throw new Error('runtime schema mismatch');
const integrity = { manifestSha256: manifestSha, files: {} };
const temporary = await mkdtemp(path.join(os.tmpdir(), 'm10v-grlife-runtime-'));
try {
  const sourceFiles=Object.entries({ ...manifest.sources, ...manifest.assets });
  let nextFile=0;
  await Promise.all(Array.from({length:Math.min(4,sourceFiles.length)},async()=>{
   while(nextFile<sourceFiles.length){
    const [name,metadata]=sourceFiles[nextFile++];
    if (!/^[a-zA-Z0-9_.\/-]+$/.test(name) || name.startsWith('/') || name.split('/').includes('..'))
      throw new Error(`unsafe runtime path: ${name}`);
    const bytes = await download(`${base}core/${name}`);
    if (bytes.length !== metadata.bytes || sha(bytes) !== metadata.sha256)
      throw new Error(`runtime integrity mismatch: ${name}`);
    const target = path.join(temporary, name);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, bytes, { mode: 0o600 });
    integrity.files[name] = metadata.sha256;
   }
  }));
  const webModules = {
    'firmware-store/film-fit.js': '1ae59035c26ecf880473f459a9e90673d1c97e5509ac1f06e53456e9a819a53a',
    'firmware-store/film-camera-model.js': '916d376fec8bc0ae6ecf2735c743bceece85b91d968f5bee50012c59f92be2e4',
    'recipes/custom-recipe-core.js': 'b7190201b15744722e107c2e68afc37968269c4823758350ba6421419ba646a9',
  };
  for (const [name, expected] of Object.entries(webModules)) {
    const bytes = await download(`https://grlife.app/${name}`);
    if (sha(bytes) !== expected) throw new Error(`GRLife web module changed: ${name}`);
    const target = path.join(temporary, 'web', name);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, bytes, { mode: 0o600 });
    integrity.files[`web/${name}`] = expected;
  }
  await writeFile(path.join(temporary, 'm10v-integrity.json'), JSON.stringify(integrity), { mode: 0o600 });
  await mkdir(path.dirname(destination), { recursive: true });
  await rm(destination, { recursive: true, force: true });
  await rename(temporary, destination);
  console.log(`GRLife compatibility runtime cached locally: ${destination}`);
} catch (error) {
  await rm(temporary, { recursive: true, force: true });
  throw error;
}
