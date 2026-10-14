import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { auditGr3Candidate } from './gr3-candidate-audit.mjs';
import { decodeFrameMap, sum32 } from './gr3-frames.mjs';
import { inspectOfficial } from './firmware.mjs';
import { localFilmPublicKey } from './gr3-local-film-pack.mjs';

export const filmBayPublicKeyOffset = 27300;
export const grlifeFilmPublicKey = Buffer.from(
  '5a7ed3a89db0592b0412b4b980d70cfb22f385d58bd390a714e815380e5cf12a', 'hex');
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');

function rtosStart(decoded, sections) {
  let at = 0;
  for (const row of sections) {
    if (row.name === 'RTOS') return at + 16;
    at += row.size;
  }
  throw new Error('RTOS 分区缺失。');
}

function packCandidate(base, decoded, frames) {
  const previous = decodeFrameMap(base, decoded.length).decoded;
  const chunks = [];
  for (const frame of frames) {
    const desired = decoded.subarray(frame.decoded_start, frame.decoded_end);
    if (desired.equals(previous.subarray(frame.decoded_start, frame.decoded_end))) {
      chunks.push(base.subarray(128 + frame.encoded_start, 128 + frame.encoded_end));
    } else {
      for (let at = 0; at < desired.length; at += 0x6000) {
        const part = desired.subarray(at, at + 0x6000);
        const prefix = Buffer.alloc(2);
        prefix.writeUInt16BE(0x8000 | part.length);
        chunks.push(prefix, part);
      }
    }
  }
  chunks.push(Buffer.alloc(2));
  const payload = Buffer.concat(chunks);
  const footer = Buffer.from(base.subarray(-24));
  footer.writeUInt32LE(payload.length, 12);
  footer.writeUInt32LE(0, 20);
  const candidate = Buffer.concat([base.subarray(0, 128), payload,
    Buffer.alloc(-(128 + payload.length) & 3), footer]);
  candidate.writeUInt32LE(-sum32(candidate) >>> 0, candidate.length - 4);
  if (sum32(candidate) !== 0 || !decodeFrameMap(candidate, decoded.length).decoded.equals(decoded))
    throw new Error('胶片库公钥补丁的固件回读不一致。');
  return candidate;
}

export function patchLocalFilmBayKey(source, candidate) {
  const official = inspectOfficial(source);
  auditGr3Candidate(source, candidate);
  const manifest = readFileSync(new URL(
    '../.runtime/grlife-current/reconstruction/firmware_store/templates/urban160-film-bay.json',
    import.meta.url));
  if (sha(manifest) !== '5897d30d64191a032275eddf0c8b97acb0f059bc08fa319480eacf05d65dd14b')
    throw new Error('胶片库模板摘要不匹配。');
  const bay = JSON.parse(manifest);
  const decodedSize = candidate.readUInt32LE(candidate.length - 8);
  const { decoded, frames } = decodeFrameMap(candidate, decodedSize);
  const at = rtosStart(decoded, official.sections) + bay.base_va + bay.program_offset - 0x53000000 +
    filmBayPublicKeyOffset;
  if (!decoded.subarray(at, at + 32).equals(grlifeFilmPublicKey))
    throw new Error('胶片库原公钥前像不匹配。');
  const target = Buffer.from(decoded);
  localFilmPublicKey.copy(target, at);
  target.writeUInt32LE(0, target.length - 4);
  target.writeUInt32LE(-sum32(target) >>> 0, target.length - 4);
  const patched = packCandidate(candidate, target, frames);
  auditGr3Candidate(source, patched);
  return patched;
}
