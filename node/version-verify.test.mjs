import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { decodeFrameMap, sum32 } from './gr3-frames.mjs';
import { verifyVersionProbe } from './version-verify.mjs';

const official = readFileSync(new URL('../fwdc239b.bin', import.meta.url));
const TARGET = 0x020a151c;
const sizes = [72, 556, 516, 44640, 21816, 17520064, 3062784,
  13899776, 49152, 131072, 37440, 18354964, 36, 6595272];
const payloadStart = (index) => sizes.slice(0, index)
  .reduce((offset, size) => offset + 16 + size, 0) + 16;
const rtosVersion = payloadStart(5) + 0x2038;
const cpuStart = payloadStart(9);
const cpuChecksum = cpuStart + 0x7c;
const cpuVersion = cpuStart + 0x90;

function repairCpu(decoded) {
  decoded.writeUInt32BE(0, cpuChecksum);
  let value = 0;
  for (let at = cpuStart; at < cpuStart + sizes[9]; at += 4)
    value = (value + decoded.readUInt32BE(at)) >>> 0;
  decoded.writeUInt32BE(-value >>> 0, cpuChecksum);
}

function repairDecoded(decoded) {
  decoded.writeUInt32LE(0, decoded.length - 4);
  decoded.writeUInt32LE(-sum32(decoded) >>> 0, decoded.length - 4);
}

function unsafeRepack(targetDecoded) {
  const { decoded, frames } = decodeFrameMap(official);
  const chunks = [];
  for (const frame of frames) {
    const desired = targetDecoded.subarray(frame.decoded_start, frame.decoded_end);
    if (desired.equals(decoded.subarray(frame.decoded_start, frame.decoded_end))) {
      chunks.push(official.subarray(128 + frame.encoded_start, 128 + frame.encoded_end));
      continue;
    }
    for (let at = 0; at < desired.length; at += 0x6000) {
      const slice = desired.subarray(at, at + 0x6000);
      const prefix = Buffer.alloc(2);
      prefix.writeUInt16BE(0x8000 | slice.length);
      chunks.push(prefix, slice);
    }
  }
  chunks.push(Buffer.alloc(2));
  const payload = Buffer.concat(chunks);
  const footer = Buffer.from(official.subarray(-24));
  footer.writeUInt32LE(payload.length, 12);
  footer.writeUInt32LE(targetDecoded.length, 16);
  footer.writeUInt32LE(0, 20);
  const candidate = Buffer.concat([
    official.subarray(0, 128), payload, Buffer.alloc(-(128 + payload.length) & 3), footer,
  ]);
  candidate.writeUInt32BE(TARGET, 0x38);
  candidate.writeUInt32BE(TARGET, 0x50);
  candidate.writeUInt32LE(-sum32(candidate) >>> 0, candidate.length - 4);
  return candidate;
}

function baseDecoded() {
  const decoded = Buffer.from(decodeFrameMap(official).decoded);
  decoded.writeUInt32BE(TARGET, rtosVersion);
  decoded.writeUInt32BE(TARGET, cpuVersion);
  repairCpu(decoded);
  repairDecoded(decoded);
  return decoded;
}

function repairOuter(candidate) {
  candidate.writeUInt32LE(0, candidate.length - 4);
  candidate.writeUInt32LE(-sum32(candidate) >>> 0, candidate.length - 4);
  return candidate;
}

test('independent verifier accepts only the exact four-site successor probe', () => {
  const report = verifyVersionProbe(official, unsafeRepack(baseDecoded()), TARGET);
  assert.equal(report.status, 'version_probe_offline_verified');
  assert.equal(report.checks.non_target_unchanged, true);
  assert.equal(report.checks.cpu_sum32_be, 0);
});

test('independent verifier rejects logical, version and checksum tampering', () => {
  const extra = baseDecoded();
  extra[40_000_000] ^= 1;
  repairDecoded(extra);
  assert.throws(() => verifyVersionProbe(official, unsafeRepack(extra), TARGET), /non-target|diff/i);

  for (const offset of [0x38, 0x50]) {
    const changed = unsafeRepack(baseDecoded());
    changed.writeUInt32BE(TARGET + 1, offset);
    repairOuter(changed);
    assert.throws(() => verifyVersionProbe(official, changed, TARGET), /version/i);
  }

  const rtos = baseDecoded();
  rtos.writeUInt32BE(TARGET + 1, rtosVersion);
  repairDecoded(rtos);
  assert.throws(() => verifyVersionProbe(official, unsafeRepack(rtos), TARGET), /version/i);

  const cpu = baseDecoded();
  cpu.writeUInt32BE(TARGET + 1, cpuVersion);
  repairCpu(cpu);
  repairDecoded(cpu);
  assert.throws(() => verifyVersionProbe(official, unsafeRepack(cpu), TARGET), /version/i);

  const badCpuSum = baseDecoded();
  badCpuSum[cpuChecksum] ^= 1;
  repairDecoded(badCpuSum);
  assert.throws(() => verifyVersionProbe(official, unsafeRepack(badCpuSum), TARGET), /CPU checksum/i);

  const badDecodedSum = baseDecoded();
  badDecodedSum[badDecodedSum.length - 1] ^= 1;
  assert.throws(() => verifyVersionProbe(official, unsafeRepack(badDecodedSum), TARGET), /decoded checksum/i);

  const badContainerSum = unsafeRepack(baseDecoded());
  badContainerSum[badContainerSum.length - 1] ^= 1;
  assert.throws(() => verifyVersionProbe(official, badContainerSum, TARGET), /container checksum/i);

  const malformed = unsafeRepack(baseDecoded());
  malformed.writeUInt16BE(0x7fff, 128);
  repairOuter(malformed);
  assert.throws(() => verifyVersionProbe(official, malformed, TARGET));

  assert.throws(() => verifyVersionProbe(official, unsafeRepack(baseDecoded()), TARGET + 1),
    /target version/i);
});

