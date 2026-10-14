import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createGr4Client } from './client.mjs';

const python = '/opt/homebrew/bin/python3.12';

test('GR IV worker handshake and reference version allocation are exact', async () => {
  const client = createGr4Client({ python });
  assert.deepEqual(await client.request('handshake'), {
    schema_version: 1, adapter: 'gr4', evidence: 'reference_verified' });
  assert.deepEqual(await client.request('allocate_version', { source: '1.11.10.7', ledger: [] }),
    { version: '1.11.10.10' });
  await assert.rejects(() => client.request('allocate_version', {
    source: '1.11.10.7', ledger: [{ version: '1.11.10.10' }], requested: '1.11.10.10',
  }), /1\.11\.10\.11/);
  await mkdtemp(path.join(os.tmpdir(), 'm10v-gr4-workspace-'));
  assert.throws(() => client.request('unknown', {}), /unknown GR IV operation/);
});

test('GR IV client rejects extra stdout, timeouts and oversized requests', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'm10v-gr4-client-'));
  const noisy = path.join(root, 'noisy.py');
  const hanging = path.join(root, 'hanging.py');
  await writeFile(noisy, 'print("warning")\nprint("{\\"ok\\":true,\\"result\\":{}}")\n');
  await writeFile(hanging, 'import time\ntime.sleep(60)\n');
  await assert.rejects(() => createGr4Client({ python, worker: noisy }).request('handshake'),
    /protocol is corrupt/);
  await assert.rejects(() => createGr4Client({ python, worker: hanging, timeoutMs: 30 }).request('handshake'),
    /timed out/);
  await assert.rejects(() => createGr4Client({ python }).request('handshake', { data: 'x'.repeat(193 * 1024 * 1024) }),
    /request exceeds/);
});
