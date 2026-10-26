import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { decodeFrameMap, repackWithTarget } from './gr3-frames.mjs';

const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));

test('frame lengths come from bounded container metadata, with optional exact-size validation',()=>{
  const data=Buffer.alloc(160);data.writeUInt16BE(0x8004,128);data.write('test',130);
  data.writeUInt32LE(8,148);data.writeUInt32LE(4,152);
  assert.equal(decodeFrameMap(data).decoded.toString(),'test');
  assert.throws(()=>decodeFrameMap(data,8),/frame sizes/);
  for(const size of [0,128*1024*1024+1]){
    const bad=Buffer.from(data);bad.writeUInt32LE(size,152);assert.throws(()=>decodeFrameMap(bad),/frame sizes/);
  }
  const truncated=Buffer.from(data);truncated.writeUInt32LE(100,148);
  assert.throws(()=>decodeFrameMap(truncated),/frame sizes/);
  const wrong=Buffer.from(data);wrong.writeUInt32LE(8,152);
  assert.throws(()=>decodeFrameMap(wrong),/decoded length/);
});

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
