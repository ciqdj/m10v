#!/usr/bin/env node
// Research extraction only; never constructs modified update firmware.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {inspectGr2,readGr2Component} from '../node/gr2-firmware.mjs';

const args = process.argv.slice(2), sourcePath = args[0];
const index = args.indexOf('--out');
if (!sourcePath || index < 1 || !args[index + 1])
  throw new Error('Usage: node scripts/analyze_gr2_firmware.mjs INPUT --out DIRECTORY [--extract]');
const input = path.resolve(sourcePath), out = path.resolve(args[index + 1]);
if (input === out || input.startsWith(out + path.sep))
  throw new Error('output must not contain or overwrite the official input');
const source = await readFile(input), report = inspectGr2(source);
await mkdir(out, {recursive:true});
if (args.includes('--extract')) {
  for (const component of report.components)
    await writeFile(path.join(out, component.name + '.bin'), readGr2Component(source, component.name));
  const disk = readGr2Component(source, 'b01firm6');
  for (const row of report.resources) {
    const target = path.join(out, 'resources', row.name.slice(3));
    await mkdir(path.dirname(target), {recursive:true});
    await writeFile(target, disk.subarray(row.payload_offset, row.payload_offset + row.size));
  }
}
await writeFile(path.join(out,'inventory.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({model:report.model,report:path.join(out,'inventory.json'),
  sha256:report.sha256,roundtrip:report.proof.byte_exact_roundtrip}));
