import test from 'node:test';
import assert from 'node:assert/strict';
import { createStorePlan } from './gr3-store-plan.mjs';

const params = { saturation: 2, hue: 0, high_low_key: -2, contrast: 1,
  highlight_contrast: 1, shadow_contrast: 1, sharpness: 1, shading: -1, clarity: 2 };

test('builds the exact five-feature plan represented by the supplied GRLife firmware', () => {
  const plan = createStorePlan({ variant: 'street', features: ['recipes', 'timestamp', 'aspect', 'film', 'level'],
    recipes: [{ slotId: 'custom1', cameraName: 'Leica', baseEffect: 'Standard',
      parameters: params, iconMode: 'original', source: 'community_reference',
      id: 'cookbook_photo-stuff-leica-look' }] });
  assert.equal(plan.schema, 'grlife-firmware-customization-plan/v1');
  assert.deepEqual(plan.features.map(({ id }) => id), ['recipes', 'timestamp', 'aspect', 'film', 'level']);
  assert.deepEqual(plan.features[0].configuration.items[0].parameters, params);
  assert.equal(plan.features[3].configuration.bundle, 'films-v10');
});

test('film and Cross Processing recipe cannot occupy the same slot', () => {
  assert.throws(() => createStorePlan({ variant: 'street', features: ['recipes', 'film'],
    recipes: [{ slotId: 'builtin-15', cameraName: 'Cross', baseEffect: 'Cross Processing',
      parameters: params, iconMode: 'original', source: 'manual' }] }), /Cross Processing/);
});

test('retired SD film bay is not a valid store plan', () => {
  assert.throws(()=>createStorePlan({variant:'street',features:['filmbay','aspect','level']}),/废弃|不可用/);
});
