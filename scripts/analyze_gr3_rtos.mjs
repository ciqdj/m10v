// Read-only, exact-baseline GR III RTOS evidence. No firmware writer.
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { readOfficialSection, SHA256 } from '../node/firmware.mjs';

const input = process.argv[2] || new URL('../fwdc239b.bin', import.meta.url);
const firmware = readFileSync(input);
const rtos = readOfficialSection(firmware, 'RTOS');
const cpu = readOfficialSection(firmware, 'CPU');
const base = 0x53000000;
const copySourceOffset = 0x5407b540 - base;
const jpegTableRam = 0x55002b78;
const jpegTableOffset = copySourceOffset + (jpegTableRam - 0x55000000);
const expected = [
  ['GB_Diary.jpg', 0xb5f508, 0xb2298c],
  ['GB_ING.jpg', 0xb5f510, 0xb229cc],
  ['GoodBye.jpg', 0xb5f540, 0xb22abc],
  ['Collabo.jpg', 0xb5f550, 0xb22a9c],
  ['GB_Urban.jpg', 0xb5f558, 0xb229ac],
];

function check(ok, reason) { if (!ok) throw new Error(reason); }
function instruction(offset, hex) {
  check(rtos.subarray(offset, offset + hex.length / 2).toString('hex') === hex,
    `ARM instruction differs at 0x${offset.toString(16)}`);
}
function refs(word) {
  const needle = Buffer.alloc(4);
  needle.writeUInt32LE(word);
  const found = [];
  for (let at = rtos.indexOf(needle); at >= 0; at = rtos.indexOf(needle, at + 1)) found.push(at);
  return found;
}

const descriptors = expected.map(([name, descriptorOffset, pathOffset]) => {
  const path = `B:\\Resource\\Jpeg\\${name}`;
  check(rtos.toString('ascii', pathOffset, pathOffset + path.length) === path,
    `path mismatch: ${name}`);
  check(rtos.readUInt32LE(descriptorOffset) === 0x01e002d0,
    `dimensions differ: ${name}`);
  check(rtos.readUInt32LE(descriptorOffset + 4) === base + pathOffset,
    `path pointer differs: ${name}`);
  const tableOffset = refs(base + descriptorOffset).find((at) =>
    at >= jpegTableOffset && at < jpegTableOffset + 0x100);
  check(tableOffset !== undefined && (tableOffset - jpegTableOffset) % 4 === 0,
    `JPEG table entry differs: ${name}`);
  return {
    name, path, descriptor_address: `0x${(base + descriptorOffset).toString(16)}`,
    path_address: `0x${(base + pathOffset).toString(16)}`,
    native_id: (tableOffset - jpegTableOffset) / 4, width: 720, height: 480,
    descriptor_pointer_offsets: refs(base + descriptorOffset).map((at) => `0x${at.toString(16)}`),
  };
});

// ARM load consumer: MOVW/MOVT ip, 0x55002b78; LDR r1, [ip, r1, LSL #2].
instruction(0x22e4b4, '78cb02e3');
instruction(0x22e4bc, '00c545e3');
instruction(0x22e4c8, '01119ce7');
instruction(0x22e4d8, 'b0c0d1e1'); // descriptor width
instruction(0x22e4e0, 'b200d1e1'); // descriptor height
instruction(0x22e4f8, '04c091e5'); // descriptor path pointer

// Caller has a 5-way jump table, then supplies the native JPEG ID in r1.
instruction(0x19f1e4, '040053e3');
instruction(0x19f1e8, '03f19f97');
instruction(0x19f22c, '0710a0e1'); // MOV r1, r7
instruction(0x19f234, '9b3c02eb'); // BL JPEG consumer
const choiceIds = [2, 3, 11, 10, 12];
const caseAddresses = [0x5319f204, 0x5319f270, 0x5319f278, 0x5319f280, 0x5319f268];
for (let i = 0; i < choiceIds.length; i++) {
  check(rtos.readUInt32LE(0x19f1f0 + i * 4) === caseAddresses[i],
    `choice branch ${i} differs`);
  check(rtos.readUInt32LE(caseAddresses[i] - base) === 0xe3a07000 + choiceIds[i],
    `choice JPEG ID ${i} differs`);
}
const byId = new Map(descriptors.map((row) => [row.native_id, row.name]));
const choices = choiceIds.map((nativeId, value) => ({ value, native_id: nativeId,
  filename: byId.get(nativeId) || null }));
check(choices.every((row) => row.filename), 'choice points outside known shutdown resources');

const markers = ['Today : %07ld', 'Today : XXXXXXX', 'StreetEdition',
  'UrbanEdition', 'COLLAB_MODE STREET_EDITION', 'StillAspectRatio', 'StillCropMag'];
const strings = Object.fromEntries(markers.map((value) => {
  const offset = rtos.indexOf(value);
  check(offset >= 0, `missing marker: ${value}`);
  return [value, `0x${offset.toString(16)}`];
}));

// Today overlay path constructs a format string address and calls its formatter.
instruction(0x19eea0, '4c2e0fe3'); // MOVW r2, #0xfe4c
instruction(0x19eea8, 'b12345e3'); // MOVT r2, #0x53b1
instruction(0x19eeb4, '9188feeb'); // BL formatter at 0x53141100

// StillAspectRatio command handlers: text 3_2 -> internal 0; 1_1 -> 3.
check(rtos.toString('ascii', 0xb27d98, 0xb27d98 + 16) === 'StillAspectRatio',
  'aspect command name differs');
