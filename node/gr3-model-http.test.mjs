import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createServer} from './server.mjs';
import {Store} from './storage.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
test('IIIx web export downloads the complete shared ISP ten-film HDF and halation bundle',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-parity-http-')),server=createServer(new Store(dir));
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base='http://127.0.0.1:'+server.address().port;
 try{
  const {session_token}=await(await fetch(base+'/api/status')).json();
  const post=(url,body)=>fetch(base+url,{method:'POST',headers:{'Content-Type':'application/json','X-M10V-Token':session_token},body:JSON.stringify(body)});
  const imported=await post('/api/gr3/native-library/import-official',{model:'gr3x'});assert.equal(imported.status,200);
  const {project_id}=await imported.json(),route='/api/projects/'+project_id+'/native-library/';
  const configuration=defaultConfiguration('gr3x'),template=configuration.slots[0];
  configuration.slots=[33,66,67,68,294,306,307,308,310,311].map(film=>({...structuredClone(template),film}));
  configuration.slots[1].grain=1;configuration.zoom={write:true,slots:[50,71],revision:1};
  const body={configuration,debug_mode:true,hdf_enabled:true,halation_enabled:true,extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
  const prepared=await post(route+'prepare',body);assert.equal(prepared.status,200);const plan=await prepared.json();
  assert.equal(plan.active_slots,10);assert.equal(plan.live_color,true);assert.equal(plan.capture_pipeline,'gr3-native-v8');
  const stale=await post(route+'build',{...body,accepted_configuration_sha256:'0'.repeat(64)});assert.equal(stale.status,400);
  const response=await post(route+'build',{...body,accepted_configuration_sha256:plan.configuration_sha256});
  assert.equal(response.status,200,response.status===200?'':await response.text());
  const receipt=JSON.parse(Buffer.from(response.headers.get('X-M10V-Native-Receipt'),'base64'));
  const bytes=Buffer.from(await response.arrayBuffer());
  assert.equal(receipt.candidate_sha256,createHash('sha256').update(bytes).digest('hex'));
  assert.equal(receipt.model,'GR IIIx');assert.equal(receipt.capture_pipeline,'gr3-native-v8');
  assert.equal(receipt.active_slots,10);assert.equal(receipt.live_view_base.film_color_preview,true);
  assert.ok(receipt.features.includes('grain')&&receipt.features.includes('digitalHdf')&&receipt.features.includes('halation'));
  assert.deepEqual(receipt.still_isp_base.carriers,[25,26,27,28,29,30,31,32,33,34]);
  assert.equal(receipt.gr3x_port.checks.cpu_payload_unchanged,true);assert.equal(receipt.gr3x_port.model_words.length,19);
  assert.equal(bytes.readUInt32LE(0x30),609);assert.equal(receipt.camera_tested,false);
 }finally{await new Promise(resolve=>server.close(resolve));await rm(dir,{recursive:true,force:true});}
});
