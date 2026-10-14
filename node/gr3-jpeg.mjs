// Strict, one-record Street Edition resource edit for offline analysis only.
import { createHash } from 'node:crypto';
import { sum32 } from './gr3-frames.mjs';

const TARGET = 'B:\\Resource\\Jpeg\\Collabo.jpg';
const BYTES = 111155;
const DECODED_SHA = '53da690797f35ad6dc2c429d8ca1d0de8e333c211ed959816813982cd093b703';
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
function check(ok, message) { if (!ok) throw new Error(message); }

export function inspectStreetJpeg(jpeg) {
  check(Buffer.isBuffer(jpeg) && jpeg.length === BYTES && jpeg.readUInt16BE(0) === 0xffd8,
    'Street JPEG exact size or SOI differs');
  let position = 2;
  let frame = null;
  let scans = 0;
  const markers = [];
  while (position < jpeg.length) {
    check(jpeg[position] === 0xff && position + 1 < jpeg.length, 'JPEG marker missing');
    const marker = jpeg[position + 1];
    check(marker !== 0x00 && marker !== 0xff && marker !== 0xd8, 'unsupported JPEG marker');
    if (marker === 0xd9) {
      check(position + 2 === jpeg.length && frame && scans === 1, 'JPEG EOI or scan differs');
      return { width: frame.width, height: frame.height, bytes: jpeg.length,
        profile: { coding: 'baseline-DCT', components: frame.components,
          sampling: frame.sampling, scans, markers, sha256: hash(jpeg) } };
    }
    check(position + 4 <= jpeg.length, 'truncated JPEG segment');
    const length = jpeg.readUInt16BE(position + 2);
    check(length >= 2 && position + 2 + length <= jpeg.length, 'invalid JPEG segment length');
    markers.push(`0x${marker.toString(16)}`);
    if (marker === 0xc0) {
      check(!frame && length >= 8 && jpeg[position + 4] === 8, 'unsupported JPEG frame');
      const components = jpeg[position + 9];
      check(components === 3 && length === 8 + 3 * components, 'JPEG components differ');
      frame = { width: jpeg.readUInt16BE(position + 7),
        height: jpeg.readUInt16BE(position + 5), components,
        sampling: [jpeg[position + 11], jpeg[position + 14], jpeg[position + 17]] };
      check(frame.width === 720 && frame.height === 480, 'Street JPEG dimensions differ');
    } else if ((marker >= 0xc1 && marker <= 0xcf && marker !== 0xc4) ||
      !([0xc4, 0xdb, 0xdd, 0xda, 0xfe].includes(marker) || marker >= 0xe0 && marker <= 0xef)) {
      throw new Error('unsupported JPEG coding marker');
    }
    position += length + 2;
    if (marker === 0xda) {
      check(frame && ++scans === 1, 'JPEG scan structure differs');
      for (;;) {
        check(position + 1 < jpeg.length, 'truncated JPEG entropy data');
        if (jpeg[position] !== 0xff) { position++; continue; }
        const next = jpeg[position + 1];
        if (next === 0x00 || next >= 0xd0 && next <= 0xd7) { position += 2; continue; }
        check(next === 0xd9, 'unexpected marker inside JPEG entropy data');
        break;
      }
    }
  }
  throw new Error('JPEG EOI missing');
}

export function findCollabo(decoded) {
  check(Buffer.isBuffer(decoded) && decoded.length === 59718388, 'decoded size differs');
  let position = 0;
  const names = ['BOOTPARA', 'DRAMPARA', 'PARTPARA', 'M0', 'BOOT', 'RTOS',
    'LINUX', 'INITFS', 'SRIC', 'CPU', 'SHELLCMD', 'ICONBIN', 'FDRVPARA', 'RES'];
  for (const expected of names) {
    check(position + 16 <= decoded.length - 4, 'section header truncated');
    const name = decoded.toString('ascii', position, position + 8).split('\0')[0];
    check(name === expected, 'section sequence differs');
    const length = decoded.readUInt32LE(position + 12);
    if (expected !== 'RES') { position += 16 + length; continue; }
    check(length === 35, 'RES count differs');
    let cursor = position + 16;
    let found = null;
    for (let i = 0; i < 35; i++) {
      check(cursor + 36 <= decoded.length - 4, 'RES header truncated');
      const recordName = decoded.toString('ascii', cursor, cursor + 32).split('\0')[0];
      const size = decoded.readUInt32LE(cursor + 32);
      const start = cursor + 36;
      check(start + size <= decoded.length - 4, 'RES payload truncated');
      if (recordName === TARGET) {
        check(!found && size === BYTES, 'Street RES record shape differs');
        found = { start, end: start + size, res_start: position };
      }
      cursor = start + size;
    }
    check(found && cursor === decoded.length - 4, 'Street RES record or tail differs');
    return found;
  }
  throw new Error('RES section missing');
}

export function replaceCollabo(decoded, jpeg) {
  inspectStreetJpeg(jpeg);
  check(Buffer.isBuffer(decoded) && hash(decoded) === DECODED_SHA,
    'source decoded image differs from exact official baseline');
  const record = findCollabo(decoded);
  const targetDecoded = Buffer.from(decoded);
  jpeg.copy(targetDecoded, record.start);
  let total = 0;
  for (let at = 0; at < targetDecoded.length - 4; at += 4)
    total = (total + targetDecoded.readUInt32LE(at)) >>> 0;
  targetDecoded.writeUInt32LE(-total >>> 0, targetDecoded.length - 4);
  check(sum32(targetDecoded) === 0, 'decoded checksum repair failed');
  return { targetDecoded, changed_offset: record.start, changed_length: BYTES };
}
