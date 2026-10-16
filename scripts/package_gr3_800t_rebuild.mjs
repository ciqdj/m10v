// Build and independently re-read a GR III delivery from the pinned official image.
// Usage: node scripts/package_gr3_800t_rebuild.mjs configuration.json output-directory
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {prepareNative,generateNative,readNativeOfficial} from '../node/gr3-native-library.mjs';
import {auditIntegratedNative} from '../node/gr3-integrated-components.mjs';
import {decodeFrameMap} from '../node/gr3-frames.mjs';

const [configFile,out]=process.argv.slice(2);
if(!configFile||!out)throw Error('Usage: configuration.json output-directory');
const {configuration,extensions}=JSON.parse(await readFile(configFile,'utf8'));
const source=await readNativeOfficial('gr3'),options={extensions,debug_mode:true};
const plan=prepareNative(source,configuration,options);
const result=await generateNative(source,configuration,plan.configuration_sha256,options);
await mkdir(path.join(out,'evidence'),{recursive:true});
const save=(name,data)=>writeFile(path.join(out,name),data);
const json=(name,data)=>save(name,JSON.stringify(data,null,2)+'\n');
await save('fwdc239b.bin',result.candidate);
await save('evidence/runtime.bin',result.runtime);
await save('evidence/native-candidate.bin',result.nativeCandidate);
if(result.component)await save('evidence/camera-component.bin',result.component);
await json('configuration.json',{configuration:plan.configuration,extensions:plan.extensions});
await json('evidence/plan.json',plan);
await json('evidence/manifest.json',result.manifest);
await json('evidence/receipt.json',result.receipt);
// Verify bytes read from the delivered files, rather than just the build buffers.
const candidate=await readFile(path.join(out,'fwdc239b.bin'));
const audit=auditIntegratedNative(source,candidate,
  await readFile(path.join(out,'evidence/native-candidate.bin')),
  await readFile(path.join(out,'evidence/runtime.bin')),
  JSON.parse(await readFile(path.join(out,'evidence/manifest.json'),'utf8')),
  result.component?await readFile(path.join(out,'evidence/camera-component.bin')):null,plan.extensions);
const decoded=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8)).decoded;
let at=0;while(decoded.toString('ascii',at,at+4)!=='RTOS')at+=16+decoded.readUInt32LE(at+12);
await save('evidence/RTOS.bin',decoded.subarray(at+16,at+16+decoded.readUInt32LE(at+12)));
await json('evidence/readback-audit.json',audit);
const sha=createHash('sha256').update(candidate).digest('hex');
await save('SHA256SUMS.txt',sha+'  fwdc239b.bin\n');
console.log(JSON.stringify({sha256:sha,bytes:candidate.length,rtos_growth:result.receipt.rtos_growth,
  build_id:plan.debug_log.build_id,verified:audit.verified,camera_tested:false},null,2));
