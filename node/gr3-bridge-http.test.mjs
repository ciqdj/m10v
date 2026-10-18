import {test} from 'node:test';import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import {createServer} from './server.mjs';import {Store} from './storage.mjs';
test('bridge HTTP requires source, plan and acknowledgement and returns two distinct stages',async()=>{
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
  const response=await post('export',{accepted_plan_id:plan.plan_id,acknowledge_instructions:true});assert.equal(response.status,200);assert.equal(response.headers.get('content-type'),'application/zip');assert.match(response.headers.get('content-disposition'),/bridge-2.10.22.27\.zip/);assert.doesNotMatch(response.headers.get('content-disposition'),/EXPERIMENTAL/);
  const b=Buffer.from(await response.arrayBuffer());assert.equal(b.readUInt32LE(0),0x04034b50);
  let pos=0,files={};while(b.readUInt32LE(pos)===0x04034b50){const n=b.readUInt16LE(pos+26),size=b.readUInt32LE(pos+18),start=pos+30+n;files[b.toString('utf8',pos+30,start)]=b.subarray(start,start+size);pos=start+size;}
  assert.deepEqual(files['stage-2-official/fwdc239b.bin'],original);
  assert.equal(files['stage-1-bridge/fwdc239b.bin'].readUInt32BE(0x38),0x020a161b);
  assert.equal(JSON.parse(files['receipt.json']).camera_verified,true);assert.match(files['README.txt'].toString(),/2.10.22.27/);
  assert.doesNotMatch(files['README.txt'].toString(),/实机未验证|实验候选|测试包/);
  const x=await store.importOfficial(await readFile(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url)));
  const res=await fetch(`${base}/api/projects/${x.id}/bridge/prepare`,{method:'POST',headers:{'X-M10V-Token':token},body:'{}'});assert.equal(res.status,400);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
