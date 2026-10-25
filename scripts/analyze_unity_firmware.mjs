#!/usr/bin/env node
// Research extraction only; never constructs modified update firmware.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import path from 'node:path';
import {inspectUnityModel,readUnityModelComponent} from '../node/unity-firmware.mjs';
import {unityProfiles} from '../node/unity-model-profiles.mjs';
import {createHash} from 'node:crypto';

const args = process.argv.slice(2), sourcePath = args[0];
const index = args.indexOf('--out');
if (!sourcePath || index < 1 || !args[index + 1])
  throw new Error('Usage: node scripts/analyze_unity_firmware.mjs INPUT --out DIRECTORY [--extract]');
const input = path.resolve(sourcePath), out = path.resolve(args[index + 1]);
if (input === out || input.startsWith(out + path.sep))
  throw new Error('output must not contain or overwrite the official input');
const source = await readFile(input), digest=createHash('sha256').update(source).digest('hex');
const model=Object.keys(unityProfiles).find(id=>unityProfiles[id].sha256===digest);
if(!model)throw Error('unsupported firmware identity');
const requested=args.indexOf('--model');
if(requested>=0&&args[requested+1]!==model)throw Error('input model differs from requested model');
const report=inspectUnityModel(source,model);
await mkdir(out, {recursive:true});
if (args.includes('--extract')) {
  for (const component of report.components)
    await writeFile(path.join(out, component.name + '.bin'), readUnityModelComponent(source, model, component.name));
  const disk = readUnityModelComponent(source, model, 'b01firm6');
  for (const row of report.resources) {
    const target = path.join(out, 'resources', row.name.slice(3));
    await mkdir(path.dirname(target), {recursive:true});
    await writeFile(target, disk.subarray(row.payload_offset, row.payload_offset + row.size));
  }
}
await writeFile(path.join(out,'inventory.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({model:report.model,report:path.join(out,'inventory.json'),
  sha256:report.sha256,roundtrip:report.proof.byte_exact_roundtrip}));
