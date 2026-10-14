// Read-only anchors for the exact GR III 2.10 pair. This script emits no patch or firmware.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { readOfficialSection, SHA256 } from '../node/firmware.mjs';
import { decodeFrameMap } from '../node/gr3-frames.mjs';

const official = readFileSync(process.argv[2] || new URL('../fwdc239b.bin', import.meta.url));
const modified = readFileSync(process.argv[3] || new URL('../fwdc239b-modify.bin', import.meta.url));
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const check = (condition, message) => { if (!condition) throw new Error(message); };
check(hash(official) === SHA256, 'official firmware identity differs');
check(hash(modified) === '4dd72e70c0f88749f89ccbd213ff4f46557d05c29b438731f69db615757aff21',
  'modified firmware identity differs');

const rtos = readOfficialSection(official, 'RTOS');
const captureOffset = 0x5048e8;
const captureVA = 0x53000000 + captureOffset;
const originalWord = rtos.readUInt32LE(captureOffset);
check(originalWord === 0xeb069d0e, 'GR III stock capture call differs');
function branchTarget(address, word) {
  const signed = (word << 8) >> 8;
  return (address + 8 + (signed << 2)) >>> 0;
}
check(branchTarget(captureVA, originalWord) === 0x536abd28, 'stock capture target differs');

// GRLife's locked GR IIIx profile differs from this exact GR III RTOS only at identity spans.
const identity = [
  [0x200e, '78'], [0x2030, '61'], [0x2034, '9a'], [0x2038, '013c0b11'],
  [0x2066, '33303a3530'], [0x2078, '610261'], [0x6b62ec, 'e4'], [0x6b6574, '04'],
  [0x81fe4c, '610200'], [0x81fe54, '9a'], [0x81fe6c, '4f0fa0'], [0x81fe74, '01'],
  [0x81fe7c, '3c'], [0x81fe84, '110b00'], [0x81fe8c, '0b'], [0x81fe94, '11'],
  [0x81fe9c, '9a'], [0xd62314, 'e5'],
];
const reference = Buffer.from(rtos);
for (const [offset, hex] of identity) Buffer.from(hex, 'hex').copy(reference, offset);
check(hash(reference) === '0f11b0d28bc67932d044c5d01bc0314844a756057c89984278c73a23449a24c6',
  'GR III and reference RTOS differ beyond the locked identity spans');

const textureRaw = readFileSync(new URL(
  '../.runtime/grlife/reconstruction/firmware_store/templates/urban160-film-texture.json', import.meta.url));
check(hash(textureRaw) === 'cf378eb62fec13d300c7207ef76422dc405e716503f138c70626003191067449',
  'GRLife reference texture template differs');
const texture = JSON.parse(textureRaw);
const textureCode = Buffer.from(texture.code_hex, 'hex');
check(hash(textureCode) === texture.code_sha256, 'GRLife reference texture code differs');
for (const [offset, hex] of [
  [0x2c, '3c0094e5'], [0xcc, 'b291d0e1'], [0xd0, 'b071d0e1'],
  [0xd4, 'b461d0e1'], [0xd8, '048090e5'],
]) check(textureCode.subarray(offset, offset + 4).toString('hex') === hex,
  `reference image descriptor load differs at 0x${offset.toString(16)}`);
check(texture.capture_hook.rtos_offset === captureOffset &&
  texture.capture_hook.expected_hex === '0e9d06eb' &&
  texture.capture_hook.replacement_hex === '9fd22eeb',
'GRLife capture hook reference differs');

const expectedDecodedSize = modified.readUInt32LE(modified.length - 8);
const { decoded } = decodeFrameMap(modified, expectedDecodedSize);
const candidateHook = decoded.readUInt32LE(0x10870 + captureOffset);
check(candidateHook === 0xeb2ed29f, 'modified capture call differs');
const programStart = decoded.indexOf(Buffer.from('00c00fe1000090e5', 'hex'));
check(programStart >= 0 && decoded.lastIndexOf(Buffer.from('00c00fe1000090e5', 'hex')) === programStart,
  'modified program entry is absent or ambiguous');
check(programStart - 0x10870 === 17522688, 'modified program placement differs');
check(decoded.subarray(programStart + 13184, programStart + 13188).toString('hex') === 'b30300eb',
  'modified timestamp capture branch differs');
// The supplied adapter saves the caller state, invokes the timestamp routine,
// restores the state, and tail-jumps into the stock callee. These are exact
// preimages, not proof that the adapter receives a JPEG-only colour buffer.
for (const [offset, word] of [
  [0x336c, 0xe92d5fff], [0x3370, 0xe24dd008], [0x3374, 0xe10fc000],
  [0x3378, 0xe58dc000], [0x3380, 0xeb0003b3], [0x3384, 0xe59dc000],
  [0x3388, 0xe12cf00c], [0x338c, 0xe28dd008], [0x3390, 0xe8bd5fff],
  [0x3394, 0xe51ff004], [0x3398, 0x536abd28],
]) check(decoded.readUInt32LE(programStart + offset) === word,
  `modified capture adapter differs at 0x${offset.toString(16)}`);
check(branchTarget(0x540b9380, decoded.readUInt32LE(programStart + 0x3380)) === 0x540ba254,
  'modified timestamp routine target differs');
check(decoded.subarray(programStart + 20480, programStart + 24576).every((byte) => byte === 0),
  'modified program extension page is not empty');

console.log(JSON.stringify({
  source_sha256: SHA256,
  modified_sha256: hash(modified),
  reference_rtos_identity_equivalent: true,
  reference_identity_bytes: identity.reduce((sum, [, hex]) => sum + hex.length / 2, 0),
  reference_texture_sha256: hash(textureRaw),
  reference_image_descriptor_reads: { context_offset: '0x3c', data_offset: '0x04',
    width_offset: '0x10', height_offset: '0x12', stride_offset: '0x14' },
  capture_call: {
    virtual_address: `0x${captureVA.toString(16)}`,
    stock_bytes: '0e9d06eb', stock_target: `0x${branchTarget(captureVA, originalWord).toString(16)}`,
    modified_bytes: '9fd22eeb', modified_target: `0x${branchTarget(captureVA, candidateHook).toString(16)}`,
  },
  modified_program: {
    decoded_offset: `0x${programStart.toString(16)}`,
    timestamp_branch_bytes: 'b30300eb',
    capture_adapter: { entry: '0x540b936c', timestamp_target: '0x540ba254',
      original_callee_tail_jump: '0x536abd28' },
    empty_extension_offset: '0x5000', empty_extension_bytes: 4096,
  },
  proved: ['exact baseline', 'capture-call preimages', 'RTOS identity equivalence',
    'modified adapter preserves the stock callee', 'modified program placement',
    'unused extension bytes in supplied modified firmware'],
  unresolved: ['capture descriptor semantics', 'JPEG-only condition', 'chroma plane layout',
    'red-channel write and cache synchronization', 'camera update acceptance and recovery'],
}, null, 2));
