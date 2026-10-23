// Local diagnostic export only. Does not flash, push or deploy.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve} from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {encodeZip} from '../node/gr3-sd-film-export.mjs';
const folder=resolve(process.argv[2]||'builds/m10v-gr3-zoom80-diagnostic-20261023');
const configuration=defaultConfiguration();configuration.zoom={write:true,slots:[50,80],revision:0x238050};
const options={debug_mode:true,extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const source=await readNativeOfficial('gr3'),plan=prepareNative(source,configuration,options);
const result=await generateNative(source,configuration,plan.configuration_sha256,options);
const sha=b=>createHash('sha256').update(b).digest('hex'),json=x=>Buffer.from(JSON.stringify(x,null,2)+'\n');
const files={'gr3/fwdc239b.bin':result.candidate,'gr3/manifest.json':json(result.manifest),'gr3/receipt.json':json(result.receipt),'gr3/configuration.json':json(plan.configuration),
 'README.txt':await readFile('docs/testing/gr3-zoom80-diagnostic-20261023.txt'),'LICENSE':await readFile('LICENSE'),'THIRD_PARTY_NOTICES.md':await readFile('THIRD_PARTY_NOTICES.md')};
for(const name of ['third_party/curated-film-luts/LICENSE','third_party/spectral-film-lut/LICENSE'])files[name]=await readFile(name);
const snapshot={};for(const name of Object.keys(result.manifest.sources))snapshot[name]=await readFile(name);
files['evidence/source-snapshot.zip']=encodeZip(snapshot);
files['SHA256SUMS']=Buffer.from(Object.entries(files).map(([name,b])=>sha(b)+'  '+name).join('\n')+'\n');
await mkdir(folder,{recursive:false});for(const[name,b]of Object.entries(files)){await mkdir(resolve(folder,name,'..'),{recursive:true});await writeFile(resolve(folder,name),b);}
await writeFile(resolve(folder,'runtime.bin'),result.runtime);
const zip=encodeZip(files),path=resolve(folder,'m10v-gr3-zoom80-diagnostic-20261023.zip');await writeFile(path,zip);
console.log(JSON.stringify({path,bin_sha256:sha(result.candidate),zip_sha256:sha(zip),build_id:result.receipt.debug_log.build_id,camera_tested:false,status:'DIAGNOSTIC_NOT_A_CONFIRMED_FIX'},null,2));
