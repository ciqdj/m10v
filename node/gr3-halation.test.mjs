import test from 'node:test';
import assert from 'node:assert/strict';
import { apply800THalation } from '../web/gr3/halation.mjs';

test('isolated bright pixel adds red halo to neighboring dark pixels without changing its core', () => {
  const width = 21;
  const pixels = new Uint8ClampedArray(width * width * 4);
  for (let i = 3; i < pixels.length; i += 4) pixels[i] = 255;
  const center = ((10 * width) + 10) * 4;
  pixels.fill(255, center, center + 3);
  const result = apply800THalation(pixels, width, width, { threshold: 0.7, radius: 3, strength: 1 });
  const neighbor = ((10 * width) + 12) * 4;
  assert.ok(result[neighbor] > result[neighbor + 1]);
  assert.ok(result[neighbor] > result[neighbor + 2]);
  assert.equal(result[center], 255);
  assert.equal(result[center + 1], 255);
  assert.equal(result[center + 2], 255);
});

test('uniform light has no halo and strength zero preserves the source', () => {
  const pixels = new Uint8ClampedArray(9 * 9 * 4).fill(255);
  assert.deepEqual(apply800THalation(pixels, 9, 9), pixels);
  pixels[0] = 0;
  assert.deepEqual(apply800THalation(pixels, 9, 9, { strength: 0 }), pixels);
});

test('rejects invalid image and parameter ranges', () => {
  assert.throws(() => apply800THalation(new Uint8ClampedArray(4), 2, 1), RangeError);
  assert.throws(() => apply800THalation(new Uint8ClampedArray(4), 1, 1, { radius: 0 }), RangeError);
});
