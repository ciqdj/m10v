// Read-only assertions for update-path evidence in the exact GR III image.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { readOfficialSection, SHA256 } from '../node/firmware.mjs';

const BASE = 0x53000000;
const gateRows = [
  [0x53838cd0, '02bef7eb000050e30200000a', 'updater state calls version gate and branches on false', 'update state dispatch'],
  [0x53628574, '000055e11700003a', 'candidate below current enters rejection path', 'version gate'],
  [0x536290c8, '0dc0a0e1f0d92de9', 'project/marker wrapper entry only; outcome not fully traced', 'update parser'],
  [0x53629044, '0c3090e504e02de5', 'CPU checksum verifier entry; caller linkage unresolved', 'CPU payload validator'],
];

export function analyzeUpdatePath(official) {
  const rtos = readOfficialSection(official, 'RTOS');
  const gates = gateRows.map(([address, bytes, observation, caller]) => {
    const offset = address - BASE;
    if (rtos.subarray(offset, offset + bytes.length / 2).toString('hex') !== bytes)
      throw new Error(`update instruction mismatch at 0x${address.toString(16)}`);
    return { address: `0x${address.toString(16)}`, instruction_bytes: bytes,
      observation, caller };
  });
  return {
    source_sha256: SHA256,
    gates,
    unresolved: ['flash_write_callback', 'same_version_acceptance',
      'full_project_marker_call_chain', 'CPU_verifier_call_conditions', 'recovery_path'],
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const input = process.argv[2] || new URL('../fwdc239b.bin', import.meta.url);
  console.log(JSON.stringify(analyzeUpdatePath(readFileSync(input)), null, 2));
}
