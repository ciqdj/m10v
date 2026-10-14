import { inspectOfficial } from './firmware.mjs';
import { decodeFrameMap, repackWithTarget, sum32 } from './gr3-frames.mjs';
import { verifyVersionProbe } from './version-verify.mjs';

const SOURCE_WORD = 0x020a151b;
const TARGET_WORD = 0x020a151c;
const TARGET_VERSION = '2.10.21.28';
const sizes = [72, 556, 516, 44640, 21816, 17520064, 3062784,
  13899776, 49152, 131072, 37440, 18354964, 36, 6595272];
const RTOS_INDEX = 5;
const CPU_INDEX = 9;
const check = (condition, reason) => { if (!condition) throw new Error(reason); };

function payloadStart(index) {
  return sizes.slice(0, index).reduce((offset, size) => offset + 16 + size, 0) + 16;
}

function parseExactSuccessor(target) {
  check(typeof target === 'string' && /^\d+\.\d+\.\d+\.\d+$/.test(target),
    'version must be the exact successor 2.10.21.28');
  const parts = target.split('.').map(Number);
  check(parts.every((value) => Number.isInteger(value) && value >= 0 && value <= 255) &&
    target === TARGET_VERSION, 'version must be the exact successor 2.10.21.28');
  return TARGET_WORD;
}

function repairDecoded(bytes) {
  let value = 0;
  for (let offset = 0; offset < bytes.length - 4; offset += 4)
    value = (value + bytes.readUInt32LE(offset)) >>> 0;
  bytes.writeUInt32LE(-value >>> 0, bytes.length - 4);
}

function repairCpu(decoded, cpuStart) {
  const checksum = cpuStart + 0x7c;
  decoded.writeUInt32BE(0, checksum);
  let value = 0;
  for (let offset = cpuStart; offset < cpuStart + sizes[CPU_INDEX]; offset += 4)
    value = (value + decoded.readUInt32BE(offset)) >>> 0;
  decoded.writeUInt32BE(-value >>> 0, checksum);
}

function cpuSum(decoded, cpuStart) {
  let value = 0;
  for (let offset = cpuStart; offset < cpuStart + sizes[CPU_INDEX]; offset += 4)
    value = (value + decoded.readUInt32BE(offset)) >>> 0;
  return value;
}

function buildVersionProbe(official, targetWord) {
  inspectOfficial(official);
  check(targetWord === TARGET_WORD, 'version must be the exact successor 2.10.21.28');
  const source = decodeFrameMap(official);
  const targetDecoded = Buffer.from(source.decoded);
  const rtosVersion = payloadStart(RTOS_INDEX) + 0x2038;
  const cpuStart = payloadStart(CPU_INDEX);
  const cpuVersion = cpuStart + 0x90;
  check(targetDecoded.readUInt32BE(rtosVersion) === SOURCE_WORD &&
    targetDecoded.readUInt32BE(cpuVersion) === SOURCE_WORD &&
    official.readUInt32BE(0x38) === SOURCE_WORD && official.readUInt32BE(0x50) === SOURCE_WORD,
  'source version differs from exact GR III baseline');
  targetDecoded.writeUInt32BE(targetWord, rtosVersion);
  targetDecoded.writeUInt32BE(targetWord, cpuVersion);
  repairCpu(targetDecoded, cpuStart);
  repairDecoded(targetDecoded);
  const replay = repackWithTarget(official, targetDecoded);
  const candidate = Buffer.from(replay.candidate);
  candidate.writeUInt32BE(targetWord, 0x38);
  candidate.writeUInt32BE(targetWord, 0x50);
  candidate.writeUInt32LE(0, candidate.length - 4);
  candidate.writeUInt32LE(-sum32(candidate) >>> 0, candidate.length - 4);
  check(sum32(candidate) === 0 && sum32(targetDecoded) === 0 && cpuSum(targetDecoded, cpuStart) === 0,
    'version probe checksum repair failed');
  return { candidate, targetDecoded, replay, rtosVersion, cpuVersion, cpuStart };
}

export function analyzeVersionProbe(official, target = TARGET_VERSION) {
  const targetWord = parseExactSuccessor(target);
  const built = buildVersionProbe(official, targetWord);
  const report = verifyVersionProbe(official, built.candidate, targetWord);
  return { ...report, reused_frames: built.replay.reused_frames,
    replaced_frames: built.replay.replaced_frames };
}

