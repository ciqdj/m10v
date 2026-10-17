// Reproducible local camera-test export; does not flash or deploy.
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {prepareNative,generateNative} from '../node/gr3-native-library.mjs';
const root=fileURLToPath(new URL('..',import.meta.url));
const out=path.resolve(process.argv[2]||path.join(root,'builds/gr3-integrated-device-test'));
const configuration=process.argv[3]?JSON.parse(await readFile(process.argv[3],'utf8')):{
 slots:[1,64,54,37,33].map((film,i)=>({film,grain:i===4?2:0,soft:0,halo:{gain:3,spread:3,threshold:5,profile:2}})),
 stamp:2,format:0,corner:3,color:1};
const extensions={aspect:true,level:true,negativeGrain:true},debug_mode=!process.argv.includes('--release');
const version_unlock=process.argv.includes('--dsp-version-unlock')?{enabled:true,mode:'dsp-package-only'}:{enabled:false};
const source=await readFile(path.join(root,'bin/fwdc239b-gr3-official.bin'));
const plan=prepareNative(source,configuration,{extensions,debug_mode,version_unlock});
const result=await generateNative(source,configuration,plan.configuration_sha256,{extensions,debug_mode,version_unlock});
await mkdir(path.join(out,'fw'),{recursive:true});await mkdir(path.join(out,'evidence'),{recursive:true});
await writeFile(path.join(out,'fw/fwdc239b.bin'),result.candidate);
for(const [name,value] of Object.entries({'M10V-configuration.json':{configuration,extensions,debug_mode,version_unlock},'M10V-build-receipt.json':result.receipt,'M10V-preparation.json':plan,'evidence/M10V-runtime-manifest.json':result.manifest}))await writeFile(path.join(out,name),JSON.stringify(value,null,2)+'\n');
await writeFile(path.join(out,'evidence/M10V-runtime-arm.bin'),result.runtime);
await writeFile(path.join(out,'evidence/native-only.bin'),result.nativeCandidate);
if(result.component)await writeFile(path.join(out,'evidence/aspect-level.bin'),result.component);
await writeFile(path.join(out,'SHA256SUMS'),result.receipt.candidate_sha256+'  fw/fwdc239b.bin\n');
console.log(JSON.stringify({file:path.join(out,'fw/fwdc239b.bin'),bytes:result.candidate.length,sha256:result.receipt.candidate_sha256,build_id:result.receipt.debug_log?.build_id??null,extensions},null,2));
