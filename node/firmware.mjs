// Exact GR III baseline inspection. This module has no firmware writer.
import { createHash } from 'node:crypto';

export const SHA256 = 'd6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4';
const FILE_SIZE = 30391780;
const DECODED_SIZE = 59718388;
const RTOS_HASH = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67';
const rules = [
  ['BOOTPARA', 72, 0xffff0005], ['DRAMPARA', 556, 0xffff0001],
  ['PARTPARA', 516, 0xffff0002], ['M0', 44640, 3], ['BOOT', 21816, 4],
  ['RTOS', 17520064, 0x10004], ['LINUX', 3062784, 0x50004],
  ['INITFS', 13899776, 0x60004], ['SRIC', 49152, 0x20004],
  ['CPU', 131072, 7], ['SHELLCMD', 37440, 0x30004],
  ['ICONBIN', 18354964, 0x40004], ['FDRVPARA', 36, 0xffff0008],
  ['RES', 6595272, 0xffff0006, 35],
];

const hash = (data) => createHash('sha256').update(data).digest('hex');
const requireValue = (condition, reason) => { if (!condition) throw new Error(reason); };

function sum32(data) {
  requireValue(data.length % 4 === 0, 'container: unaligned checksum');
  let value = 0;
  for (let i = 0; i < data.length; i += 4) value = (value + data.readUInt32LE(i)) >>> 0;
  return value;
}

function decode(payload) {
  const output = Buffer.allocUnsafe(DECODED_SIZE);
  let position = 0;
  let used = 0;
  let frames = 0;
  while (true) {
    requireValue(position + 2 <= payload.length, 'decoded: missing stream terminator');
    const prefix = payload.readUInt16BE(position);
    position += 2;
    if (prefix === 0) {
      requireValue(position === payload.length && used === DECODED_SIZE, 'decoded: length or terminator mismatch');
      return { output, frames };
    }
    const length = prefix & 0x7fff;
    const end = position + length;
    requireValue(length > 0 && end <= payload.length, 'decoded: invalid frame length');
    frames++;
    if (prefix & 0x8000) {
      requireValue(used + length <= DECODED_SIZE, 'decoded: literal overrun');
      payload.copy(output, used, position, end);
      used += length;
      position = end;
      continue;
    }
    let terminated = false;
    while (position < end && !terminated) {
      requireValue(position + 2 <= end, 'decoded: truncated flags');
      const flags = payload.readUInt16BE(position);
      position += 2;
      for (let bit = 15; bit >= 0; bit--) {
        if (!(flags & (1 << bit))) {
          requireValue(position < end && used < DECODED_SIZE, 'decoded: literal token overrun');
          output[used++] = payload[position++];
          continue;
        }
        requireValue(position + 2 <= end, 'decoded: truncated back-reference');
        const first = payload[position++];
        const second = payload[position++];
        const offset = ((first & 0xf8) << 5) | second;
        let count = first & 7;
        if (count === 7) {
          requireValue(position < end, 'decoded: truncated extension');
          count += payload[position++];
        }
        if (offset === 0) {
          requireValue(position === end, 'decoded: trailing bytes after frame terminator');
          terminated = true;
          break;
        }
        if (count === 262) {
          let extra = 255;
          while (extra === 255) {
            requireValue(position < end, 'decoded: truncated long extension');
            extra = payload[position++];
            count += extra;
          }
        }
        count += 3;
        requireValue(offset <= used && used + count <= DECODED_SIZE, 'decoded: invalid back-reference');
        for (let i = 0; i < count; i++) output[used + i] = output[used + i - offset];
        used += count;
      }
    }
    requireValue(terminated, 'decoded: frame has no end marker');
    position = end;
  }
}

