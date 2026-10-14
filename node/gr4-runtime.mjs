import { createHash } from 'node:crypto';
import { lstat, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { createGr4Client } from './adapters/gr4/client.mjs';

const ID = /^[a-z0-9_-]{1,90}$/i;
const SHA = /^[0-9a-f]{64}$/;
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');

export class Gr4Runtime {
  constructor(root, client = createGr4Client()) {
    this.root = path.resolve(root);
    this.client = client;
  }
  async ensure() { await mkdir(path.join(this.root, 'inputs'), { recursive: true }); }
  checkId(value) { if (!ID.test(value || '')) throw new Error('invalid GR IV identifier'); return value; }
  async import(bytes, filename = 'fwdc248b.bin') {
    if (!Buffer.isBuffer(bytes)) throw new Error('firmware input must be bytes');
    await this.ensure();
    const sha256 = hash(bytes);
    const inputPath = path.join(this.root, 'inputs', `${sha256}.bin`);
    try { await writeFile(inputPath, bytes, { flag: 'wx', mode: 0o400 }); }
    catch (error) {
      if (error.code !== 'EEXIST' || !(await readFile(inputPath)).equals(bytes)) throw error;
    }
    const project = await this.client.request('import', { input_path: inputPath,
      filename: path.basename(filename) }, this.root);
    return { ...project, evidence: 'reference_verified', hardware: 'not_tested' };
  }
  async call(operation, payload = {}) {
    await this.ensure();
    return this.client.request(operation, payload, this.root);
  }
  async stage(bytes, suffix = '.upload') {
    if (!Buffer.isBuffer(bytes)) throw new Error('upload must be bytes');
    await this.ensure();
    const target = path.join(this.root, 'inputs', `${hash(bytes)}${suffix}`);
    try { await writeFile(target, bytes, { flag: 'wx', mode: 0o400 }); }
    catch (error) { if (error.code !== 'EEXIST' || !(await readFile(target)).equals(bytes)) throw error; }
    return target;
  }
  async readWorkerArtifact(value) {
    const target = path.resolve(value?.path || '');
    const dataRoot = path.resolve(this.root, 'data');
    if (!target.startsWith(`${dataRoot}${path.sep}`)) throw new Error('unsafe GR IV artifact path');
    const info = await lstat(target);
    if (!info.isFile() || info.isSymbolicLink()) throw new Error('unsafe GR IV artifact');
    return { bytes: await readFile(target), filename: path.basename(value.filename || target) };
  }
  project(id) { return this.client.request('project', { project_id: this.checkId(id) }, this.root); }
  history(id) { return this.client.request('history', { project_id: this.checkId(id) }, this.root); }
  save(id, value) { return this.client.request('save', { ...value, project_id: this.checkId(id) }, this.root); }
  preview(id, value) { return this.client.request('crop_preview', {
    project_id: this.checkId(id), ratio: value.ratio }, this.root); }
  build(id, value) { return this.client.request('build', {
    project_id: this.checkId(id), version: value.version,
    allow_older: value.allow_older }, this.root); }
  rollback(id, value) { return this.client.request('rollback', {
    project_id: this.checkId(id), sha256: value.sha256, version: value.version,
    allow_older: value.allow_older }, this.root); }
  async importShutdown(id, bytes, metadata) {
    await this.ensure();
    const imagePath = path.join(this.root, 'inputs', `${hash(bytes)}.image`);
    try { await writeFile(imagePath, bytes, { flag: 'wx', mode: 0o400 }); }
    catch (error) { if (error.code !== 'EEXIST') throw error; }
    return this.client.request('shutdown_import', { project_id: this.checkId(id), image_path: imagePath,
      filename: metadata.filename, target_id: metadata.target_id, fit: metadata.fit,
      item_id: metadata.item_id, item_name: metadata.item_name }, this.root);
  }
  async artifact(kind, id) {
    this.checkId(id);
    if (!['firmware', 'manifest'].includes(kind)) throw new Error('invalid artifact kind');
    const ledgerPath = path.join(this.root, 'data', 'build-ledger.json');
    const ledger = JSON.parse(await readFile(ledgerPath, 'utf8'));
    const row = ledger.find((item) => item.id === id);
    if (!row) throw new Error('build not found');
    const target = path.resolve(kind === 'firmware' ? row.firmware_path : row.manifest_path);
    const builds = path.resolve(this.root, 'data', 'builds');
    if (!target.startsWith(`${builds}${path.sep}`)) throw new Error('unsafe artifact path');
    const info = await lstat(target);
    if (!info.isFile() || info.isSymbolicLink()) throw new Error('unsafe artifact');
    return readFile(target);
  }
  async original(sha256) {
    if (!SHA.test(sha256 || '')) throw new Error('invalid GR IV input hash');
    const target = path.join(this.root, 'inputs', `${sha256}.bin`);
    const bytes = await readFile(target);
    if (hash(bytes) !== sha256) throw new Error('GR IV input hash differs');
    return bytes;
  }
}
