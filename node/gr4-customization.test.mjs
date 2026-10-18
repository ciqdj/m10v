import test from 'node:test';import assert from 'node:assert/strict';
import {readFile,mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';import path from 'node:path';import os from 'node:os';
import {normalizeGr4Customization,gr4StockPresetCapabilities,prepareGr4Customization,buildGr4Customization} from './gr4-customization.mjs';
import {createServer} from './server.mjs';import {Store} from './storage.mjs';import {Gr4Runtime} from './gr4-runtime.mjs';
import {GR4_OFFICIAL_SHA256} from './gr4-m10v-native-build.mjs';
const fields=['saturation','hue','high_low_key','contrast','highlight_contrast','shadow_contrast','sharpness','shading','clarity'];
const selection={variant:'street',features:['recipes'],recipes:[{slotId:'builtin-0b',cameraName:'GR4 TEST',parameters:Object.fromEntries(fields.map(k=>[k,0])),iconMode:'original',source:'manual'}]};
test('GR IV customization normalizer rejects film/native mix and unknown input',()=>{
 assert.deepEqual(normalizeGr4Customization(selection).recipes,selection.recipes);
 for(const bad of [{...selection,features:['film','recipes']},{...selection,features:['recipes','recipes']},{...selection,unknown:true}])assert.throws(()=>normalizeGr4Customization(bad));
});
test('GR IV actual native capabilities and custom prepare are model-specific',{timeout:120000},async()=>{
 const source=await readFile(new URL('../bin/fwdc248b-gr4-officical.bin',import.meta.url));
 const caps=await gr4StockPresetCapabilities(source);assert.equal(caps.length,20);assert.deepEqual(caps.map(x=>x.slot).sort((a,b)=>a-b),Array.from({length:20},(_,i)=>i+11));
 assert.ok(caps.every(x=>Buffer.from(x.iconPixelsBase64,'base64').length===6400&&x.canRename));
 const report=await prepareGr4Customization(source,selection);assert.equal(report.ready,true);assert.equal(report.model,'GR IV');assert.equal(report.filename,'fwdc248b.bin');assert.equal(report.reset_required,true);assert.match(report.configuration_sha256,/^[0-9a-f]{64}$/);
 await assert.rejects(buildGr4Customization(source,selection,'0'.repeat(64)),/重新预检/);
});
test('GR IV custom API has independent route and authorization',{timeout:120000},async()=>{
 const folder=await mkdtemp(path.join(os.tmpdir(),'gr4-custom-route-')),runtime=new Gr4Runtime(path.join(folder,'gr4'));await mkdir(path.join(runtime.root,'inputs'),{recursive:true});await writeFile(path.join(runtime.root,'inputs',GR4_OFFICIAL_SHA256+'.bin'),await readFile(new URL('../bin/fwdc248b-gr4-officical.bin',import.meta.url)));
 const server=createServer(new Store(folder),undefined,runtime);await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{
  const endpoint=base+'/api/gr4/customization/'+GR4_OFFICIAL_SHA256+'/stock-presets';assert.equal((await fetch(endpoint)).status,403);
  const status=await(await fetch(base+'/api/status')).json();const response=await fetch(endpoint,{headers:{'X-M10V-Token':status.session_token}});assert.equal(response.status,200);assert.equal((await response.json()).length,20);
  const wrong=await fetch(endpoint,{headers:{'X-M10V-Token':status.session_token,Origin:'https://unexpected.example'}});assert.equal(wrong.status,403);
 }finally{await new Promise(r=>server.close(r));await rm(folder,{recursive:true,force:true});}
});
