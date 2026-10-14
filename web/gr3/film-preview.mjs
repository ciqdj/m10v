// Browser approximation from the film tables read from the supplied firmware.
const clamp = (value) => Math.min(255, Math.max(0, Math.round(value)));

function tone(table, value) {
  const index = Math.min(255, Math.max(0, value));
  if (table.length === 256) {
    const left = Math.floor(index);
    return (table[left] + (table[Math.min(255, left + 1)] - table[left]) * (index - left)) * 255 / 16383;
  }
  const position = index * 32 / 255;
  const left = Math.floor(position);
  return (table[left] + (table[Math.min(32, left + 1)] - table[left]) *
    (position - left)) * 255 / 16383;
}

export function previewFilmPixels(source, look) {
  const output = new Uint8ClampedArray(source.length);
  const tables = look.curves || look.knots;
  const first = tables[0], second = tables[1], third = tables[2];
  const m = look.matrixQ13, p = look.postQ512;
  for (let index = 0; index < source.length; index += 4) {
    const r = source[index], g = source[index + 1], b = source[index + 2];
    const cr = tone(first, (r * m[0] + g * m[1] + b * m[2]) / 8192);
    const cg = tone(second, (r * m[3] + g * m[4] + b * m[5]) / 8192);
    const cb = tone(third, (r * m[6] + g * m[7] + b * m[8]) / 8192);
    output[index] = clamp((cr * p[0] + cg * p[1] + cb * p[2]) / 512);
    output[index + 1] = clamp((cr * p[3] + cg * p[4] + cb * p[5]) / 512);
    output[index + 2] = clamp((cr * p[6] + cg * p[7] + cb * p[8]) / 512);
    output[index + 3] = source[index + 3];
  }
  return output;
}
