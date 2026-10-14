// Read-only GR III feature evidence. No patch coordinates or build path.
import { createHash } from 'node:crypto';
import { readOfficialSection, SHA256 } from './firmware.mjs';

const TARGETS = [
  ['Collabo.jpg', 111155], ['GoodBye.jpg', 7264], ['GB_Diary.jpg', 112509],
  ['GB_ING.jpg', 91119], ['GB_Urban.jpg', 107902],
];
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');

function jpegDimensions(bytes) {
  if (bytes.length < 12 || bytes.readUInt16BE(0) !== 0xffd8 ||
    bytes.readUInt16BE(bytes.length - 2) !== 0xffd9) throw new Error('invalid JPEG boundaries');
  let position = 2;
  while (position + 4 <= bytes.length) {
    if (bytes[position] !== 0xff) throw new Error('invalid JPEG marker');
    const marker = bytes[position + 1];
    if (marker === 0xda || marker === 0xd9) break;
    const segment = bytes.readUInt16BE(position + 2);
    if (segment < 2 || position + 2 + segment > bytes.length) throw new Error('invalid JPEG segment');
    if ([0xc0, 0xc1, 0xc2].includes(marker)) {
      if (segment < 8 || bytes[position + 4] !== 8 || bytes[position + 9] !== 3)
        throw new Error('unsupported JPEG frame');
      return { width: bytes.readUInt16BE(position + 7), height: bytes.readUInt16BE(position + 5) };
    }
    position += 2 + segment;
  }
  throw new Error('JPEG frame header not found');
}

export function shutdownCatalog(data) {
  const res = readOfficialSection(data, 'RES');
  const records = new Map();
  let position = 0;
  for (let i = 0; i < 35; i++) {
    if (position + 36 > res.length) throw new Error('truncated RES record');
    const pathBytes = res.subarray(position, position + 32);
    const nullAt = pathBytes.indexOf(0);
    if (nullAt <= 0) throw new Error('unbounded RES path');
    const name = pathBytes.toString('ascii', 0, nullAt);
    const size = res.readUInt32LE(position + 32);
    const end = position + 36 + size;
    if (end > res.length || records.has(name)) throw new Error('invalid RES resource');
    records.set(name, res.subarray(position + 36, end));
    position = end;
  }
  if (position !== res.length) throw new Error('RES record tail differs');
  const resources = TARGETS.map(([filename, size]) => {
    const resourcePath = `B:\\Resource\\Jpeg\\${filename}`;
    const bytes = records.get(resourcePath);
    if (!bytes || bytes.length !== size) throw new Error(`missing official resource: ${filename}`);
    const dimensions = jpegDimensions(bytes);
    if (dimensions.width !== 720 || dimensions.height !== 480)
      throw new Error(`unexpected JPEG dimensions: ${filename}`);
    return {
      filename, path: resourcePath, size, sha256: hash(bytes), ...dimensions,
      preview_data_url: `data:image/jpeg;base64,${bytes.toString('base64')}`,
    };
  });
  return {
    source_sha256: SHA256, evidence: 'exact official BIN RES record and JPEG frame header',
    selection_verified: false, can_generate: false, resources,
  };
}
