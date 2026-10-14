import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { analyzeUpdatePath } from '../scripts/analyze_gr3_update.mjs';

const original = readFileSync(new URL('../fwdc239b.bin', import.meta.url));

test('update evidence is tied to the exact GR III image and states unresolved links', () => {
  const report = analyzeUpdatePath(original);
  for (const address of ['0x53838cd0', '0x536290c8', '0x53629044'])
    assert.ok(report.gates.some((gate) => gate.address === address));
  assert.ok(report.unresolved.includes('flash_write_callback'));
  assert.ok(report.unresolved.includes('same_version_acceptance'));
  const altered = Buffer.from(original);
  altered[1000] ^= 1;
  assert.throws(() => analyzeUpdatePath(altered));
});
