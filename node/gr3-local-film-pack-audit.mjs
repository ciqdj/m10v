import { createHash, createPublicKey, verify } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { crc32 } from 'node:zlib';
import { localFilmPublicKey } from './gr3-local-film-pack.mjs';

const PAGE = 8192;
const catalog = JSON.parse(readFileSync(new URL('../web/gr3/film-catalog.json', import.meta.url)));
const byCrc = new Map(catalog.looks.map((look) => [crc32(Buffer.from(look.id)), look]));
const key = createPublicKey({
  key: Buffer.concat([Buffer.from('302a300506032b6570032100', 'hex'), localFilmPublicKey]),
  format:'der', type:'spki',
});
const need = (condition, message) => {if (!condition) throw new Error(message);};

export function auditLocalFilmPack(input) {
  const pack = Buffer.from(input);
  need(pack.length >= 11 * PAGE && pack.length % PAGE === 0, '胶片库文件长度无效。');
  const header = pack.subarray(0, PAGE);
  const count = header.readUInt16LE(10);
  need(header.toString('ascii', 0, 8) === 'GRLFILM2' && header.readUInt16LE(8) === 2 &&
    count >= 5 && count <= 32 && header.readUInt32LE(12) === PAGE &&
    pack.length === (1 + 2 * count) * PAGE &&
    header.readUInt32LE(16) === crc32(header.subarray(20)) &&
    header.subarray(280, 288).equals(Buffer.alloc(8)), '胶片库文件头或机身绑定无效。');
  const seen = new Set();
  for (let index = 0; index < count; index++) {
    const record = pack.subarray((index + 1) * PAGE, (index + 2) * PAGE);
    const icon = pack.subarray((count + index + 1) * PAGE, (count + index + 2) * PAGE);
    const look = byCrc.get(record.readUInt32LE(0x674));
    need(look && !seen.has(look.id) &&
      record.readUInt16LE(0) === 40 && record.readUInt16LE(2) === 40 &&
      record.toString('ascii', 8, 12) === 'GRF2' &&
      record.readUInt32LE(12) === crc32(record.subarray(16)) &&
      record.toString('ascii', 16, 16 + look.name.length) === look.name &&
      record.readUInt16LE(0x678) === 0x100 &&
      record.subarray(0x6f8, 0x700).equals(Buffer.alloc(8)),
      `胶片记录 ${index + 1} 的格式无效。`);
    seen.add(look.id);
    const colorMatches = look.matrixQ13.every((value, at) => record.readInt16LE(72 + at * 2) === value) &&
      look.postQ512.every((value, at) => record.readInt16LE(92 + at * 2) === value) &&
      look.curves.every((curve, channel) => curve.every((value, at) =>
        record.readUInt16LE(112 + channel * 512 + at * 2) === value));
    need(colorMatches && record.subarray(0x700).equals(Buffer.from(look.iconPixelsBase64, 'base64')),
      `胶片记录 ${index + 1} 的色彩或图标数据无效。`);
    const digest = createHash('sha512').update(record.subarray(0, 12))
      .update(record.subarray(16, 0x6a0)).update(record.subarray(0x700)).digest();
    need(verify(null, Buffer.concat([Buffer.from('GRLIFE-FILM-2'), digest]),
      key, record.subarray(0x6a0, 0x6e0)), `胶片记录 ${index + 1} 的签名无效。`);
    need(icon.toString('ascii', 0, 4) === 'GRB1' &&
      icon.readUInt32LE(4) === crc32(icon.subarray(8)) &&
      icon.subarray(8, 6408).equals(record.subarray(0x700)),
      `胶片记录 ${index + 1} 的图标无效。`);
  }
  need(catalog.looks.slice(0, 5).every((look) => seen.has(look.id)), '胶片库缺少内置胶片。');
  return {film_count:count,device_bound:false,signature_count:count};
}
