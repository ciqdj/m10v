import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createServer} from './server.mjs';
import {Store} from './storage.mjs';
import {normalizeConfiguration} from '../web/gr3/native-library-state.mjs';
import {createHash} from 'node:crypto';

test('original M10V web workflow binds all five slots and timestamp into audited firmware',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-web-native-'));
 const server=createServer(new Store(dir)); await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;
 try{
  for(const asset of ['native-library.html','native-library.js','native-library.css','native-library-state.mjs'])assert.equal((await fetch(base+'/gr3/'+asset)).status,200);
  const workspace=await (await fetch(base+'/gr3/')).text();assert.ok(workspace.includes('id="native-editor"'));
  const status=await (await fetch(base+'/api/status')).json();
  const catalog=await fetch(base+'/api/gr3/native-library/catalog'); assert.equal(catalog.status,200);
  const data=await catalog.json();assert.equal(data.films.length,33);assert.deepEqual(data.films.filter(f=>f.group==='M10V精选').map(f=>f.name),['800T']);assert.ok(data.films.every(f=>f.id>=33));assert.equal(data.external_film_pack,true);
  const post=(url,body,auth=true)=>fetch(base+url,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{'X-M10V-Token':status.session_token}:{})},body:JSON.stringify(body)});
  assert.equal((await post('/api/gr3/native-library/import-official',{},false)).status,403);
  const ximport=await post('/api/gr3/native-library/import-official',{model:'gr3x'});assert.equal(ximport.status,200);const xid=(await ximport.json()).project_id;
  const imported=await post('/api/gr3/native-library/import-official',{});assert.equal(imported.status,200);
  const {project_id:id}=await imported.json();
  const route=`/api/projects/${id}/native-library/`;
  const config=normalizeConfiguration({slots:[{film:33,grain:3,soft:2},{film:7,grain:1,soft:3},{film:16,grain:0,soft:1},{film:21,grain:2,soft:0},{film:1,grain:0,soft:0}],stamp:2,format:3,corner:2,color:1});
  assert.equal((await post(route+'prepare',{configuration:{...config,stamp:9}})).status,400);
  const nrExtensions={aspect:false,level:false,negativeGrain:false,rawNr:{mode:'off'}};
  for(const rawNr of [{mode:'stock'},{mode:'off'},{mode:'threshold',iso:6400}]){
   const nr=await post(route+'prepare',{configuration:config,extensions:{...nrExtensions,rawNr}});
   assert.equal(nr.status,200);assert.deepEqual((await nr.json()).extensions.rawNr,rawNr);
  }
  assert.equal((await post(route+'prepare',{configuration:config,extensions:{...nrExtensions,rawNr:{mode:'threshold',iso:6300}}})).status,400);
  assert.equal((await post(`/api/projects/${xid}/native-library/prepare`,{configuration:config,extensions:nrExtensions})).status,400);
  const p=await post(route+'prepare',{configuration:config});assert.equal(p.status,200);const plan=await p.json();
  assert.deepEqual(plan.configuration,config);assert.equal(plan.debug_mode,false);
  assert.equal((await post(`/api/projects/${xid}/native-library/prepare`,{configuration:config,debug_mode:true})).status,400);
  const dp=await post(route+'prepare',{configuration:config,debug_mode:true});assert.equal(dp.status,200);const debugPlan=await dp.json();
  assert.notEqual(debugPlan.configuration_sha256,plan.configuration_sha256);
  assert.equal((await post(route+'build',{configuration:config,debug_mode:true,accepted_configuration_sha256:plan.configuration_sha256})).status,400);
  const stale=await post(route+'build',{configuration:config,accepted_configuration_sha256:'0'.repeat(64)});assert.equal(stale.status,400);
  const built=await post(route+'build',{configuration:config,accepted_configuration_sha256:plan.configuration_sha256});
  assert.equal(built.status,200,await built.clone().text());
  const bytes=Buffer.from(await built.arrayBuffer());const receipt=JSON.parse(Buffer.from(built.headers.get('X-M10V-Native-Receipt'),'base64'));
  assert.equal(receipt.candidate_sha256,createHash('sha256').update(bytes).digest('hex'));
  assert.deepEqual(receipt.configuration,config);assert.equal(receipt.camera_tested,false);assert.equal(receipt.verified_hooks,34);
  const xp=await (await post(`/api/projects/${xid}/native-library/prepare`,{configuration:config})).json();assert.equal(xp.model,'GR IIIx');assert.equal(xp.filename,'fwdc243b.bin');
  const xb=await post(`/api/projects/${xid}/native-library/build`,{configuration:config,accepted_configuration_sha256:xp.configuration_sha256});assert.equal(xb.status,200);assert.ok(xb.headers.get('Content-Disposition').includes('fwdc243b.bin'));
  const xr=JSON.parse(Buffer.from(xb.headers.get('X-M10V-Native-Receipt'),'base64'));assert.equal(xr.model,'GR IIIx');assert.equal(xr.source_sha256,xid);assert.equal(xr.candidate_sha256,createHash('sha256').update(Buffer.from(await xb.arrayBuffer())).digest('hex'));
  const nrPlan=await (await post(route+'prepare',{configuration:config,extensions:nrExtensions})).json();
  assert.equal((await post(route+'build',{configuration:config,extensions:nrExtensions,accepted_configuration_sha256:plan.configuration_sha256})).status,400);
  const nrBuilt=await post(route+'build',{configuration:config,extensions:nrExtensions,accepted_configuration_sha256:nrPlan.configuration_sha256});
  assert.equal(nrBuilt.status,200,nrBuilt.status===200?'':await nrBuilt.text());
  const nrReceipt=JSON.parse(Buffer.from(nrBuilt.headers.get('X-M10V-Native-Receipt'),'base64'));
  assert.equal(nrReceipt.composition.raw_nr.patch_count,3);assert.deepEqual(nrReceipt.extensions,nrExtensions);
  assert.equal(nrReceipt.candidate_sha256,createHash('sha256').update(Buffer.from(await nrBuilt.arrayBuffer())).digest('hex'));
  assert.equal(receipt.debug_mode,false);
  const debugBuilt=await post(route+'build',{configuration:config,debug_mode:true,accepted_configuration_sha256:debugPlan.configuration_sha256});
  assert.equal(debugBuilt.status,200,debugBuilt.status===200?'':await debugBuilt.text());
  const debugReceipt=JSON.parse(Buffer.from(debugBuilt.headers.get('X-M10V-Native-Receipt'),'base64'));
  assert.equal(debugReceipt.debug_mode,true);assert.equal(debugReceipt.debug_log.build_id,debugPlan.configuration_sha256.slice(0,8));
  assert.equal(debugReceipt.candidate_sha256,createHash('sha256').update(Buffer.from(await debugBuilt.arrayBuffer())).digest('hex'));
  assert.notEqual(debugReceipt.candidate_sha256,receipt.candidate_sha256);assert.equal(debugReceipt.verified_hooks,34);
  assert.equal(receipt.external_film_pack,true);assert.equal(receipt.initial_state_hex.length,128);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
