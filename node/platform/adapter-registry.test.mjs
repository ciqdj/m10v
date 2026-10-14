import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createRegistry, NO_MATCH } from './adapter-registry.mjs';
import { createGr3Adapter } from '../adapters/gr3/index.mjs';
import { createGr4Adapter } from '../adapters/gr4/index.mjs';
import { gr2Descriptor } from '../adapters/gr2/index.mjs';

const sample = fileURLToPath(new URL('../../fwdc239b.bin', import.meta.url));

function adapter(id, detect) {
  return {
    schema_version: 1, id, model: id.toUpperCase(), evidence: 'test',
    detect, inspect: detect, capabilities: () => ({}), createDraft: () => ({}),
    validateDraft: (value) => value, previewCrop: () => ({}),
    prepareShutdownAsset: () => ({}), build: async () => ({}),
    verify: async () => ({}), rollback: async () => ({}),
    outputFilename: () => `${id}.bin`,
  };
}

test('registry selects the exact GR III adapter and exposes the multi-model catalog', () => {
  const registry = createRegistry([createGr3Adapter(), createGr4Adapter(), gr2Descriptor]);
  const result = registry.detect(readFileSync(sample));
  assert.equal(result.adapter.id, 'gr3');
  assert.equal(result.inspection.model, 'GR III');
  assert.deepEqual(registry.list().map(({ id, supported }) => [id, supported]),
    [['gr3', true], ['gr4', true], ['gr2', false]]);
});

test('GR IV adapter exposes reference features and strict draft/version policy', async () => {
  const adapter = createGr4Adapter();
  assert.equal(adapter.capabilities().shutdown.max_items, 16);
  assert.equal(adapter.capabilities().build.hardware, 'not_tested');
  const draft = adapter.createDraft();
  assert.equal(adapter.validateDraft(draft), draft);
  assert.equal((await adapter.allocateVersion('1.11.10.7')).version, '1.11.10.10');
  assert.throws(() => adapter.validateDraft({ ...draft, shutdown: {
    schema_version: 1, assets: [], items: [{ fit: 'stretch' }] } }), /shutdown fit/);
});

test('registry rejects unsupported, ambiguous, corrupt and duplicate adapters', () => {
  const never = adapter('never', () => { throw NO_MATCH; });
  assert.throws(() => createRegistry([never]).detect(Buffer.from('unknown')), /unsupported firmware/);

  const yes = (id) => adapter(id, () => ({ model: id }));
  assert.throws(() => createRegistry([yes('a1'), yes('b1')]).detect(Buffer.alloc(8)),
    /ambiguous firmware/);

  const corrupt = adapter('broken', () => { throw new Error('damaged structure'); });
  assert.throws(() => createRegistry([corrupt, never]).detect(Buffer.alloc(8)),
    /broken: damaged structure/);
  assert.throws(() => createRegistry([yes('same'), yes('same')]), /duplicate adapter id/);
});

test('adapter validation rejects malformed contracts', () => {
  assert.throws(() => createRegistry([{ schema_version: 2, id: 'bad' }]),
    /adapter schema/);
  assert.throws(() => createRegistry([adapter('BAD ID', () => ({ model: 'bad' }))]),
    /adapter id/);
});
