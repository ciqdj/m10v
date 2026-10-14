import assert from 'node:assert/strict';
import { createHash, createPrivateKey, createPublicKey, sign, verify } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { crc32 } from 'node:zlib';
import { buildLocalFilmPack, localFilmPublicKey } from './gr3-local-film-pack.mjs';
import { auditLocalFilmPack } from './gr3-local-film-pack-audit.mjs';

const catalog = JSON.parse(readFileSync(new URL('../web/gr3/film-catalog.json', import.meta.url)));
const publicKey = createPublicKey({
  key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), localFilmPublicKey]),
  format: 'der', type: 'spki',
});

test('local film library signs plaintext records for the bundled five and one optional look', () => {
  const pack = buildLocalFilmPack(['hb-hncs']);
  assert.equal(pack.length, 13 * 8192);
  const header = pack.subarray(0, 8192);
  assert.equal(header.toString('ascii', 0, 8), 'GRLFILM2');
  assert.equal(header.readUInt16LE(10), 6);
  assert.equal(header.readUInt32LE(16), crc32(header.subarray(20)));
  assert.equal(header.subarray(280, 288).equals(Buffer.alloc(8)), true);
  assert.equal(header.toString('ascii', 40, 42), 'HB');
  assert.equal(header[512 + 5 * 16 + 13], 1);
  const record = pack.subarray(6 * 8192, 7 * 8192);
  assert.equal(record.toString('ascii', 8, 12), 'GRF2');
  assert.equal(record.readUInt32LE(12), crc32(record.subarray(16)));
  assert.equal(record.readUInt16LE(0x678), 0x100);
  assert.equal(record.subarray(0x6f8, 0x700).equals(Buffer.alloc(8)), true);
  assert.equal(record.readUInt32LE(0x674), crc32(Buffer.from('hb-hncs')));
  const look = catalog.looks.find((item) => item.id === 'hb-hncs');
  assert.equal(record.readInt16LE(72), look.matrixQ13[0]);
  assert.equal(record.readUInt16LE(112), look.curves[0][0]);
  assert.equal(record.subarray(1792).equals(Buffer.from(look.iconPixelsBase64, 'base64')), true);
  const digest = createHash('sha512').update(record.subarray(0, 12))
    .update(record.subarray(16, 1696)).update(record.subarray(1792)).digest();
  assert.equal(verify(null, Buffer.concat([Buffer.from('GRLIFE-FILM-2'), digest]),
    publicKey, record.subarray(1696, 1760)), true);
  const iconPage = pack.subarray(12 * 8192, 13 * 8192);
  assert.equal(iconPage.toString('ascii', 0, 4), 'GRB1');
  assert.equal(iconPage.readUInt32LE(4), crc32(iconPage.subarray(8)));
});

test('local film library rejects unknown, duplicate, and built-in selections', () => {
  assert.throws(() => buildLocalFilmPack(['not-a-film']), /胶片/);
  assert.throws(() => buildLocalFilmPack(['hb-hncs', 'hb-hncs']), /胶片/);
  assert.throws(() => buildLocalFilmPack(['ektar100']), /胶片/);
});

test('independent pack audit accepts all looks and rejects one altered record', () => {
  const pack = buildLocalFilmPack(catalog.looks.slice(5).map((look) => look.id));
  assert.deepEqual(auditLocalFilmPack(pack), {film_count:32,device_bound:false,signature_count:32});
  const corrupt = Buffer.from(pack);
  corrupt[6 * 8192 + 1696] ^= 1;
  assert.throws(() => auditLocalFilmPack(corrupt), /胶片记录/);
});

test('independent pack audit rejects a validly signed record with wrong color data', () => {
  const pack = buildLocalFilmPack(['hb-hncs']);
  const record = pack.subarray(6 * 8192, 7 * 8192);
  record.writeInt16LE(record.readInt16LE(72) + 1, 72);
  const seed = createHash('sha256').update('m10v-gr3-local-film-bay-v1-public-key').digest();
  const privateKey = createPrivateKey({
    key: Buffer.concat([Buffer.from('302e020100300506032b657004220420','hex'), seed]),
    format:'der',type:'pkcs8',
  });
  const digest = createHash('sha512').update(record.subarray(0, 12))
    .update(record.subarray(16, 1696)).update(record.subarray(1792)).digest();
  sign(null, Buffer.concat([Buffer.from('GRLIFE-FILM-2'), digest]), privateKey).copy(record, 1696);
  record.writeUInt32LE(crc32(record.subarray(16)), 12);
  assert.throws(() => auditLocalFilmPack(pack), /胶片记录/);
});
