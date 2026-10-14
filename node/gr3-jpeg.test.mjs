import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { readOfficialSection } from './firmware.mjs';
import { decodeFrameMap } from './gr3-frames.mjs';
import { inspectStreetJpeg, replaceCollabo } from './gr3-jpeg.mjs';

const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));
const decoded = decodeFrameMap(original).decoded;
const res = readOfficialSection(original, 'RES');
let cursor = 0;
let jpeg;
for (let i = 0; i < 35; i++) {
  const name = res.toString('ascii', cursor, cursor + 32).split('\0')[0];
  const size = res.readUInt32LE(cursor + 32);
  if (name === 'B:\\Resource\\Jpeg\\Collabo.jpg') jpeg = res.subarray(cursor + 36, cursor + 36 + size);
  cursor += 36 + size;
}

test('the official Street JPEG has the exact expected record profile', () => {
  assert.deepEqual([inspectStreetJpeg(jpeg).width, inspectStreetJpeg(jpeg).height,
    inspectStreetJpeg(jpeg).bytes], [720, 480, 111155]);
  assert.ok(replaceCollabo(decoded, jpeg).targetDecoded.equals(decoded));
});

test('rejects mismatched length, dimensions, trailing data and unsupported coding', () => {
  assert.throws(() => inspectStreetJpeg(jpeg.subarray(0, -1)));
  assert.throws(() => inspectStreetJpeg(Buffer.concat([jpeg, Buffer.from([0])])));
  const wrong = Buffer.from(jpeg);
  const sof = wrong.indexOf(Buffer.from([0xff, 0xc0]));
  assert.ok(sof > 0);
  wrong.writeUInt16BE(721, sof + 7);
  assert.throws(() => inspectStreetJpeg(wrong));
  wrong.writeUInt16BE(720, sof + 7);
  wrong[sof + 1] = 0xc2;
  assert.throws(() => inspectStreetJpeg(wrong));
  const changedRecord = Buffer.from(decoded);
  changedRecord[changedRecord.length - 100] ^= 1;
  assert.throws(() => replaceCollabo(changedRecord, jpeg));
});
