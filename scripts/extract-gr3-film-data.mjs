// Extract UI preview tables and actual 40×40 camera icons from the user's output BIN.
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeFrameMap } from '../node/gr3-frames.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const candidate = await readFile(path.join(root, 'fwdc239b-modify.bin'));
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
if (sha(candidate) !== '4dd72e70c0f88749f89ccbd213ff4f46557d05c29b438731f69db615757aff21')
  throw new Error('the supplied GRLife output has changed');
const runtime = process.env.GRLIFE_CORE_PATH || path.join(root, '.runtime', 'grlife');
const template = JSON.parse(await readFile(path.join(runtime,
  'reconstruction/firmware_store/templates/film-v10.json'), 'utf8'));
const decoded = decodeFrameMap(candidate, candidate.readUInt32LE(candidate.length - 8)).decoded;
const output = { schema: 'm10v-gr3-film-preview/v1', sourceFirmwareSha256: sha(candidate),
  note: 'Tables and icon pixels extracted from the user-supplied GRLife output; preview approximates JPEG rendering.',
  looks: [] };
for (const [mode, slot] of Object.entries(template.slots)) {
  const iconOffset = template.icon_patches.find((entry) => entry.mode === mode).offset + 27200;
  const icon = decoded.subarray(iconOffset, iconOffset + 6400);
  const nameBytes = decoded.subarray(slot.name_offset, slot.name_offset + 2 * (slot.name_room + 1));
  const name = nameBytes.toString('utf16le').split('\0', 1)[0];
  const matrix = (offset) => Array.from({ length: 9 }, (_, index) => decoded.readInt16LE(offset + 2 * index));
  const points = (offset, count) => Array.from({ length: count }, (_, index) =>
    decoded.readUInt16LE(offset + 2 * index));
  output.looks.push({ mode, name, iconPixelsBase64: icon.toString('base64'),
    matrixQ13: matrix(slot.matrix_offset), postQ512: matrix(slot.post_offset),
    ...(slot.curve_offsets ? { curves: slot.curve_offsets.map((offset) => points(offset, 256)) } :
      { knots: [0, 1, 2].map((channel) => points(slot.knots_offset + channel * 66, 33)) }) });
}
await writeFile(path.join(root, 'web/gr3/film-data.json'), JSON.stringify(output));
console.log(output.looks.map((look) => look.name).join(', '));
