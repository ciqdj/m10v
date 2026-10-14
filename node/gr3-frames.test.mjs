import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { decodeFrameMap, repackWithTarget } from './gr3-frames.mjs';

const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));

test('no-op frame replay is byte-for-byte official', () => {
  const map = decodeFrameMap(original);
  const result = repackWithTarget(original, map.decoded);
  assert.ok(result.candidate.equals(original));
  assert.equal(result.replaced_frames, 0);
});

test('one changed decoded byte becomes a fresh valid candidate stream', () => {
  const map = decodeFrameMap(original);
  const target = Buffer.from(map.decoded);
  target[40_000_000] ^= 1;
  repair(target);
  const result = repackWithTarget(original, target);
  assert.ok(result.replaced_frames > 0);
  assert.ok(decodeFrameMap(result.candidate).decoded.equals(target));
  assert.throws(() => repackWithTarget(original, target.subarray(0, -1)));
  const broken = Buffer.from(original);
  broken.writeUInt16BE(0x7fff, 128);
  assert.throws(() => decodeFrameMap(broken));
});

function repair(bytes) {
  let sum = 0;
  for (let i = 0; i < bytes.length - 4; i += 4) sum = (sum + bytes.readUInt32LE(i)) >>> 0;
  bytes.writeUInt32LE(-sum >>> 0, bytes.length - 4);
}
