// GR III v16 research format: 12 sectors, each a 3×3 row-sum-preserving matrix.
// The firmware activation tables are a separate dependency and are not supplied here.
const SECTORS = 12;
const ROWS = 3;
const SCALE = 1024;
const STEP = 4;

function need(condition, message) { if (!condition) throw new Error(message); }

export function normalizeHueSectors(input) {
  need(Array.isArray(input) && input.length === SECTORS, '色相必须包含12个分区');
  return input.map((sector, s) => {
    need(Array.isArray(sector) && sector.length === ROWS, `色相分区${s}必须为3×3矩阵`);
    return sector.map((row, r) => {
      need(Array.isArray(row) && row.length === ROWS && row.every(Number.isFinite),
        `色相分区${s}第${r}行无效`);
      need(Math.abs(row.reduce((sum, value) => sum + value, 0) - 1) <= 1e-6,
        `色相分区${s}第${r}行和必须为1`);
      return [...row];
    });
  });
}

export function quantizeHueSectors(input) {
  const normalized = normalizeHueSectors(input);
  const packed = new Uint8Array(SECTORS * ROWS * ROWS);
  const q10 = normalized.map((sector, s) => sector.map((row, r) => {
    const raw = row.map((value, c) => c === r ? 0 : Math.round(value * SCALE / STEP));
    raw[r] = -raw.reduce((sum, value) => sum + value, 0);
    need(raw.every(value => Number.isInteger(value) && value >= -127 && value <= 127),
      `色相分区${s}第${r}行超出固件有符号范围`);
    for (let c = 0; c < ROWS; c++) packed[(s * 3 + r) * 3 + c] = raw[c] & 255;
    return raw.map((value, c) => (c === r ? SCALE : 0) + STEP * value);
  }));
  return { q10, packed };
}

export function inspectPackedHueSectors(bytes) {
  need(bytes instanceof Uint8Array && bytes.length === SECTORS * ROWS * ROWS, '色相表长度必须为108字节');
  return Array.from({ length: SECTORS }, (_, s) => Array.from({ length: ROWS }, (_, r) => {
    const raw = Array.from({ length: ROWS }, (_, c) => {
      const byte=bytes[(s * 3 + r) * 3 + c];return byte < 128 ? byte : byte - 256;
    });
    need(raw.reduce((sum, value) => sum + value, 0) === 0, `色相分区${s}第${r}行不守恒`);
    need(raw.every(value => value !== -128), `色相分区${s}第${r}行超出固件范围`);
    return raw.map((value, c) => (c === r ? SCALE : 0) + STEP * value);
  }));
}
