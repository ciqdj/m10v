import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { test } from 'node:test';
import { createBackup, inspectBackup, restoreBytes } from './backup.mjs';
import { SHA256 } from './firmware.mjs';

const sample = new URL('../fwdc239b.bin', import.meta.url);
const pythonBackup = '/Users/zhaoo/Downloads/m10v-gr3-backup.zip';

test('Node backup validates and restores exact original', { skip: !existsSync(sample) }, () => {
  const original = readFileSync(sample);
  const backup = createBackup(original);
  const report = inspectBackup(backup);
  assert.equal(report.original_sha256, SHA256);
  assert.equal(report.recovery_scope, 'computer_official_package_only');
  assert.equal(report.camera_flash_included, false);
  assert.deepEqual(restoreBytes(backup), original);
  for (const forbidden of ['2.10.21.28', 'version_probe', 'candidate_sha256',
    'camera_flash_recovery']) assert.equal(backup.includes(Buffer.from(forbidden)), false);
  const changed = Buffer.from(backup);
  changed[200] ^= 1;
  assert.throws(() => inspectBackup(changed));
});

test('existing Python backup remains readable', { skip: !existsSync(pythonBackup) }, () => {
  const backup = readFileSync(pythonBackup);
  const report = inspectBackup(backup);
  assert.equal(report.original_sha256, SHA256);
  assert.equal(report.camera_flash_included, false);
});
