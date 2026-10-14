// Independent readback of an in-memory candidate. No candidate bytes leave this module.
import { createHash } from 'node:crypto';
import { inspectOfficial, SHA256 } from './firmware.mjs';
import { decodeFrameMap, sum32 } from './gr3-frames.mjs';
import { findCollabo, inspectStreetJpeg } from './gr3-jpeg.mjs';

const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
function check(ok, reason) { if (!ok) throw new Error(reason); }
const rows = [
  ['BOOTPARA', 72], ['DRAMPARA', 556], ['PARTPARA', 516], ['M0', 44640],
  ['BOOT', 21816], ['RTOS', 17520064], ['LINUX', 3062784], ['INITFS', 13899776],
  ['SRIC', 49152], ['CPU', 131072], ['SHELLCMD', 37440], ['ICONBIN', 18354964],
  ['FDRVPARA', 36], ['RES', 6595272],
];

export function verifyCandidate(official, candidate, requestedJpeg) {
  inspectOfficial(official);
  inspectStreetJpeg(requestedJpeg);
  check(Buffer.isBuffer(candidate) && candidate.length >= 152 && candidate.length < 128 * 1024 * 1024,
    'candidate container size differs');
  const footer = candidate.length - 24;
  const encoded = candidate.readUInt32LE(footer + 12);
  check(candidate.readUInt32LE(48) === 588 && candidate.readUInt32LE(120) === 0x024c024c &&
    candidate.readUInt32LE(124) === 0xa55a5aa5 &&
    candidate.readUInt32LE(footer) === 0x024c024c &&
    candidate.readUInt32LE(footer + 4) === 0xa55a5aa5 &&
    candidate.readUInt32LE(footer + 8) === 2 &&
    candidate.readUInt32LE(footer + 16) === 59718388 &&
    128 + encoded <= footer && ((128 + encoded + 3) & ~3) === footer &&
    candidate.subarray(0, 128).equals(official.subarray(0, 128)),
  'candidate outer fields or header differ');
  check(sum32(candidate) === 0, 'candidate outer checksum differs');
  const fresh = decodeFrameMap(candidate);
  const source = decodeFrameMap(official);
  const decoded = fresh.decoded;
  check(sum32(decoded) === 0, 'candidate decoded checksum differs');
  let position = 0;
  const boundaries = [];
  for (const [name, size] of rows) {
    check(position + 16 + size <= decoded.length - 4, 'candidate section exceeds decoded stream');
    const actual = decoded.toString('ascii', position, position + 8).split('\0')[0];
    check(actual === name && decoded.subarray(position, position + 16)
      .equals(source.decoded.subarray(position, position + 16)), 'candidate section header differs');
    boundaries.push({ name, start: position, end: position + 16 + size });
    position += 16 + size;
  }
  check(position + 4 === decoded.length, 'candidate section tail differs');
  const record = findCollabo(source.decoded);
  const reread = findCollabo(decoded);
  check(record.start === reread.start && record.end === reread.end &&
    decoded.subarray(record.start, record.end).equals(requestedJpeg),
  'candidate JPEG readback differs');
  let differences = 0;
  let first = -1;
  let last = -1;
  for (let i = 0; i < decoded.length - 4; i++) {
    if (decoded[i] === source.decoded[i]) continue;
    check(i >= record.start && i < record.end, 'candidate modifies a second resource or executable byte');
    if (first < 0) first = i;
    last = i;
    differences++;
  }
  for (const [offset, size] of [[0x38, 4], [0x50, 4]])
    check(candidate.subarray(offset, offset + size).equals(official.subarray(offset, offset + size)),
      'outer version differs');
  const rtos = boundaries.find((row) => row.name === 'RTOS');
  const cpu = boundaries.find((row) => row.name === 'CPU');
  for (const at of [rtos.start + 16 + 0x2038, cpu.start + 16 + 0x90])
    check(decoded.readUInt32BE(at) === 0x020a151b, 'internal version differs');
  let cpuSum = 0;
  for (let at = cpu.start + 16; at < cpu.end; at += 4)
    cpuSum = (cpuSum + decoded.readUInt32BE(at)) >>> 0;
  check(cpuSum === 0, 'CPU checksum differs');
  return {
    status: 'candidate_offline_verified', source_sha256: SHA256,
    candidate_sha256: hash(candidate), candidate_bytes: candidate.length,
    versions: { outer_cpu: '2.10.21.27', outer_dsp: '2.10.21.27',
      rtos: '2.10.21.27', cpu: '2.10.21.27' },
    changed_logical_bytes: differences,
    changed_logical_range: differences ? [first, last + 1] : null,
    section_count: boundaries.length, frame_count: fresh.frames.length,
    checks: { outer_sum32: 0, decoded_sum32: 0, cpu_sum32_be: 0,
      jpeg_readback: true, non_target_unchanged: true },
    blockers: ['camera_same_version_acceptance_unverified',
      'modified_package_acceptance_unverified', 'camera_jpeg_decoder_unverified',
      'hardware_recovery_not_verified'],
    candidate_export_allowed: false, candidate_sd_allowed: false,
  };
}
