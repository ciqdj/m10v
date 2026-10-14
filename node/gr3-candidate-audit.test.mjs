import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { auditGr3Candidate } from './gr3-candidate-audit.mjs';

const originalPath = new URL('../fwdc239b.bin', import.meta.url);
const modifiedPath = new URL('../fwdc239b-modify.bin', import.meta.url);
const available = await Promise.all([originalPath, modifiedPath]
  .map((file) => access(file).then(() => true, () => false)));

test('independent decoder accepts the exact GRLife output and identifies modified sections',
  { skip: !available.every(Boolean) }, async () => {
    const original = await readFile(originalPath);
    const candidate = await readFile(modifiedPath);
    const result = auditGr3Candidate(original, candidate);
    assert.deepEqual(result.changedSections, ['RTOS', 'ICONBIN']);
    assert.equal(result.rtosGrowth, 27200);
    assert.equal(result.candidateSha256,
      '4dd72e70c0f88749f89ccbd213ff4f46557d05c29b438731f69db615757aff21');
  });

test('independent decoder rejects a changed firmware byte',
  { skip: !available.every(Boolean) }, async () => {
    const original = await readFile(originalPath);
    const candidate = Buffer.from(await readFile(modifiedPath));
    candidate[1000] ^= 1;
    assert.throws(() => auditGr3Candidate(original, candidate), /checksum/);
  });
