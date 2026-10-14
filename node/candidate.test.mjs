import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { decodeFrameMap } from './gr3-frames.mjs';
import { findCollabo } from './gr3-jpeg.mjs';
import { analyzeStreetCandidate, buildStreetCandidate } from './candidate.mjs';

test('candidate analysis returns a report without exposing firmware bytes', () => {
  const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));
  const decoded = decodeFrameMap(original).decoded;
  const { start, end } = findCollabo(decoded);
  const report = analyzeStreetCandidate(original, decoded.subarray(start, end));
  assert.equal(report.status, 'candidate_offline_verified');
  assert.equal(report.source_sha256, report.candidate_sha256);
  assert.equal(report.candidate, undefined);
  assert.equal(report.bytes, undefined);
  const modified = Buffer.from(decoded.subarray(start, end));
  const at = modified.findIndex((byte, index) => index > 10_000 && index < modified.length - 100 &&
    byte !== 0xff && modified[index - 1] !== 0xff && byte !== 0x00);
  assert.ok(at > 0);
  modified[at] ^= 1;
  const changed = analyzeStreetCandidate(original, modified);
  assert.equal(changed.status, 'candidate_offline_verified');
  assert.notEqual(changed.candidate_sha256, report.candidate_sha256);
  assert.ok(changed.replaced_frames > 0);
  assert.ok(changed.changed_logical_bytes >= 1);
});

test('verified GR III shutdown modification exports a same-version firmware package', () => {
  const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));
  const decoded = decodeFrameMap(original).decoded;
  const { start, end } = findCollabo(decoded);
  const jpeg = Buffer.from(decoded.subarray(start, end));
  const at = jpeg.findIndex((byte, index) => index > 10_000 && index < jpeg.length - 100 &&
    byte !== 0xff && jpeg[index - 1] !== 0xff && byte !== 0x00);
  jpeg[at] ^= 1;
  const result = buildStreetCandidate(original, jpeg);
  assert.equal(result.report.status, 'candidate_offline_verified');
  assert.equal(result.report.candidate_export_allowed, true);
  assert.equal(result.candidate.length, result.report.candidate_bytes);
  assert.notEqual(result.report.source_sha256, result.report.candidate_sha256);
  assert.equal(result.candidate.readUInt32BE(0x38), original.readUInt32BE(0x38));
  assert.equal(result.candidate.readUInt32BE(0x50), original.readUInt32BE(0x50));
});
