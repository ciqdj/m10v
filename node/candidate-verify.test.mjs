import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { decodeFrameMap, repackWithTarget } from './gr3-frames.mjs';
import { findCollabo, replaceCollabo } from './gr3-jpeg.mjs';
import { verifyCandidate } from './candidate-verify.mjs';

const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));
const decoded = decodeFrameMap(original).decoded;
const record = findCollabo(decoded);
const jpeg = decoded.subarray(record.start, record.end);

test('fresh candidate verification accepts only the exact intended logical scope', () => {
  const candidate = repackWithTarget(original, replaceCollabo(decoded, jpeg).targetDecoded).candidate;
  assert.equal(verifyCandidate(original, candidate, jpeg).status, 'candidate_offline_verified');
  const target = Buffer.from(decoded);
  target[record.end + 40] ^= 1;
  repair(target);
  assert.throws(() => verifyCandidate(original, repackWithTarget(original, target).candidate, jpeg));
  const cpu = Buffer.from(decoded);
  const cpuStart = [72, 556, 516, 44640, 21816, 17520064, 3062784,
    13899776, 49152].reduce((sum, size) => sum + 16 + size, 0);
  cpu[cpuStart + 16 + 0x90] ^= 1;
  repair(cpu);
  assert.throws(() => verifyCandidate(original, repackWithTarget(original, cpu).candidate, jpeg));
  const footer = Buffer.from(candidate);
  footer[footer.length - 1] ^= 1;
  assert.throws(() => verifyCandidate(original, footer, jpeg));
  const frame = Buffer.from(candidate);
  frame[130] ^= 1;
  assert.throws(() => verifyCandidate(original, frame, jpeg));
});

function repair(bytes) {
  let sum = 0;
  for (let i = 0; i < bytes.length - 4; i += 4) sum = (sum + bytes.readUInt32LE(i)) >>> 0;
  bytes.writeUInt32LE(-sum >>> 0, bytes.length - 4);
}
