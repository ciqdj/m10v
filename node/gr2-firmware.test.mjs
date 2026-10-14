import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
const moduleURL = new URL('./gr2-firmware.mjs', import.meta.url);
const sample = new URL('../bin/rg2_v003/rg2_v003.frm', import.meta.url);
async function implementation() {
  assert.ok(existsSync(moduleURL), 'GR II UNITY inspector is not implemented');
  return import(moduleURL);
}
test('GR II block XOR uses a fresh key for each 512-byte block and is reversible', async () => {
  const {xorUnityPayload} = await implementation();
  const source = Buffer.alloc(516);
  const encoded = xorUnityPayload(source);
  assert.equal(encoded.readUInt32BE(0), 0xf8e69612);
  assert.equal(encoded.readUInt32BE(508), 0xf8e69612);
  assert.equal(encoded.readUInt32BE(512), 0xb72047a5);
  assert.deepEqual(xorUnityPayload(encoded), source);
  assert.throws(() => xorUnityPayload(Buffer.alloc(3)), /aligned/);
});
test('UNITY parser refuses truncated, overlapping and out-of-bounds records', async () => {
  const {decodeUnity} = await implementation();
  const bytes = Buffer.alloc(2560, 0xff);
  bytes.write('UNITY FILE V1.10 / RICOH COMPANY');
  bytes.writeUInt32BE(bytes.length, 32); bytes.writeUInt32BE(1, 36);
  bytes.writeUInt32BE(4, 64); bytes.writeUInt32BE(512, 68);
  bytes.fill(0, 72, 84); bytes.write('component', 72);
  bytes[94] = 1; bytes[95] = 1;
  assert.equal(decodeUnity(bytes).records.length, 1);
  assert.throws(() => decodeUnity(bytes.subarray(0, 2500)), /size/);
  const headerOverlap = Buffer.from(bytes); headerOverlap.writeUInt32BE(0, 64);
  assert.throws(() => decodeUnity(headerOverlap), /bounds|header/);
  const tooLong = Buffer.from(bytes); tooLong.writeUInt32BE(4096, 68);
  assert.throws(() => decodeUnity(tooLong), /bounds/);
});
test('exact GR II image decodes a resource disk and nested updater without altering bytes', {skip: !existsSync(sample)}, async () => {
  const {inspectGr2, readGr2Component, decodeUnity} = await implementation();
  const source = readFileSync(sample), report = inspectGr2(source);
  assert.equal(report.model, 'GR II'); assert.equal(report.size, 14033920);
  assert.equal(report.public_version, '3.00');
  assert.equal(report.components.length, 3);
  assert.equal(report.components.find(r => r.name === 'b01firm8').sha256, '13fa830bff194679628eb1bb3f233420ee23c4fca3a28c4b650c53692820de95');
  assert.equal(report.resources.length, 121);
  const resource = report.resources.find(r => r.name === 'A:/cpu1/cp1.bin');
  assert.equal(resource.declared_offset, 0x6e9c00);
  assert.equal(resource.payload_offset, 0x6e9e00);
  const disk = readGr2Component(source, 'b01firm6');
  assert.equal(disk.readUInt32BE(resource.payload_offset), 0xee110f10);
  assert.equal(report.proof.byte_exact_roundtrip, true);
  assert.equal(report.capabilities.native_film_library.can_build, false);
  assert.equal(readGr2Component(source, 'b01firm8').length, 6132308);
  assert.deepEqual(decodeUnity(source).reencoded, source);
});
test('GR II official inspection rejects wrong identity and unknown components', {skip: !existsSync(sample)}, async () => {
  const {inspectGr2, readGr2Component} = await implementation();
  const source = readFileSync(sample), damaged = Buffer.from(source); damaged[0x900] ^= 1;
  assert.throws(() => inspectGr2(damaged), /identity/);
  assert.throws(() => inspectGr2(source.subarray(0, source.length - 512)), /size/);
  assert.throws(() => readGr2Component(source, 'RTOS'), /unknown component/);
});
