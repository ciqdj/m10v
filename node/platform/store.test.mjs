import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, symlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { PlatformStore } from './store.mjs';

const bytes = Buffer.from('exact firmware fixture');
const adapter = {
  id: 'fixture',
  createDraft: () => ({ schema_version: 1, value: 0 }),
  validateDraft(value) {
    if (!value || value.schema_version !== 1 || !Number.isInteger(value.value))
      throw new Error('invalid fixture draft');
    return value;
  },
};
const registry = {
  detect(value) {
    if (!value.equals(bytes)) throw new Error('unsupported firmware');
    return { adapter, inspection: { model: 'Fixture Camera', public_version: '1.0',
      internal_version: '1.0.0.1' } };
  },
  get(id) { if (id !== adapter.id) throw new Error('unknown adapter'); return adapter; },
};

async function fixture(options) {
  return new PlatformStore(await mkdtemp(path.join(os.tmpdir(), 'm10v-store-')), registry, options);
}

test('one immutable object can own two isolated optimistic-revision projects', async () => {
  const store = await fixture();
  const object = await store.importObject(bytes, 'fixture.bin');
  const first = await store.createProject(object.sha256, 'First');
  const second = await store.createProject(object.sha256, 'Second');
  assert.notEqual(first.id, second.id);
  assert.equal(first.adapter_id, 'fixture');
  assert.equal((await store.readObject(object.sha256)).toString(), bytes.toString());

  const saved = await store.saveDraft(first.id, 0, { schema_version: 1, value: 7 });
  assert.equal(saved.revision, 1);
  assert.deepEqual(saved.draft, { schema_version: 1, value: 7 });
  await assert.rejects(() => store.saveDraft(first.id, 0, { schema_version: 1, value: 8 }),
    /project revision conflict/);
  assert.equal((await store.readProject(second.id)).revision, 0);
});

test('store rejects malformed ids, adapter mismatch and symlinked project roots', async () => {
  const store = await fixture();
  const object = await store.importObject(bytes, 'fixture.bin');
  const project = await store.createProject(object.sha256, 'Safe');
  await assert.rejects(() => store.readProject('../escape'), /invalid project id/);

  const recordPath = path.join(store.root, 'projects', project.id, 'project.json');
  const record = JSON.parse(await readFile(recordPath, 'utf8'));
  record.adapter_id = 'other';
  await assert.rejects(() => store.validateProjectRecord(record), /project adapter differs/);

  const unsafeRoot = await mkdtemp(path.join(os.tmpdir(), 'm10v-store-link-'));
  const target = await mkdtemp(path.join(os.tmpdir(), 'm10v-store-target-'));
  await mkdir(path.join(unsafeRoot, 'objects'));
  await symlink(target, path.join(unsafeRoot, 'projects'));
  const unsafe = new PlatformStore(unsafeRoot, registry);
  await assert.rejects(() => unsafe.ensureRoot(),
    /unsafe projects directory/);
});

test('interrupted object publication leaves no readable partial object', async () => {
  const store = await fixture({ beforeObjectPublish: async () => { throw new Error('injected'); } });
  await assert.rejects(() => store.importObject(bytes, 'fixture.bin'), /injected/);
  await assert.rejects(() => store.readObject('f'.repeat(64)), /object not found/);
});
