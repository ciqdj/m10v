import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { mkdtemp, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { prepareOfficialSd } from './sd-write.mjs';

const sample = new URL('../fwdc239b.bin', import.meta.url);
const official = existsSync(sample) ? readFileSync(sample) : null;

async function withVolume(run) {
  const mount_point = await mkdtemp(path.join(os.tmpdir(), 'm10v-sd-'));
  const volume = { device_identifier: 'disk7s1', mount_point, free_bytes: 64_000_000 };
  try { await run(volume); } finally { await rm(mount_point, { recursive: true, force: true }); }
}

test('stages exact official BIN then proves on-volume hash and length',
  { skip: !official }, async () => withVolume(async (volume) => {
    const result = await prepareOfficialSd(official, volume);
    assert.equal(result.status, 'official_sd_ready');
    assert.equal(result.filename, 'fwdc239b.bin');
    assert.equal(result.bytes, 30_391_780);
    assert.equal(result.sha256, 'd6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4');
    assert.deepEqual(await readdir(volume.mount_point), ['fwdc239b.bin']);
    assert.ok((await readFile(path.join(volume.mount_point, result.filename))).equals(official));
  }));

test('refuses existing firmware and leaves it untouched',
  { skip: !official }, async () => withVolume(async (volume) => {
    const target = path.join(volume.mount_point, 'fwdc239b.bin');
    await writeFile(target, 'previous firmware');
    await assert.rejects(prepareOfficialSd(official, volume), /already exists/);
    assert.equal(await readFile(target, 'utf8'), 'previous firmware');
    assert.deepEqual(await readdir(volume.mount_point), ['fwdc239b.bin']);
  }));

test('low space and mismatching readback never report ready',
  { skip: !official }, async () => withVolume(async (volume) => {
    await assert.rejects(prepareOfficialSd(official, { ...volume, free_bytes: 5 }), /space/);
    assert.deepEqual(await readdir(volume.mount_point), []);
    await assert.rejects(prepareOfficialSd(official, volume, { readback: async () => Buffer.from('wrong') }),
      /readback/);
    assert.deepEqual(await readdir(volume.mount_point), []);
  }));

test('publication race preserves the competing target and removes only owned staging',
  { skip: !official }, async () => withVolume(async (volume) => {
    const target = path.join(volume.mount_point, 'fwdc239b.bin');
    await assert.rejects(prepareOfficialSd(official, volume, {
      beforePublish: async ({ destination }) => writeFile(destination, 'race winner'),
    }), /exist|publish/i);
    assert.equal(await readFile(target, 'utf8'), 'race winner');
    assert.deepEqual(await readdir(volume.mount_point), ['fwdc239b.bin']);
  }));

test('forced atomic publication failure leaves neither target nor staging file',
  { skip: !official }, async () => withVolume(async (volume) => {
    await assert.rejects(prepareOfficialSd(official, volume, {
      publish: async () => { throw new Error('forced publish failure'); },
    }), /forced publish failure/);
    assert.deepEqual(await readdir(volume.mount_point), []);
  }));

test('post-move command failure removes the target owned by this attempt',
  { skip: !official }, async () => withVolume(async (volume) => {
    await assert.rejects(prepareOfficialSd(official, volume, {
      publish: async (stage, destination) => {
        await rename(stage, destination);
        throw new Error('post-move status failure');
      },
    }), /post-move status failure/);
    assert.deepEqual(await readdir(volume.mount_point), []);
  }));
