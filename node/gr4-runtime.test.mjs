import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp } from 'node:fs/promises';
import { stat } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Gr4Runtime } from './gr4-runtime.mjs';

test('GR IV runtime confines an immutable input and delegates to the reference bridge', async () => {
  const calls = [];
  const client = { async request(operation, payload, workspace) {
    calls.push({ operation, payload, workspace });
    return { id: 'project-fixture', input: { sha256: path.basename(payload.input_path || '', '.bin') } };
  } };
  const root = await mkdtemp(path.join(os.tmpdir(), 'm10v-gr4-runtime-'));
  const runtime = new Gr4Runtime(root, client);
  const bytes = Buffer.from('GR IV fixture placeholder');
  const result = await runtime.import(bytes, '../unsafe.bin');
  assert.equal(result.id, 'project-fixture');
  assert.equal(result.evidence, 'reference_verified');
  assert.equal(calls[0].operation, 'import');
  assert.equal(calls[0].workspace, root);
  assert.equal(await runtime.original(result.input.sha256).then((value) => value.toString()), bytes.toString());
  assert.throws(() => runtime.project('../escape'), /invalid GR IV identifier/);
});

test('GR IV status creates its confined runtime root before spawning the worker', async () => {
  const parent = await mkdtemp(path.join(os.tmpdir(), 'm10v-gr4-parent-'));
  const root = path.join(parent, 'missing-runtime');
  const client = { async request(_operation, _payload, workspace) {
    assert.equal((await stat(workspace)).isDirectory(), true);
    return { projects: [] };
  } };
  assert.deepEqual(await new Gr4Runtime(root, client).call('status'), { projects: [] });
});
