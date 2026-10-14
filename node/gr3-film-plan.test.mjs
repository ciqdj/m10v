import test from 'node:test';
import assert from 'node:assert/strict';
import { createFilmPlan } from './gr3-film-plan.mjs';

const defaults = ['ektar100', 'gold200', 'pro400h', 'portra400', 'vision3-250d'];

test('the five original catalog choices use the unmodified fixed film bundle', () => {
  assert.deepEqual(createFilmPlan(defaults), { bundle: 'films-v10' });
});

test('a catalog replacement moves through a valid slot and writes its real tables', () => {
  const plan = createFilmPlan([...defaults.slice(0, 4), 'hb-hncs']);
  assert.equal(plan.custom.length, 1);
  assert.equal(plan.custom[0].mode, 'bleach');
  assert.equal(plan.custom[0].name, 'HB HNCS');
  assert.equal(plan.custom[0].knots.length, 3);
  assert.equal(plan.custom[0].iconPixelsBase64.length, 8536);
});

test('exactly five unique films must fit the camera name fields', () => {
  assert.throws(() => createFilmPlan(defaults.slice(0, 4)), /five films/);
  assert.throws(() => createFilmPlan([...defaults.slice(0, 4), defaults[0]]), /unique/);
  assert.throws(() => createFilmPlan(['ektar100', 'portra400', 'vision3-250d', 'hb-portrait', 'hb-lowsat']), /8 characters/);
});

test('a fitted user LUT can replace a catalog film with its own camera tables', () => {
  const sample = createFilmPlan([...defaults.slice(0, 4), 'hb-hncs']).custom[0];
  const lut = { ...sample, id: 'lut-demo', name: 'My LUT', home: null,
    curves: Array.from({ length: 3 }, () => Array.from({ length: 256 }, (_, index) => index * 32)),
    knots: sample.knots };
  const plan = createFilmPlan([...defaults.slice(0, 4), lut.id], [lut]);
  assert.equal(plan.custom[0].name, 'My LUT');
  assert.deepEqual(plan.custom[0].knots, lut.knots);
});
