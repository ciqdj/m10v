import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { inspect800TEvidence } from './gr3-800t-evidence.mjs';
const sample = new URL('../fwdc239b.bin', import.meta.url);
test('800T rejects unsupported firmware before reporting evidence', () => {
  assert.throws(() => inspect800TEvidence(Buffer.alloc(152)), /unsupported/);
});
test('800T validates exact capture contract without claiming camera testing',
  { skip: !existsSync(sample) }, () => {
    const report = inspect800TEvidence(readFileSync(sample));
    assert.equal(report.firmwareReady, true);
    assert.equal(report.cameraTested,false);
    assert.equal(report.descriptor.format422, 1);
    assert.equal(report.descriptor.format420, 2);
    assert.equal(report.descriptor.chroma, 8);
    assert.equal(report.jpegType, '22JpegEncodeMacroProcess');
    assert.deepEqual(report.unresolved,[]);
    assert.equal(report.descriptor.chromaOrder,'CbCr');
    assert.equal(report.descriptor.neutral,128);
    assert.deepEqual(report.supportedRecipeModes,[0,1,5,6,7,8,12]);
    assert.ok(report.anchors.some((row) => row.address === '0x535048e8'));
    assert.ok(report.anchors.every((row) => row.verified));
    report.supportedRecipeModes.push(99);
    assert.equal(inspect800TEvidence(readFileSync(sample)).supportedRecipeModes.includes(99),false);
  });
test('800T refuses a changed official capture instruction', { skip: !existsSync(sample) }, () => {
  const bytes = readFileSync(sample); bytes[1000] ^= 1;
  assert.throws(() => inspect800TEvidence(bytes), /SHA-256/);
});
