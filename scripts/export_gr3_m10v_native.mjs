// Local delivery CLI using the same original build pipeline as the webpage.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import path from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
const rawArgs=process.argv.slice(2),model=rawArgs.find(a=>a.startsWith('--model='))?.slice(8)||'gr3';
const args=rawArgs.filter(a=>!a.startsWith('--model='));
if(args.length>2)throw Error('usage: node scripts/export_gr3_m10v_native.mjs [output-directory] [configuration.json]');
const directory=path.resolve(args[0]||'builds/m10v-gr3-native-test');
const configuration=args[1]?JSON.parse(await readFile(args[1],'utf8')):defaultConfiguration();
const original=await readNativeOfficial(model),plan=prepareNative(original,configuration);
const {candidate,receipt,manifest,runtime}=await generateNative(original,configuration,plan.configuration_sha256);
await mkdir(directory,{recursive:true});
await writeFile(path.join(directory,plan.filename),candidate);
await writeFile(path.join(directory,'M10V-runtime-arm.bin'),runtime);
await writeFile(path.join(directory,'M10V-build-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
await writeFile(path.join(directory,'M10V-runtime-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
await writeFile(path.join(directory,'M10V-configuration.json'),JSON.stringify(plan.configuration,null,2)+'\n');
console.log(JSON.stringify({directory,sha256:receipt.candidate_sha256,bytes:receipt.candidate_bytes,verified_hooks:receipt.verified_hooks,camera_tested:false},null,2));
