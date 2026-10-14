// Read-only GR II 3.00 UNITY inventory. Address patches are never inferred.
// Container facts are independently checked against the local official image.
import {createHash} from 'node:crypto';

export const GR2_SHA256 = '3643850f2ae74ae967eb336794048f554caa1b11d05b8569824d5719f1838331';
export const GR2_SIZE = 14033920;
const MAGIC = Buffer.from('UNITY FILE V1.10 / RICOH COMPANY');
const sha = b => createHash('sha256').update(b).digest('hex');
const need = (value, reason) => { if (!value) throw new Error(reason); };

export function xorUnityPayload(data) {
  need(Buffer.isBuffer(data) && data.length % 4 === 0, 'UNITY payload must be word aligned');
  const output = Buffer.allocUnsafe(data.length);
  let key = 0xf8e69612;
  for (let block = 0; block < data.length; block += 512) {
    for (let at = block; at < Math.min(block + 512, data.length); at += 4)
      output.writeUInt32BE((data.readUInt32BE(at) ^ key) >>> 0, at);
    key = (key + 0xbe39b193) >>> 0;
  }
  return output;
}

export function decodeUnity(data, depth = 0) {
  need(Buffer.isBuffer(data) && data.length >= 2048 && data.length <= 64 * 1024 * 1024,
    'UNITY container size is invalid');
  need(depth <= 2, 'UNITY nesting exceeds limit');
  need(data.subarray(0, MAGIC.length).equals(MAGIC), 'UNITY magic differs');
  need(data.readUInt32BE(32) === data.length, 'UNITY declared size differs');
  const count = data.readUInt32BE(36);
  need(count > 0 && count <= 31, 'UNITY record count is invalid');
  const records = [], names = new Set(), reencoded = Buffer.from(data);
  for (let i = 0; i < count; i++) {
    const at = 64 + i * 64, start = data.readUInt32BE(at) * 512, size = data.readUInt32BE(at + 4);
    const nameBytes = data.subarray(at + 8, at + 20), terminator = nameBytes.indexOf(0);
    need(terminator > 0, 'UNITY component name is not terminated');
    const name = nameBytes.subarray(0, terminator).toString('ascii');
    need(/^[a-zA-Z0-9_-]+$/.test(name) && !names.has(name), 'UNITY component name is invalid or duplicated');
    names.add(name);
    need(size > 0 && size % 4 === 0 && start >= 2048 && start + size <= data.length,
      'UNITY component bounds overlap header or exceed container');
    need(records.every(row => start + size <= row.offset || start >= row.offset + row.size),
      'UNITY component bounds overlap another record');
    const type = data[at + 30], encoding = data[at + 31], payload = data.subarray(start, start + size);
    need(encoding === 1 && (type === 1 || type === 0x80), 'UNITY unsupported record encoding');
    const decoded = type === 1 ? xorUnityPayload(payload) : Buffer.from(payload);
    const nested = type === 0x80 ? decodeUnity(decoded, depth + 1) : null;
    (nested ? nested.reencoded : xorUnityPayload(decoded)).copy(reencoded, start);
    records.push({name, offset: start, size, type, encoding, decoded, nested,
      sha256: sha(decoded), encoded_sha256: sha(payload)});
  }
  need(reencoded.equals(data), 'UNITY byte-exact roundtrip failed');
  return {records, reencoded};
}

function official(data) {
  need(Buffer.isBuffer(data) && data.length === GR2_SIZE, 'GR II official size differs');
  need(sha(data) === GR2_SHA256, 'GR II official identity differs');
  return decodeUnity(data);
}

function flatten(container, parent = null) {
  return container.records.flatMap(row => [row, ...(row.nested ? flatten(row.nested, row.name) : [])]
    .map(value => value === row ? {...value, parent} : value));
}

function resourceRows(disk) {
  const table = 0x786000, rows = [], names = new Set();
  need(disk.length === 7896704, 'GR II resource disk size differs');
  for (let i = 0; i < 121; i++) {
    const at = table + i * 64;
    need(at + 64 <= disk.length, 'GR II resource table exceeds component');
    const nameBytes = disk.subarray(at, at + 32), end = nameBytes.indexOf(0);
    need(end > 0, 'GR II resource name is not terminated');
    const name = nameBytes.subarray(0, end).toString('ascii');
    need(/^A:\/[a-zA-Z0-9_./-]+$/.test(name) && !name.includes('..') && !names.has(name),
      'GR II resource name is invalid or duplicated');
    names.add(name);
    const declared_offset = disk.readUInt32BE(at + 32), size = disk.readUInt32BE(at + 36);
    // Volume addresses are relative to its 512-byte header, not file offset zero.
    const payload_offset = 512 + declared_offset;
    need(declared_offset % 512 === 0 && size > 0 && payload_offset + size <= table,
      'GR II resource bounds exceed volume or overlap directory');
    need(rows.every(row => payload_offset + size <= row.payload_offset ||
      payload_offset >= row.payload_offset + row.size), 'GR II resource bounds overlap');
    rows.push({name, table_offset: at, declared_offset, payload_offset, size,
      sha256: sha(disk.subarray(payload_offset, payload_offset + size))});
  }
  return rows;
}

export function readGr2Component(data, name) {
  const row = flatten(official(data)).find(row => row.name === name);
  need(row, 'unknown component');
  return Buffer.from(row.decoded);
}

export function inspectGr2(data) {
  const rows = flatten(official(data)), disk = rows.find(row => row.name === 'b01firm6');
  need(disk && rows.some(row => row.name === 'b01firm8'), 'GR II known component layout differs');
  const resources = resourceRows(disk.decoded);
  const version = disk.decoded.readUInt16BE(18);
  need(version === 0x0300, 'GR II internal version differs');
  return {
    schema: 'm10v-model-firmware-inventory/v1', model: 'GR II', public_version: '3.00',
    internal_version: '3.00', sha256: GR2_SHA256, size: data.length, filename: 'rg2_v003.frm',
    components: rows.map(({decoded, nested, ...row}) => row), resources,
    proof: {identity: true, strict_record_bounds: true, nested_container: true,
      resource_bounds: true, byte_exact_roundtrip: true,
      modified_update_checksum: false},
    capabilities: {
      inspect: {status: 'verified_offline', can_read: true},
      native_film_library: {status: 'not_ported', can_build: false,
        reason: 'GR II native menu, capture ABI and modified update checksum require proof'},
    },
    hardware_tested: false,
  };
}
