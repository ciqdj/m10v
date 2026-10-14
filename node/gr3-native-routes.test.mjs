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
  const data=await catalog.json();assert.equal(data.films.length,65);assert.equal(data.external_film_pack,false);
  const post=(url,body,auth=true)=>fetch(base+url,{method:'POST',headers:{'Content-Type':'application/json',...(auth?{'X-M10V-Token':status.session_token}:{})},body:JSON.stringify(body)});
  assert.equal((await post('/api/gr3/native-library/import-official',{},false)).status,403);
  const ximport=await post('/api/gr3/native-library/import-official',{model:'gr3x'});assert.equal(ximport.status,200);const xid=(await ximport.json()).project_id;
  const imported=await post('/api/gr3/native-library/import-official',{});assert.equal(imported.status,200);
  const {project_id:id}=await imported.json();
  const route=`/api/projects/${id}/native-library/`;
  const config=normalizeConfiguration({slots:[{film:33,grain:3,soft:2},{film:7,grain:1,soft:3},{film:16,grain:0,soft:1},{film:21,grain:2,soft:0},{film:1,grain:0,soft:0}],stamp:2,format:3,corner:2,color:1});
  assert.equal((await post(route+'prepare',{configuration:{...config,stamp:9}})).status,400);
  const p=await post(route+'prepare',{configuration:config});assert.equal(p.status,200);const plan=await p.json();
  assert.deepEqual(plan.configuration,config);
  const stale=await post(route+'build',{configuration:config,accepted_configuration_sha256:'0'.repeat(64)});assert.equal(stale.status,400);
  const built=await post(route+'build',{configuration:config,accepted_configuration_sha256:plan.configuration_sha256});
  assert.equal(built.status,200,await built.clone().text());
  const bytes=Buffer.from(await built.arrayBuffer());const receipt=JSON.parse(Buffer.from(built.headers.get('X-M10V-Native-Receipt'),'base64'));
  assert.equal(receipt.candidate_sha256,createHash('sha256').update(bytes).digest('hex'));
  assert.deepEqual(receipt.configuration,config);assert.equal(receipt.camera_tested,false);assert.equal(receipt.verified_hooks,27);
  const xp=await (await post(`/api/projects/${xid}/native-library/prepare`,{configuration:config})).json();assert.equal(xp.model,'GR IIIx');assert.equal(xp.filename,'fwdc243b.bin');
  const xb=await post(`/api/projects/${xid}/native-library/build`,{configuration:config,accepted_configuration_sha256:xp.configuration_sha256});assert.equal(xb.status,200);assert.ok(xb.headers.get('Content-Disposition').includes('fwdc243b.bin'));
  const xr=JSON.parse(Buffer.from(xb.headers.get('X-M10V-Native-Receipt'),'base64'));assert.equal(xr.model,'GR IIIx');assert.equal(xr.source_sha256,xid);assert.equal(xr.candidate_sha256,createHash('sha256').update(Buffer.from(await xb.arrayBuffer())).digest('hex'));
  assert.equal(receipt.external_film_pack,false);assert.equal(receipt.initial_state_hex.length,128);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
