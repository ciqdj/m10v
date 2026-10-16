import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { buildNativeLibrary, auditNativeLibrary } from './gr3-m10v-native-build.mjs';
import { decodeFrameMap } from './gr3-frames.mjs';

const source = readFileSync(new URL('../fwdc239b-offical.bin', import.meta.url));

test('M10V native library builds from official bytes without a compatibility runtime and audits every patch', async () => {
  const folder = await mkdtemp(path.join(tmpdir(), 'm10v-native-build-'));
  try {
    const manifest = JSON.parse(execFileSync(new URL('../.venv/bin/python', import.meta.url).pathname,
      ['scripts/build_gr3_m10v_library.py', '--out', folder], {cwd:new URL('..', import.meta.url).pathname}));
    const runtime = await readFile(path.join(folder, 'm10v-library-arm.bin'));
    const result = buildNativeLibrary(source, runtime, manifest);
    assert.deepEqual(result.receipt.changed_sections, ['RTOS']);
    assert.equal(result.receipt.camera_tested, false);
    assert.equal(result.receipt.film_count, 66);
    assert.equal(result.receipt.external_film_pack, false);
    assert.deepEqual(auditNativeLibrary(source, result.candidate, runtime, manifest), result.receipt);
    const decoded = decodeFrameMap(result.candidate, result.candidate.readUInt32LE(result.candidate.length - 8)).decoded;
    assert.ok(decoded.includes(Buffer.from('M10V3A.bin')));
    assert.ok(!runtime.includes(Buffer.from('GRLIFE')));
    const damaged = Buffer.from(result.candidate); damaged[200] ^= 1;
    assert.throws(() => auditNativeLibrary(source, damaged, runtime, manifest));
    const wrongRuntime = Buffer.from(runtime); wrongRuntime[0] ^= 1;
    assert.throws(() => buildNativeLibrary(source, wrongRuntime, manifest), /hash|摘要/);
    const changedSource = Buffer.from(source); changedSource[200] ^= 1;
    assert.throws(() => buildNativeLibrary(changedSource, runtime, manifest));
  } finally { await rm(folder, {recursive:true, force:true}); }
});