for (const [offset, value] of [[0xb23090, '3_2'], [0xd59e94, '1_1'],
  [0xb2e5e4, '3_2'], [0xb2e5ec, '1_1']]) {
  check(rtos.toString('ascii', offset, offset + value.length) === value,
    `aspect value differs at 0x${offset.toString(16)}`);
}
instruction(0x34e694, '72e3feea'); // write command tail-branch to 0x53307464
instruction(0x3074ac, '0310a0e3'); // 1_1 -> internal value 3
instruction(0x3074c4, '0410a0e1'); // 3_2 -> internal value 0
instruction(0x2525c0, 'c214c3e5'); // setter stores aspect byte at context +0x4c2
instruction(0x3904bc, 'a859ffea'); // read command tail-branch to 0x53366b64
instruction(0x245264, 'c204d3e5'); // getter reads aspect byte at context +0x4c2
instruction(0x366b84, '030050e3'); // read handler compares internal value 3

// One update-version gate compares candidate/current packed version words.
const downgradeMessage = 'Update Version is older than Current Version!!';
check(rtos.toString('ascii', 0xd33804, 0xd33804 + downgradeMessage.length) === downgradeMessage,
  'downgrade diagnostic differs');
instruction(0x628574, '000055e1'); // CMP candidate, current
instruction(0x628578, '1700003a'); // BLO reject
const versionCaseTargets = [0x53628604, 0x53628604, 0x53628598,
  0x53628598, 0x53628598, 0x5362857c, 0x53628550];
for (let index = 0; index < versionCaseTargets.length; index++) {
  check(rtos.readUInt32LE(0x628534 + index * 4) === versionCaseTargets[index],
    `version type ${index} branch differs`);
}
instruction(0x6285d4, '000056e1'); // CMP second candidate, current
instruction(0x6285d8, '1500002a'); // BHS second-check path
instruction(0x62862c, 'eaffff3a'); // another BLO reject after outer +0x38 parse
instruction(0x628644, 'e4ffff3a'); // another BLO reject after second comparison
instruction(0x6285dc, '042803e3'); // MOVW diagnostic address
instruction(0x6285e4, 'd32345e3'); // MOVT diagnostic address
instruction(0x6285fc, '0000a0e3'); // return false after diagnostic
instruction(0x6298f8, '38c0d1e5'); // candidate outer header +0x38
instruction(0x629008, '90c0d1e5'); // candidate CPU payload +0x90
instruction(0x838cd0, '02bef7eb'); // updater state calls version gate
instruction(0x838cd4, '000050e3'); // compare gate result with zero
instruction(0x838cd8, '0200000a'); // false follows error branch

// CPU payload has a 128 KiB big-endian additive checksum and a header field.
instruction(0x62904c, '7d20d3e5'); // read CPU header +0x7d
instruction(0x629050, '7c00d3e5'); // read CPU header +0x7c
instruction(0x6290ac, '020080e0'); // accumulate big-endian words
instruction(0x6290b4, '100f6fe1'); // CLZ sum
instruction(0x6290b8, 'a002a0e1'); // reduce zero-sum result to boolean
instruction(0x62906c, '010072e3'); // special-case header word 0xffffffff
instruction(0x629070, '1200000a'); // skip sum when header is 0xffffffff
instruction(0x6290c0, '0100a0e3'); // special case returns true
check(cpu.length === 0x20000, 'CPU length differs');
let cpuSumWithoutField = 0;
for (let offset = 0; offset < cpu.length; offset += 4) {
  if (offset !== 0x7c) cpuSumWithoutField = (cpuSumWithoutField + cpu.readUInt32BE(offset)) >>> 0;
}
const cpuChecksumWord = cpu.readUInt32BE(0x7c);
check(cpuChecksumWord === (-cpuSumWithoutField >>> 0), 'CPU header checksum complement differs');

console.log(JSON.stringify({
  source_sha256: SHA256,
  rtos_sha256: createHash('sha256').update(rtos).digest('hex'),
  base_address: `0x${base.toString(16)}`,
  jpeg_table_ram: `0x${jpegTableRam.toString(16)}`,
  jpeg_consumer_address: '0x5322e4a8',
  choice_caller_address: '0x5319f180',
  today_overlay_formatter_address: '0x5319eea0',
  version_gate_address: '0x536284e0',
  version_gate_caller_address: '0x53838cd0',
  version_gate_observation: 'BLO rejects lower candidate at observed branches; equality passes this check but full updater acceptance is unproven',
  version_type_targets: versionCaseTargets.map((address, type) => ({
    type, address: `0x${address.toString(16)}` })),
  cpu_checksum: {
    payload_bytes: cpu.length, word_offset: '0x7c', byte_order: 'big',
    word: `0x${cpuChecksumWord.toString(16)}`,
    additive_sum: '0x00000000',
    verifier_address: '0x53629044',
    sentinel_exception: 'header checksum 0xffffffff returns true in this function; no use in candidate strategy',
  },
  aspect_command: {
    name: 'StillAspectRatio', write_handler: '0x53307464',
    read_handler: '0x53366b64', storage_byte_offset: '0x4c2',
    text_to_internal_value: { '3_2': 0, '1_1': 3 },
    scope: 'observed command interface and context byte only; capture, RAW, menu and display consumers not traced',
  },
  descriptors, choices, strings,
  interpretation: 'static image-ID choice and resource consumer proven for exact BIN; camera edition value, full shutdown runtime, repack and acceptance not proven',
}, null, 2));
