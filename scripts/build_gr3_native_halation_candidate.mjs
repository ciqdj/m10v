// Local-only GR III native color/grain + full-resolution halo test package.
import {mkdir,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
const out=path.resolve(process.argv[2]||'builds/gr3-native-halation-v8');
const configuration=defaultConfiguration();
[33,66,67,68,35].forEach((film,i)=>{
 const s=configuration.slots[i];s.film=film;s.grain=i===2?1:2;s.soft=0;
 s.halo={gain:film===33?3:film===67?2:0,spread:3,threshold:5,profile:2};
 s.effects={grainSize:0,leakGain:0,leakPosition:0,leakSpread:4,leakVariation:0,filmExposure:0};
});
const options={debug_mode:true,live_color:true,hdf_enabled:true,extensions:{aspect:true,level:true,negativeGrain:true}};
const official=await readNativeOfficial('gr3'),plan=prepareNative(official,configuration,options);
const result=await generateNative(official,configuration,plan.configuration_sha256,options);
if(!result.receipt.live_view_base?.film_color_preview||result.manifest.capture_lifecycle.snapshot.live_color!==true)throw Error('Missing live color hook');
const pack=buildSdFilmPack(),packReceipt=auditSdFilmPack(pack);
await mkdir(path.join(out,'M10V'),{recursive:true});await mkdir(path.join(out,'evidence'),{recursive:true});
await writeFile(path.join(out,'fwdc239b.bin'),result.candidate);await writeFile(path.join(out,'M10V/FILMS.M10'),pack);
for(const [name,data] of Object.entries({'configuration.json':configuration,'receipt.json':result.receipt,'preparation.json':plan,'evidence/M10V-runtime-manifest.json':result.manifest,'evidence/film-pack.json':packReceipt}))await writeFile(path.join(out,name),JSON.stringify(data,null,2)+'\n');
await writeFile(path.join(out,'evidence/M10V-runtime-arm.bin'),result.runtime);
const hash=b=>createHash('sha256').update(b).digest('hex');
await writeFile(path.join(out,'SHA256SUMS'),`${hash(result.candidate)}  fwdc239b.bin\n${hash(pack)}  M10V/FILMS.M10\n`);
console.log(JSON.stringify({out,bytes:result.candidate.length,sha256:hash(result.candidate),build_id:result.receipt.debug_log.build_id,verified_hooks:result.receipt.verified_hooks,live_color:true,camera_tested:false},null,2));
