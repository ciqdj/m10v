// Exact-byte evidence, not a claim of camera compatibility.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { readOfficialSection, SHA256 } from './firmware.mjs';

export const RTOS_SHA256 = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67';
const contract=JSON.parse(readFileSync(new URL('./gr3-800t-contract.json',import.meta.url)));
const sites = [
  [0x535048e8, '0e9d06eb', 'stock JPEG macro send call'],
  [0x53c62a10, 'd4475053', 'JPEG macro vtable consumer'],
  [0x53c62a54, '5c2ac653', 'JPEG macro type name pointer'],
  [0x534a276c, '030050e3', 'high-level 422 format comparison'],
  [0x534a2778, '0100a003', '422 descriptor enum'],
  [0x534a2788, '040050e3', 'high-level 420 format comparison'],
  [0x534a278c, '0200a003', '420 descriptor enum'],
  [0x535040e4, '010040e2', '422 named assertion expects enum 1'],
  [0x534a2bdc, '975027e0', 'combined chroma address = base + allocated area'],
  [0x534a2ba4, '00a086e5', 'first address output'],
  [0x534a2bac, '047086e5', 'combined chroma output'],
  [0x534a2bb4, '082086e5', 'third address output is zero'],
  [0x534a2d60, '0e0085e9', 'descriptor copies three addresses'],
  [0x534ab20c, '010053e3', 'cache span distinguishes 422'],
  [0x534ab218, 'a560a011', '420 combined chroma span halved'],
  [0x536a3d94, '049091e5', 'descriptor Y load'],
  [0x536a3d98, '088091e5', 'descriptor combined chroma load'],
  [0x53000944, '3e4f07ee', 'cache clean and invalidate by address'],
];

export function inspect800TEvidence(official) {
  const rtos = readOfficialSection(official, 'RTOS');
  const hash = createHash('sha256').update(rtos).digest('hex');
  if (hash !== RTOS_SHA256) throw new Error('800T RTOS identity differs');
  if (contract.schema!=='m10v-gr3-800t-static-contract/v1' || contract.rtos_sha256!==hash)
    throw new Error('800T static contract identity differs');
  const anchors = [...sites,...contract.anchors.map(row=>[row.address,row.bytes,row.meaning])].map(([address, expected, meaning]) => {
    const actual = rtos.subarray(address - 0x53000000, address - 0x53000000 + expected.length / 2).toString('hex');
    if (actual !== expected) throw new Error(`800T preimage differs at 0x${address.toString(16)}: ${actual}`);
    return { address: `0x${address.toString(16)}`, bytes: actual, meaning, verified: true };
  });
  const jpegType = rtos.toString('ascii', 0xc62a5c, 0xc62a5c + 24).split('\0')[0];
  if (jpegType !== '22JpegEncodeMacroProcess') throw new Error('800T JPEG type identity differs');
  return {
    schema: 'm10v-gr3-800t-evidence/v1', sourceSha256: SHA256, rtosSha256: hash,
    jpegType, anchors,
    descriptor: { format422: 1, format420: 2, y: 4, chroma: 8, third: 12,
      width: 16, height: 18, stride: 20, allocatedHeight: 22,
      chromaOrder: 'CbCr', numericEncoding: 'unsigned8',neutral:128,addressMode:2 },
    proved: ['exact_baseline', 'jpeg_macro_type', 'descriptor_format_enums',
      'combined_chroma_address_creation', 'cache_span_422_420', 'cache_range_instructions',
      'original_cpu_CbCr_unsigned128','jpeg_raw_request_split','local_producer_wait_jpeg_wait_sequence',
      'startup_executable_identity_mapping'],
    supportedRecipeModes:[...contract.recipeModes],runtimeIsolation:'exact topology + CFA/scratch nonoverlap',
    unresolved: [], limits:[...contract.limits],
    firmwareReady: true, cameraTested: false,physicalValidationRequired:true,
  };
}
