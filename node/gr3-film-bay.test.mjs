import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeCustomization } from './gr3-customization.mjs';
import { createStorePlan } from './gr3-store-plan.mjs';

test('the superseded external film bay cannot be built through either planner', () => {
  const selection = { variant: 'street', features: ['filmbay', 'level'] };
  assert.throws(() => normalizeCustomization(selection), /废弃/);
  assert.throws(() => createStorePlan(selection), /废弃/);
});
