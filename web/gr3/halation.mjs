const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function blur(input, width, height, radius) {
  const horizontal = new Float32Array(input.length);
  const output = new Float32Array(input.length);
  for (let y = 0; y < height; y++) {
    let sum = 0;
    for (let x = 0; x <= Math.min(radius, width - 1); x++) sum += input[y * width + x];
    for (let x = 0; x < width; x++) {
      horizontal[y * width + x] = sum / (Math.min(width - 1, x + radius) - Math.max(0, x - radius) + 1);
      if (x + radius + 1 < width) sum += input[y * width + x + radius + 1];
      if (x - radius >= 0) sum -= input[y * width + x - radius];
    }
  }
  for (let x = 0; x < width; x++) {
    let sum = 0;
    for (let y = 0; y <= Math.min(radius, height - 1); y++) sum += horizontal[y * width + x];
    for (let y = 0; y < height; y++) {
      output[y * width + x] = sum / (Math.min(height - 1, y + radius) - Math.max(0, y - radius) + 1);
      if (y + radius + 1 < height) sum += horizontal[(y + radius + 1) * width + x];
      if (y - radius >= 0) sum -= horizontal[(y - radius) * width + x];
    }
  }
  return output;
}

export function apply800THalation(pixels, width, height, options = {}) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 ||
      pixels?.length !== width * height * 4) throw new RangeError('Invalid RGBA image dimensions');
  const { threshold = 0.78, radius = 16, strength = 0.7 } = options;
  if (![threshold, radius, strength].every(Number.isFinite) || threshold < 0 || threshold >= 1 ||
      !Number.isInteger(radius) || radius < 1 || radius > 64 || strength < 0 || strength > 1)
    throw new RangeError('Invalid halation parameters');
  const result = new Uint8ClampedArray(pixels);
  if (strength === 0) return result;

  const mask = new Float32Array(width * height);
  for (let i = 0; i < mask.length; i++) {
    const offset = i * 4;
    const luminance = (0.2126 * pixels[offset] + 0.7152 * pixels[offset + 1] +
      0.0722 * pixels[offset + 2]) / 255;
    const t = clamp((luminance - threshold) / Math.max(0.01, 1 - threshold), 0, 1);
    mask[i] = t * t * (3 - 2 * t) * (pixels[offset + 3] / 255);
  }
  const inner = blur(mask, width, height, radius);
  const outer = blur(mask, width, height, Math.min(64, radius * 2));
  for (let i = 0; i < mask.length; i++) {
    const halo = Math.sqrt(Math.max(0, (inner[i] * 0.8 + outer[i] * 0.5) - mask[i])) * strength * 0.8;
    const offset = i * 4;
    const alpha = pixels[offset + 3] / 255;
    result[offset] = clamp(pixels[offset] + 255 * halo * alpha, 0, 255);
    result[offset + 1] = clamp(pixels[offset + 1] + 65 * halo * alpha, 0, 255);
    result[offset + 2] = clamp(pixels[offset + 2] + 32 * halo * alpha, 0, 255);
  }
  return result;
}
