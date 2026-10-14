import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { previewFilmPixels } from '../web/gr3/film-preview.mjs';

test('the five default catalog looks match the user-supplied firmware tables and icons', async () => {
  const extracted = JSON.parse(await readFile(new URL('../web/gr3/film-data.json', import.meta.url))).looks;
  const catalog = JSON.parse(await readFile(new URL('../web/gr3/film-catalog.json', import.meta.url))).looks;
  for (const look of extracted) {
    const item = catalog.find((entry) => entry.name === look.name);
    assert.ok(item, look.name);
    for (const key of ['iconPixelsBase64', 'matrixQ13', 'postQ512', 'curves', 'knots'])
      if (look[key] !== undefined) assert.deepEqual(item[key], look[key], `${look.name} ${key}`);
  }
});

test('preview uses extracted film tables to change color while preserving alpha', async () => {
  const data = JSON.parse(await readFile(new URL('../web/gr3/film-data.json', import.meta.url)));
  const original = Uint8ClampedArray.from([210, 72, 45, 153, 40, 130, 220, 255]);
  const transformed = previewFilmPixels(original, data.looks[0]);
  assert.equal(transformed.length, original.length);
  assert.equal(transformed[3], 153);
  assert.equal(transformed[7], 255);
  assert.notDeepEqual(Array.from(transformed.slice(0, 3)), Array.from(original.slice(0, 3)));
  assert.deepEqual(Array.from(original), [210, 72, 45, 153, 40, 130, 220, 255]);
});

test('fast preview matches the original table calculation over the full color range sample', async () => {
  const looks = JSON.parse(await readFile(new URL('../web/gr3/film-data.json', import.meta.url))).looks;
  const source = new Uint8ClampedArray(4096 * 4);
  for (let i = 0; i < source.length; i++) source[i] = (i * 73 + Math.floor(i / 4) * 91) & 255;
  function original(input, look) {
    const out = new Uint8ClampedArray(input.length);
    const mat = (values, coefficients, unit) => [0, 1, 2].map(row => values.reduce(
      (sum, value, column) => sum + value * coefficients[row * 3 + column] / unit, 0));
    const tone = (table, value) => {
      const index = Math.min(255, Math.max(0, value));
      const pos = table.length === 256 ? index : index * 32 / 255;
      const left = Math.floor(pos);
      const right = Math.min(table.length - 1, left + 1);
      return (table[left] + (table[right] - table[left]) * (pos - left)) * 255 / 16383;
    };
    for (let i = 0; i < input.length; i += 4) {
      const values = mat([input[i], input[i + 1], input[i + 2]], look.matrixQ13, 8192);
      const curves = look.curves || look.knots;
      const curved = values.map((value, channel) => tone(curves[channel], value));
      const post = mat(curved, look.postQ512, 512);
      for (let channel = 0; channel < 3; channel++) out[i + channel] = Math.min(255, Math.max(0, Math.round(post[channel])));
      out[i + 3] = input[i + 3];
    }
    return out;
  }
  for (const look of looks) assert.deepEqual(previewFilmPixels(source, look), original(source, look), look.name);
});
