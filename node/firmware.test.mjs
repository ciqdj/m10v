import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { inspectOfficial, SHA256 } from './firmware.mjs';

const sample = new URL('../fwdc239b.bin', import.meta.url);

test('exact official GR III baseline has 14 verified sections', { skip: !exists(sample) }, () => {
  const data = readFileSync(sample);
  const report = inspectOfficial(data);
  assert.equal(report.sha256, SHA256);
  assert.equal(report.sections.length, 14);
  assert.equal(report.internal_version, '2.10.21.27');
  const changed = Buffer.from(data);
  changed[200] ^= 1;
  assert.throws(() => inspectOfficial(changed), /identity/);
});

test('unsupported data is rejected before parsing', () => {
  assert.throws(() => inspectOfficial(Buffer.alloc(4)), /size/);
});

function exists(url) {
  try { readFileSync(url, { flag: 'r' }); return true; } catch { return false; }
}
