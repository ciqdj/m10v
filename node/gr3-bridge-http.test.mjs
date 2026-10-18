import {test} from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import {createServer} from './server.mjs';import {Store} from './storage.mjs';
test('bridge HTTP preserves authentication and blocks withdrawn downloads for old and new plans',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-bridge-http-')),store=new Store(dir),server=createServer(store);
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{
  const original=await readFile(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url)),record=await store.importOfficial(original);
  const url=`${base}/api/projects/${record.id}/bridge/`;
  assert.equal((await fetch(url+'prepare',{method:'POST',body:'{}'})).status,403);
  const token=(await(await fetch(base+'/api/status')).json()).session_token;
  const post=(route,data,extra={})=>fetch(url+route,{method:'POST',headers:{'X-M10V-Token':token,'Content-Type':'application/json',...extra},body:JSON.stringify(data)});
  assert.equal((await post('prepare',{}, {Origin:'https://invalid.example'})).status,403);
  const pre=await post('prepare',{});assert.equal(pre.status,200);const plan=await pre.json();assert.equal(plan.hardware_verification.source,'user_report');assert.equal(plan.package_version,'2.10.22.27');
  assert.equal((await post('export',{})).status,400);
  assert.equal((await post('export',{accepted_plan_id:'stale',acknowledge_instructions:true})).status,400);
  assert.equal(plan.camera_verified,false);assert.equal(plan.download_available,false);
  assert.equal(plan.hardware_verification.status,'failed');
  // A previously accepted plan must not retrieve the withdrawn binary either.
  for(const planId of [plan.plan_id,'stale']){
   const response=await post('export',{accepted_plan_id:planId,acknowledge_instructions:true});
   assert.equal(response.status,400);assert.match(await response.text(),/暂停下载/);
   assert.notEqual(response.headers.get('content-type'),'application/zip');
  }
  const x=await store.importOfficial(await readFile(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url)));
  const res=await fetch(`${base}/api/projects/${x.id}/bridge/prepare`,{method:'POST',headers:{'X-M10V-Token':token},body:'{}'});assert.equal(res.status,400);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
