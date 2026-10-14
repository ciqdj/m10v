import { createHash } from 'node:crypto';
import { chmod, lstat, mkdir, mkdtemp, open, readFile, rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { checkProjectId, checkSha256, newProjectId } from './ids.mjs';
import { validateProjectShape } from './project-schema.mjs';

const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const json = (value) => Buffer.from(`${JSON.stringify(value)}\n`);

async function infoOrNull(target) {
  try { return await lstat(target); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}
async function safeDirectory(target, label) {
  const info = await infoOrNull(target);
  if (info && (!info.isDirectory() || info.isSymbolicLink()))
    throw new Error(`unsafe ${label} directory`);
  return info;
}
async function syncDirectory(target) {
  const handle = await open(target, 'r');
  try { await handle.sync(); } finally { await handle.close(); }
}
async function writeSynced(target, bytes, mode = 0o600) {
  const handle = await open(target, 'wx', mode);
  try { await handle.writeFile(bytes); await handle.sync(); } finally { await handle.close(); }
}

export class PlatformStore {
  constructor(root, registry, options = {}) {
    this.root = path.resolve(root);
    this.registry = registry;
    this.options = options;
  }

  async ensureRoot() {
    await safeDirectory(this.root, 'data');
    await mkdir(this.root, { recursive: true });
    for (const name of ['objects', 'projects', 'builds']) {
      const target = path.join(this.root, name);
      await safeDirectory(target, name);
      await mkdir(target, { recursive: true });
    }
  }

  objectPath(sha) { return path.join(this.root, 'objects', `${checkSha256(sha)}.bin`); }
  projectPath(id) { return path.join(this.root, 'projects', checkProjectId(id)); }

  async importObject(bytes, filename = 'firmware.bin') {
    if (!Buffer.isBuffer(bytes)) throw new Error('firmware input must be bytes');
    const detected = this.registry.detect(bytes);
    const sha256 = hash(bytes);
    await this.ensureRoot();
    const destination = this.objectPath(sha256);
    const existing = await infoOrNull(destination);
    if (existing) {
      const current = await this.readObject(sha256);
      if (!current.equals(bytes)) throw new Error('existing object differs');
      return { sha256, adapter_id: detected.adapter.id, filename: path.basename(filename),
        ...detected.inspection };
    }
    const objects = path.join(this.root, 'objects');
    const stage = await mkdtemp(path.join(objects, '.m10v-object-'));
    const staged = path.join(stage, 'object.bin');
    try {
      await writeSynced(staged, bytes, 0o400);
      await syncDirectory(stage);
      if (this.options.beforeObjectPublish) await this.options.beforeObjectPublish(staged, destination);
      await rename(staged, destination);
      await chmod(destination, 0o400);
      await syncDirectory(objects);
    } finally { await rm(stage, { recursive: true, force: true }); }
    return { sha256, adapter_id: detected.adapter.id, filename: path.basename(filename),
      ...detected.inspection };
  }

  async readObject(sha) {
    const target = this.objectPath(sha);
    const info = await infoOrNull(target);
    if (!info) throw new Error('object not found');
    if (!info.isFile() || info.isSymbolicLink() || info.size > 128 * 1024 * 1024)
      throw new Error('unsafe object file');
    const bytes = await readFile(target);
    if (hash(bytes) !== sha) throw new Error('object hash differs');
    return bytes;
  }

  async createProject(objectSha, title) {
    const bytes = await this.readObject(objectSha);
    const { adapter } = this.registry.detect(bytes);
    if (typeof title !== 'string' || !title.trim() || title.trim().length > 120)
      throw new Error('invalid project title');
    await this.ensureRoot();
    const id = newProjectId();
    const now = new Date().toISOString();
    const record = { schema_version: 1, id, adapter_id: adapter.id, input_sha256: objectSha,
      title: title.trim(), revision: 0, created_at: now, updated_at: now,
      draft: adapter.createDraft(bytes) };
    validateProjectShape(record);
    const projects = path.join(this.root, 'projects');
    const stage = await mkdtemp(path.join(projects, '.m10v-project-'));
    try {
      await writeSynced(path.join(stage, 'project.json'), json(record));
      await syncDirectory(stage);
      await rename(stage, this.projectPath(id));
      await syncDirectory(projects);
    } finally { await rm(stage, { recursive: true, force: true }); }
    return record;
  }

  async validateProjectRecord(value) {
    validateProjectShape(value);
    const bytes = await this.readObject(value.input_sha256);
    const { adapter } = this.registry.detect(bytes);
    if (adapter.id !== value.adapter_id) throw new Error('project adapter differs from input');
    this.registry.get(value.adapter_id);
    return value;
  }

  async readProject(id) {
    const folder = this.projectPath(id);
    const dir = await infoOrNull(folder);
    if (!dir) throw new Error('project not found');
    if (!dir.isDirectory() || dir.isSymbolicLink()) throw new Error('unsafe project directory');
    const file = path.join(folder, 'project.json');
    const info = await infoOrNull(file);
    if (!info || !info.isFile() || info.isSymbolicLink() || info.size > 1024 * 1024)
      throw new Error('unsafe project record');
    return this.validateProjectRecord(JSON.parse(await readFile(file, 'utf8')));
  }

  async saveDraft(id, expectedRevision, draft) {
    const current = await this.readProject(id);
    if (current.revision !== expectedRevision) throw new Error('project revision conflict');
    const adapter = this.registry.get(current.adapter_id);
    const next = { ...current, revision: current.revision + 1,
      updated_at: new Date().toISOString(), draft: adapter.validateDraft(draft) };
    await this.validateProjectRecord(next);
    const folder = this.projectPath(id);
    const stage = path.join(folder, `.project-${process.pid}-${Date.now()}.json`);
    try {
      await writeSynced(stage, json(next));
      await rename(stage, path.join(folder, 'project.json'));
      await syncDirectory(folder);
    } finally { await rm(stage, { force: true }); }
    return next;
  }
}
