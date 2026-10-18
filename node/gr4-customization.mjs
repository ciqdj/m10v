// GR IV customization owns its native identities, parameter getters and resources.
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdtemp,rm,readdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {GR4_OFFICIAL_SHA256,validateGr4Source} from './gr4-m10v-native-build.mjs';
const root=fileURLToPath(new URL('..',import.meta.url)),run=promisify(execFile),hash=b=>createHash('sha256').update(b).digest('hex');
const known=['variant','features','recipes','filmIds','filmLibrary','filmTexture','stockPresets','negativeGrainMenu','rawNr'];
export function normalizeGr4Customization(input){
 if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!known.includes(k)))throw Error('方案包含未知字段');
 if(!Array.isArray(input.features)||!input.features.length||new Set(input.features).size!==input.features.length||input.features.some(f=>!['recipes','presets','aspect','level','negativeGrain','rawNr'].includes(f)))throw Error('GR IV 配方工具支持配方、原厂名称图标和已验证扩展；胶片和时间戳请使用胶卷库');
 if(!Array.isArray(input.recipes??[])||!Array.isArray(input.stockPresets??[])||(input.recipes?.length||0)>6||(input.stockPresets?.length||0)>20)throw Error('配方或原厂预设列表无效');
 return structuredClone({...input,recipes:input.recipes??[],stockPresets:input.stockPresets??[]});
}
async function engineHash(){
 const files=['node/gr4-customization.mjs'];
 async function walk(folder){for(const entry of await readdir(path.join(root,folder),{withFileTypes:true})){
  if(entry.name.startsWith('.')||entry.name==='__pycache__')continue;
  const name=folder+'/'+entry.name;if(entry.isDirectory())await walk(name);
  else if(/\.(py|c|h|json|rgba|bin)$/.test(name))files.push(name);
 }}
 await walk('.runtime/grlife-current/reconstruction/firmware_store');await walk('native/gr4');await walk('vendor/gr4/gr4_editor');
 for(const name of await readdir(path.join(root,'scripts')))if(/^build_gr4_.*\.py$/.test(name))files.push('scripts/'+name);
 return hash(JSON.stringify(await Promise.all([...new Set(files)].sort().map(async f=>[f,hash(await readFile(path.join(root,f)))]))));
}

async function invoke(source,selection,{check=false,catalog=false,signal}={}){
 validateGr4Source(source);const folder=await mkdtemp(path.join(os.tmpdir(),'m10v-gr4-custom-'));
 try{
  const firmware=path.join(folder,'official.bin'),config=path.join(folder,'configuration.json'),reportPath=path.join(folder,'report.json'),output=path.join(folder,'fwdc248b.bin');
  await writeFile(firmware,source,{mode:0o400});await writeFile(config,JSON.stringify(selection??{}));
  const bundled=path.join(root,'.venv/bin/python'),python=process.env.M10V_PYTHON||(existsSync(bundled)?bundled:'python3');
  await run(python,['scripts/build_gr4_custom_firmware.py','--input',firmware,'--report',reportPath,...(catalog?['--catalog']:['--config',config,...(check?['--check']:['--output',output])])],{cwd:root,signal,timeout:300000,maxBuffer:2*1024*1024,env:{...process.env,M10V_NODE:process.execPath}});
  const report=JSON.parse(await readFile(reportPath,'utf8'));
  if(catalog)return report;
  if(report.ready!==true||report.source_sha256!==GR4_OFFICIAL_SHA256||report.camera_tested!==false||report.canonical_source_recovered!==true)throw Error('GR IV 自定义固件独立回读失败');
  if(check)return {report};
  const candidate=await readFile(output);if(hash(candidate)!==report.candidate_sha256||candidate.length!==report.candidate_bytes)throw Error('GR IV 自定义固件摘要不一致');
  return {candidate,report};
 }finally{await rm(folder,{recursive:true,force:true});}
}
let catalogPromise;export async function gr4StockPresetCapabilities(source,{signal}={}){validateGr4Source(source);catalogPromise??=invoke(source,null,{catalog:true,signal}).catch(e=>{catalogPromise=null;throw e;});return structuredClone(await catalogPromise);}
export async function prepareGr4Customization(source,input,{signal}={}){
 const selection=normalizeGr4Customization(input),engine=await engineHash();const {report}=await invoke(source,selection,{check:true,signal});
 return {...report,features:selection.features,configuration_sha256:hash(JSON.stringify({source:GR4_OFFICIAL_SHA256,selection,engine})),engine_sha256:engine,blockers:[]};
}
let building=false;export async function buildGr4Customization(source,input,accepted,{signal}={}){
 if(building)throw Error('另一个 GR IV 自定义固件正在构建');building=true;
 try{
  const selection=normalizeGr4Customization(input),engine=await engineHash();const expected=hash(JSON.stringify({source:GR4_OFFICIAL_SHA256,selection,engine}));
  if(accepted!==expected)throw Error('方案或构建源已变化，请重新预检');
  const {candidate,report}=await invoke(source,selection,{signal});if(await engineHash()!==engine)throw Error('GR IV 构建源已变化，请重新预检');
  return {candidate,receipt:{...report,configuration_sha256:expected,engine_sha256:engine}};
 }finally{building=false;}
}
export async function handleGr4CustomizationRequest({request,response,runtime,token,readBody,send,origin}){
 const match=/^\/api\/gr4\/customization\/([0-9a-f]{64})\/(stock-presets|prepare|build)$/.exec(request.url||'');if(!match)return false;
 try{
  if(request.headers['x-m10v-token']!==token||(request.headers.origin&&request.headers.origin!==origin))return send(response,403,{error:'authorization failed'}),true;
  if(match[1]!==GR4_OFFICIAL_SHA256)throw Error('GR IV 项目标识无效');const source=await readFile(path.join(runtime.root,'inputs',match[1]+'.bin'));validateGr4Source(source);
  const controller=new AbortController();response.on('close',()=>{if(!response.writableEnded)controller.abort();});
  if(request.method==='GET'&&match[2]==='stock-presets')return send(response,200,await gr4StockPresetCapabilities(source,{signal:controller.signal})),true;
  if(request.method!=='POST')return send(response,405,{error:'POST required'}),true;
  const body=JSON.parse((await readBody(request,512*1024)).toString('utf8')||'{}');
  if(match[2]==='prepare')return send(response,200,await prepareGr4Customization(source,body.selection,{signal:controller.signal})),true;
  if(match[2]==='build'){const {candidate,receipt}=await buildGr4Customization(source,body.selection,body.accepted_configuration_sha256,{signal:controller.signal});response.setHeader('X-M10V-Custom-Receipt',Buffer.from(JSON.stringify(Object.fromEntries(['model','filename','ready','camera_tested','source_sha256','candidate_sha256','candidate_bytes','configuration_sha256','engine_sha256','canonical_source_recovered','reset_required','custom_styles'].map(k=>[k,receipt[k]])))).toString('base64'));return send(response,200,candidate,'application/octet-stream','fwdc248b.bin'),true;}
  return send(response,404,{error:'接口不存在'}),true;
 }catch(error){send(response,400,{error:error.message});return true;}
}
