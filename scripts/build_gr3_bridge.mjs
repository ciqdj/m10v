#!/usr/bin/env node
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {prepareGr3Bridge,exportGr3Bridge} from '../node/gr3-bridge.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source=await readFile(path.resolve(process.argv[2]||path.join(root,'bin/fwdc239b-gr3-official.bin')));
const destination=path.resolve(process.argv[3]||path.join(root,'builds/gr3-bridge-2.10.33.27-release'));
const plan=prepareGr3Bridge(source),result=exportGr3Bridge(source,{accepted_plan_id:plan.plan_id,acknowledge_instructions:true});
await mkdir(destination,{recursive:true});
for(const [name,bytes] of Object.entries(result.files)){const target=path.join(destination,name);await mkdir(path.dirname(target),{recursive:true});await writeFile(target,bytes,{flag:'wx'});}
const archive=path.join(destination,'M10V-GRIII-bridge-2.10.33.27.zip');await writeFile(archive,result.zip,{flag:'wx'});
console.log(JSON.stringify({archive,...result.receipt},null,2));
