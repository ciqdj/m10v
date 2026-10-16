import {createHash} from 'node:crypto';
import {readFile,mkdtemp,rm,access} from 'node:fs/promises';
import {promisify} from 'node:util';
import {execFile} from 'node:child_process';
import path from 'node:path';
import {readFileSync} from 'node:fs';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {normalizeConfiguration,normalizeExtensions,activeExtensions} from '../web/gr3/native-library-state.mjs';
import {inspectOfficial} from './firmware.mjs';
import {buildNativeLibrary,nativeSourceFingerprint} from './gr3-m10v-native-build.mjs';
import {buildCameraComponents,composeNative,integrationFingerprint} from './gr3-integrated-components.mjs';
const root=fileURLToPath(new URL('..',import.meta.url));
const hash=b=>createHash('sha256').update(b).digest('hex');
const officialHash='d6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4';
const run=promisify(execFile);
export async function nativeCatalog(){
 const source=await readFile(path.join(root,'native/gr3/m10v_library.c'),'utf8');
 const films=[...source.matchAll(/\{"([^"\n]+)",(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)\}/g)].map((m,i)=>({id:i+1,name:m[1]}));
 if(films.length!==33)throw Error('M10V 原生目录不完整');
 const legacy=JSON.parse(await readFile(path.join(root,'web/gr3/film-catalog.json'),'utf8')).looks;
 films.forEach(f=>f.group='M10V精选');
 films.push(...legacy.map((f,i)=>({id:34+i,name:f.name,group:f.group||'胶片模拟',legacy_id:f.id,color_path:'saved-jpeg-rgb-tables'})));
 films.push({id:66,key:'m10v-5207',name:'5207',group:'M10V精选',camera_calibrated:false,film_calibrated:false});
 const icons=JSON.parse(await readFile(path.join(root,'web/gr3/film-icons/catalog.json'),'utf8'));
 if(icons.length!==films.length||icons.some((v,i)=>v.id!==films[i].id||v.name!==films[i].name))throw Error('M10V 图标目录与胶卷不同步');
 films.forEach((f,i)=>Object.assign(f,{icon_url:icons[i].icon_url,icon_color:icons[i].color}));
 let available=false;try{available=hash(await readFile(path.join(root,'fwdc239b-offical.bin')))===officialHash;}catch{}
 return {local_sources:['gr3'],films:films.filter(f=>f.id>=33),external_film_pack:false,camera_tested:false,local_source_available:available,
  scope:'保存的静态 JPEG；取景和机内 RAW 再开发尚未接入',slot_tone_ids:[12,18,19,20,21]};
}
export async function readNativeOfficial(model='gr3'){
 const profiles={gr3:['bin/fwdc239b-gr3-official.bin',officialHash],gr3x:['bin/fwdc243b-gr3x-official.bin','708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7']};
 if(!profiles[model])throw Error('首批仅开放 GR III 和 GR IIIx');
 const [file,expected]=profiles[model];const b=await readFile(path.join(root,file));if(hash(b)!==expected)throw Error('本地官方固件摘要不匹配');return b;
}
export function initialState(configuration){
 const c=normalizeConfiguration(configuration),b=Buffer.alloc(104);b.writeUInt32LE(0x5630314d);b.writeUInt16LE(3,4);b.writeUInt16LE(104,6);
 c.slots.forEach((s,i)=>{b.writeUInt16LE(s.film,12+i*8);b[14+i*8]=s.grain;b[15+i*8]=s.soft;b[16+i*8]=s.halo.gain;b[17+i*8]=s.halo.spread;b[18+i*8]=s.halo.threshold;b[19+i*8]=s.halo.profile;const e=s.effects;b[56+i*8]=e.grainSize;b[57+i*8]=e.leakGain;b[58+i*8]=e.leakPosition;b[59+i*8]=e.leakSpread;b[60+i*8]=e.leakVariation;});
 b[52]=c.stamp;b[53]=c.format;b[54]=c.corner;b[55]=c.color;
 let crc=0xffffffff;for(const byte of b.subarray(0,100)){crc^=byte;for(let k=0;k<8;k++)crc=(crc>>>1)^(0xedb88320&-(crc&1));}
 b.writeUInt32LE(~crc>>>0,100);return b;
}
export function prepareNative(source,value,{debug_mode=false,extensions:requestedExtensions}={}){
 const report=inspectOfficial(source),extensions=normalizeExtensions(requestedExtensions);
 if(report.model!=='GR III')throw Error('800T 原厂详细菜单当前仅验证 GR III 2.10；GR IIIx 原生导出尚未支持');
 if(activeExtensions(extensions).length>0&&report.model!=='GR III')throw Error('组合扩展当前仅支持 GR III');
 if(typeof debug_mode!=='boolean')throw Error('调试模式必须为布尔值');
 if(debug_mode&&report.model!=='GR III')throw Error('调试模式当前仅支持 GR III');
 const integration_source_sha256=integrationFingerprint();
 const reference=JSON.parse(readFileSync(path.join(root,'native/gr3/5207-reference.json'),'utf8'));
 const configuration=normalizeConfiguration(value),runtime_source_sha256=nativeSourceFingerprint(),configuration_sha256=hash(JSON.stringify({source:report.sha256,configuration,extensions,debug_mode,runtime_source_sha256,integration_source_sha256}));
 return {schema:'m10v-native-library-plan/v1',ready:true,extensions,integration_source_sha256,features:['film','800t','5207','grain','soft','timestamp',...activeExtensions(extensions)],source_sha256:report.sha256,configuration,configuration_sha256,runtime_source_sha256,model:report.model,public_version:report.public_version,filename:report.model==='GR IIIx'?'fwdc243b.bin':'fwdc239b.bin',
  debug_mode,debug_log:debug_mode?{schema:'m10v-gr3-sd-debug/v1',build_id:configuration_sha256.slice(0,8),files:['M10VMN0.BIN','M10VMN1.BIN','M10VCP0.BIN','M10VCP1.BIN'],page_bytes:4096,records_per_channel:63}:null,
  stock_detail:{ids:[18,19,20,21,22],fields:['gain','spread','threshold','grain','soft'],only_film:33,slots:5,lifecycle:'stock immediate callback'},
  initial_state_hex:initialState(configuration).toString('hex'),film_5207_reference:{table_sha256:reference.table_sha256,table_size:reference.table_size,table_bits:reference.table_bits,input:reference.input,camera_calibrated:false,film_calibrated:false,halation:false},film_count:66,active_slots:5,camera_tested:false,external_film_pack:false,
  scope:'静态 JPEG 色彩、颗粒、柔光与时间戳；五槽机内替换并持久化。取景和 RAW 再开发未接入。',
  initial_settings_policy:'首次无有效 M10V 记录时使用网页默认值；已有机内 M10V 记录优先。'};
}
let building=false;
export async function generateNative(source,value,accepted,{signal,debug_mode=false,extensions}={}){
 const plan=prepareNative(source,value,{debug_mode,extensions});if(accepted!==plan.configuration_sha256)throw Error('配置已变化，请重新预检');
 if(building)throw Error('另一个 M10V 原生固件正在构建，请稍后重试');
 building=true;let folder;
 try{
  folder=await mkdtemp(path.join(os.tmpdir(),'m10v-native-export-'));
  let python=path.join(root,'.venv/bin/python');try{await access(python);}catch{python='python3';}
  const component=await buildCameraComponents(source,plan.extensions,{signal});
  await run(python,['scripts/build_gr3_m10v_library.py','--base',component?'0x540ba000':'0x540b6000','--out',folder,'--initial-state-hex',plan.initial_state_hex,...(debug_mode?['--debug','--debug-build-id','0x'+plan.debug_log.build_id]:[])],{cwd:root,signal,timeout:120000,maxBuffer:2*1024*1024});
  const manifest=JSON.parse(await readFile(path.join(folder,'m10v-library-arm.json'),'utf8'));
  if(manifest.initial_state_hex!==plan.initial_state_hex)throw Error('ARM 初始配置回读不同');
  if(manifest.debug_mode!==debug_mode||(debug_mode&&manifest.debug_log?.build_id!==plan.debug_log.build_id))throw Error('ARM 调试模式回读不同');
  const runtime=await readFile(path.join(folder,'m10v-library-arm.bin'));
  const result=buildNativeLibrary(source,runtime,manifest);
  const joined=composeNative(source,result.candidate,runtime,manifest,component,plan.extensions);
  return {...result,candidate:joined.candidate,nativeCandidate:result.candidate,component,manifest,runtime,receipt:{...result.receipt,extensions:plan.extensions,features:plan.features,film_5207_reference:plan.film_5207_reference,integration_source_sha256:plan.integration_source_sha256,composition:joined.composition,candidate_sha256:hash(joined.candidate),candidate_bytes:joined.candidate.length,rtos_growth:joined.structure.rtosGrowth,configuration:plan.configuration,configuration_sha256:plan.configuration_sha256,runtime_source_sha256:plan.runtime_source_sha256,
   model:plan.model,public_version:plan.public_version,filename:plan.filename,initial_state_hex:plan.initial_state_hex,initial_settings_policy:plan.initial_settings_policy}};
 }finally{if(folder)await rm(folder,{recursive:true,force:true});building=false;}
}
