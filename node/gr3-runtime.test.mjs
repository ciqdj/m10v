import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { createStorePlan } from './gr3-store-plan.mjs';
import { runGr3Runtime } from './gr3-runtime.mjs';

const fixture = new URL('../fwdc239b.bin', import.meta.url);
const golden = new URL('../fwdc239b-modify.bin', import.meta.url);
const runtime = process.env.GRLIFE_CORE_PATH || new URL('../.runtime/grlife-current', import.meta.url).pathname;
const available = await Promise.all([fixture, golden,
  `${runtime}/reconstruction/firmware_store/browser_engine.py`]
  .map((file) => access(file).then(() => true, () => false)));
const params = (values) => Object.fromEntries(['saturation', 'hue', 'high_low_key', 'contrast',
  'highlight_contrast', 'shadow_contrast', 'sharpness', 'shading', 'clarity']
  .map((field, index) => [field, values[index]]));

test('compatibility runtime reproduces the supplied GRLife firmware byte for byte',
  { skip: !available.every(Boolean) }, async () => {
    const source = await readFile(fixture);
    const plan = createStorePlan({ variant: 'street',
      features: ['recipes', 'timestamp', 'aspect', 'film', 'level'],
      recipes: [
        { slotId: 'custom1', cameraName: 'Leica', baseEffect: 'Standard', iconMode: 'original',
          source: 'community_reference', id: 'cookbook_photo-stuff-leica-look',
          parameters: params([2, 0, -2, 1, 1, 1, 1, -1, 2]) },
        { slotId: 'custom2', cameraName: 'Koda', baseEffect: 'Standard', iconMode: 'original',
          source: 'community_reference', id: 'cookbook_kodakolor',
          parameters: params([-4, 4, 1, 4, -4, 3, 1, 2, 2]) },
      ] });
    const prepared = await runGr3Runtime(source, plan, 'prepare', runtime);
    assert.equal(prepared.receipt.ready, true);
    const built = await runGr3Runtime(source, plan, 'build', runtime);
    assert.deepEqual(built.candidate, await readFile(golden));
    assert.equal(built.receipt.camera_tested, false);
  });
