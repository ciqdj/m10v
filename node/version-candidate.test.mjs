import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { analyzeVersionProbe } from './version-candidate.mjs';

const official = readFileSync(new URL('../fwdc239b.bin', import.meta.url));

test('exact next internal version produces a report-only offline probe', () => {
  const report = analyzeVersionProbe(official);
  assert.equal(report.status, 'version_probe_offline_verified');
  assert.equal(report.strategy, 'same_version_first');
  assert.equal(report.source_version, '2.10.21.27');
  assert.equal(report.probe_version, '2.10.21.28');
  assert.deepEqual(report.versions, {
    outer_cpu: '2.10.21.28', outer_dsp: '2.10.21.28',
    rtos: '2.10.21.28', cpu: '2.10.21.28',
  });
  assert.equal(report.checks.outer_sum32, 0);
  assert.equal(report.checks.decoded_sum32, 0);
  assert.equal(report.checks.cpu_sum32_be, 0);
  assert.equal(report.candidate_export_allowed, false);
  assert.equal(report.candidate_sd_allowed, false);
  assert.ok(report.reused_frames > 0);
  assert.ok(report.replaced_frames > 0);
  assert.doesNotMatch(JSON.stringify(report), /"(?:candidate|bytes|buffer|data)"\s*:/i);
});

test('version probe rejects every target except the exact family successor', () => {
  for (const target of [
    '2.10.21.27', '2.10.21.26', '2.10.21.29', '2.10.22.28',
    '2.11.21.28', '3.10.21.28', '2.10.21.256', '2.10.21', '', null,
  ]) assert.throws(() => analyzeVersionProbe(official, target), /exact successor|version/i);
});

