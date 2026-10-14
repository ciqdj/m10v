import { createHash, createPrivateKey, createPublicKey, sign } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { crc32 } from 'node:zlib';

const PAGE = 8192;
const catalog = JSON.parse(readFileSync(new URL('../web/gr3/film-catalog.json', import.meta.url)));
const looks = catalog.looks;
const builtInIds = looks.slice(0, 5).map((look) => look.id);
const optionalIds = new Set(looks.slice(5).map((look) => look.id));
const groupNames = new Map([
  ['内置胶片', 'Classic'], ['哈苏风格', 'HB'], ['宾得风格', 'PX'],
  ['徕卡 M9 风格', 'M9'], ['富士 Superia', 'Superia'],
  ['柯达 UltraMax 400', 'UltraMax'], ['柯达 Vision3', 'Vision3'],
  ['理光 GR II 风格', 'GR II'],
]);
// This project key is intentionally public: it checks file integrity and firmware/pack pairing,
// and grants no access to GRLife's issuer or signing service.
const seed = createHash('sha256').update('m10v-gr3-local-film-bay-v1-public-key').digest();
const privateKey = createPrivateKey({
  key: Buffer.concat([Buffer.from('302e020100300506032b657004220420', 'hex'), seed]),
  format: 'der', type: 'pkcs8',
});
export const localFilmPublicKey = createPublicKey(privateKey).export({format:'der',type:'spki'}).subarray(-32);

function requireSelection(ids) {
  if (!Array.isArray(ids) || ids.length > optionalIds.size ||
      ids.some((id) => typeof id !== 'string' || !optionalIds.has(id)) ||
      new Set(ids).size !== ids.length) throw new Error('胶片选择无效。');
  return looks.filter((look) => builtInIds.includes(look.id) || ids.includes(look.id));
}

function recordFor(look) {
  const record = Buffer.alloc(PAGE);
  if (!/^[\x20-\x7e]{1,12}$/.test(look.name)) throw new Error(`胶片名称无效：${look.id}`);
  const icon = Buffer.from(look.iconPixelsBase64, 'base64');
  if (icon.length !== 6400 || look.matrixQ13.length !== 9 || look.postQ512.length !== 9 ||
      look.curves.length !== 3 || look.curves.some((curve) => curve.length !== 256))
    throw new Error(`胶片数据不完整：${look.id}`);
  record.writeUInt16LE(40, 0); record.writeUInt16LE(40, 2);
  record.write('GRF2', 8, 'ascii');
  record.write(look.name, 16, 'ascii');
  record[36] = look.name.length + 1; record[37] = 1;
  record.write(look.name, 44, 'utf16le');
  look.matrixQ13.forEach((value, index) => record.writeInt16LE(value, 72 + index * 2));
  look.postQ512.forEach((value, index) => record.writeInt16LE(value, 92 + index * 2));
  look.curves.forEach((curve, channel) => curve.forEach((value, index) =>
    record.writeUInt16LE(value, 112 + channel * 512 + index * 2)));
  record.writeUInt32LE(crc32(Buffer.from(look.id)), 0x674);
  record.writeUInt16LE(0x100, 0x678); // Signed plaintext, without device binding.
  icon.copy(record, 0x700);
  const digest = createHash('sha512').update(record.subarray(0, 12))
    .update(record.subarray(16, 0x6a0)).update(record.subarray(0x700)).digest();
  sign(null, Buffer.concat([Buffer.from('GRLIFE-FILM-2'), digest]), privateKey).copy(record, 0x6a0);
  record.writeUInt32LE(crc32(record.subarray(16)), 12);
  return record;
}

function iconPageFor(record) {
  const page = Buffer.alloc(PAGE);
  page.write('GRB1', 0, 'ascii');
  record.copy(page, 8, 0x700, PAGE);
  page.writeUInt32LE(crc32(page.subarray(8)), 4);
  return page;
}

export function buildLocalFilmPack(ids) {
  const selected = requireSelection(ids);
  const header = Buffer.alloc(PAGE);
  header.write('GRLFILM2', 0, 'ascii');
  header.writeUInt16LE(2, 8);
  header.writeUInt16LE(selected.length, 10);
  header.writeUInt32LE(PAGE, 12);
  const groups = [...new Set(selected.map((look) => groupNames.get(look.group)))];
  if (groups.some((group) => !group) || groups.length > 8) throw new Error('胶片分组无效。');
  header.writeUInt16LE(groups.length, 20);
  header.writeUInt16LE(1, 22);
  groups.forEach((group, index) => header.write(group, 24 + index * 16, 'ascii'));
  selected.forEach((look, index) => {
    const at = 512 + index * 16;
    header.write(look.name, at, 'ascii');
    header[at + 13] = groups.indexOf(groupNames.get(look.group));
    header[at + 14] = index >= 5 ? 1 : 0;
  });
  header.writeUInt32LE(crc32(header.subarray(20)), 16);
  const records = selected.map(recordFor);
  return Buffer.concat([header, ...records, ...records.map(iconPageFor)]);
}