export function inspectOfficial(data) {
  requireValue(Buffer.isBuffer(data), 'input: firmware must be bytes');
  const identity = hash(data);
  const isX = identity === '708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7';
  requireValue(data.length === (isX ? 30391788 : FILE_SIZE), 'size: unsupported firmware length');
  requireValue(identity === SHA256 || isX, 'identity: full-file SHA-256 differs from supported official baseline');
  const project = isX ? 0x02610261 : 0x024c024c;
  const version = isX ? 0x013c0b11 : 0x020a151b;
  const footer = data.length - 24;
  const encodedSize = data.readUInt32LE(footer + 12);
  const decodedSize = data.readUInt32LE(footer + 16);
  const payloadEnd = 128 + encodedSize;
  const metadataStart = (payloadEnd + 3) & ~3;
  requireValue(data.readUInt32LE(48) === (isX ? 609 : 588) && data.readUInt32LE(120) === project &&
    data.readUInt32LE(footer) === project, 'container: project mismatch');
  requireValue(data.readUInt32LE(124) === 0xa55a5aa5 && data.readUInt32LE(footer + 4) === 0xa55a5aa5 &&
    data.readUInt32LE(footer + 8) === 2, 'container: marker or type mismatch');
  requireValue(sum32(data) === 0, 'container: additive checksum failed');
  requireValue(payloadEnd <= footer && metadataStart <= footer && metadataStart === footer &&
    data.readUInt32LE(60) === 0 && decodedSize === DECODED_SIZE, 'container: metadata or decoded length mismatch');
  const { output, frames } = decode(data.subarray(128, payloadEnd));
  const sections = [];
  const rows = new Map();
  let position = 0;
  for (const [name, payloadSize, flags, resourceCount] of rules) {
    const end = position + 16 + payloadSize;
    requireValue(end <= output.length - 4, `sections: ${name} exceeds decoded stream`);
    const actualName = output.toString('ascii', position, position + 8).split('\0', 1)[0];
    requireValue(actualName === name && output.readUInt32LE(position + 8) === flags,
      `sections: layout mismatch at ${name}`);
    const lengthField = output.readUInt32LE(position + 12);
    requireValue(lengthField === (name === 'RES' ? resourceCount : payloadSize),
      `sections: length mismatch at ${name}`);
    rows.set(name, output.subarray(position + 16, end));
    const block = output.subarray(position, end);
    sections.push({ name, size: block.length, sha256: hash(block) });
    position = end;
  }
  requireValue(position + 4 === output.length && sum32(output) === 0,
    'sections: decoded trailer or checksum mismatch');
  const rtos = rows.get('RTOS');
  const cpu = rows.get('CPU');
  requireValue(rtos.length === 17520064 && hash(rtos) === (isX ? '0f11b0d28bc67932d044c5d01bc0314844a756057c89984278c73a23449a24c6' : RTOS_HASH),
    'rtos: unsupported baseline content');
  requireValue(rtos.readUInt32LE(0x450) === 0x5407b540 &&
    rtos.readUInt32LE(0x454) === 0x55000000 && rtos.readUInt32LE(0x458) === 0x3a080,
  'rtos: startup copy layout mismatch');
  for (const [name, word] of [
    ['rtos', rtos.readUInt32BE(0x2038)], ['cpu', cpu.readUInt32BE(0x90)],
    ['outer_cpu', data.readUInt32BE(0x38)], ['outer_dsp', data.readUInt32BE(0x50)],
  ]) requireValue(word === version, `version: ${name} differs`);
  return {
    model: isX ? 'GR IIIx' : 'GR III', public_version: isX ? '1.60' : '2.10', internal_version: isX ? '1.60.11.17' : '2.10.21.27',
    sha256: identity, size: data.length, sections,
    proof: { identity: true, container: true, decoded: true, sections: true,
      versions: true, strict_frames: frames > 0 },
  };
}

export function readOfficialSection(data, name) {
  // Revalidate the entire exact baseline before exposing a read-only payload.
  inspectOfficial(data);
  if (!rules.some((rule) => rule[0] === name)) throw new Error('unknown official section');
  const end = 128 + data.readUInt32LE(data.length - 12);
  const { output } = decode(data.subarray(128, end));
  let offset = 0;
  for (const [sectionName, size] of rules) {
    if (sectionName === name) return Buffer.from(output.subarray(offset + 16, offset + 16 + size));
    offset += 16 + size;
  }
  throw new Error('unknown official section');
}
