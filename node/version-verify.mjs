import { createHash } from 'node:crypto';
import { inspectOfficial, SHA256 } from './firmware.mjs';
import { decodeFrameMap, sum32 } from './gr3-frames.mjs';

const SOURCE_WORD = 0x020a151b;
const TARGET_WORD = 0x020a151c;
const VERSION = '2.10.21.28';
const sizes = [72, 556, 516, 44640, 21816, 17520064, 3062784,
  13899776, 49152, 131072, 37440, 18354964, 36, 6595272];
const names = ['BOOTPARA', 'DRAMPARA', 'PARTPARA', 'M0', 'BOOT', 'RTOS',
  'LINUX', 'INITFS', 'SRIC', 'CPU', 'SHELLCMD', 'ICONBIN', 'FDRVPARA', 'RES'];
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const check = (condition, reason) => { if (!condition) throw new Error(reason); };

function payloadStart(index) {
  return sizes.slice(0, index).reduce((offset, size) => offset + 16 + size, 0) + 16;
}

function cpuSum(decoded, start) {
  let value = 0;
  for (let offset = start; offset < start + sizes[9]; offset += 4)
    value = (value + decoded.readUInt32BE(offset)) >>> 0;
  return value;
}

function within(offset, ranges) {
  return ranges.some(([start, length]) => offset >= start && offset < start + length);
}

export function verifyVersionProbe(official, candidate, targetWord = TARGET_WORD) {
  inspectOfficial(official);
  check(targetWord === TARGET_WORD, 'target version is not the exact supported successor');
  check(Buffer.isBuffer(candidate) && candidate.length >= 152 && candidate.length < 128 * 1024 * 1024,
    'candidate container size differs');
  check(sum32(candidate) === 0, 'candidate container checksum differs');
  const footer = candidate.length - 24;
  const encodedSize = candidate.readUInt32LE(footer + 12);
  check(candidate.readUInt32LE(48) === 588 && candidate.readUInt32LE(120) === 0x024c024c &&
    candidate.readUInt32LE(124) === 0xa55a5aa5 &&
    candidate.readUInt32LE(footer) === 0x024c024c &&
    candidate.readUInt32LE(footer + 4) === 0xa55a5aa5 &&
    candidate.readUInt32LE(footer + 8) === 2 &&
    candidate.readUInt32LE(footer + 16) === 59718388 &&
    ((128 + encodedSize + 3) & ~3) === footer,
  'candidate outer structure differs');
  for (let offset = 0; offset < 128; offset++) {
    if (within(offset, [[0x38, 4], [0x50, 4]])) continue;
    check(candidate[offset] === official[offset], 'candidate outer header has a non-target diff');
  }
  check(candidate.subarray(128 + encodedSize, footer).every((byte) => byte === 0),
    'candidate container padding differs');

  const source = decodeFrameMap(official).decoded;
  const fresh = decodeFrameMap(candidate);
  const decoded = fresh.decoded;
  check(sum32(decoded) === 0, 'candidate decoded checksum differs');
  let position = 0;
  for (let index = 0; index < sizes.length; index++) {
    const headerEnd = position + 16;
    const end = headerEnd + sizes[index];
    check(end <= decoded.length - 4 &&
      decoded.toString('ascii', position, position + 8).split('\0')[0] === names[index] &&
      decoded.subarray(position, headerEnd).equals(source.subarray(position, headerEnd)),
    `candidate section boundary differs at ${names[index]}`);
    position = end;
  }
  check(position + 4 === decoded.length, 'candidate decoded layout differs');

  const rtosVersion = payloadStart(5) + 0x2038;
  const cpuStart = payloadStart(9);
  const cpuChecksum = cpuStart + 0x7c;
  const cpuVersion = cpuStart + 0x90;
  check(official.readUInt32BE(0x38) === SOURCE_WORD && official.readUInt32BE(0x50) === SOURCE_WORD &&
    source.readUInt32BE(rtosVersion) === SOURCE_WORD && source.readUInt32BE(cpuVersion) === SOURCE_WORD,
  'source version differs');
  check(candidate.readUInt32BE(0x38) === targetWord && candidate.readUInt32BE(0x50) === targetWord &&
    decoded.readUInt32BE(rtosVersion) === targetWord && decoded.readUInt32BE(cpuVersion) === targetWord,
  'candidate version readback differs');
  check(cpuSum(decoded, cpuStart) === 0, 'candidate CPU checksum differs');

  const allowed = [[rtosVersion, 4], [cpuChecksum, 4], [cpuVersion, 4], [decoded.length - 4, 4]];
  let changed = 0;
  for (let offset = 0; offset < decoded.length; offset++) {
    if (decoded[offset] === source[offset]) continue;
    check(within(offset, allowed), 'candidate contains a non-target logical diff');
    changed++;
  }
  check(changed > 0, 'candidate has no version diff');
  return {
    status: 'version_probe_offline_verified', strategy: 'same_version_first',
    source_sha256: SHA256, candidate_sha256: hash(candidate),
    source_version: '2.10.21.27', probe_version: VERSION,
    versions: { outer_cpu: VERSION, outer_dsp: VERSION, rtos: VERSION, cpu: VERSION },
    candidate_size: candidate.length, frame_count: fresh.frames.length,
    changed_logical_bytes: changed,
    changed_logical_ranges: [
      ['RTOS', 0x2038, 4], ['CPU', 0x7c, 4], ['CPU', 0x90, 4],
      ['DECODED_TRAILER', decoded.length - 4, 4],
    ],
    checks: { outer_sum32: 0, decoded_sum32: 0, cpu_sum32_be: 0,
      fresh_decode_exact: true, non_target_unchanged: true },
    blockers: ['same_version_rejection_evidence_missing',
      'modified_package_acceptance_unverified', 'hardware_recovery_not_verified'],
    candidate_export_allowed: false, candidate_sd_allowed: false,
  };
}

