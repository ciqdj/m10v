import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm} from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {createServer} from './server.mjs';
import {Store} from './storage.mjs';
import {Gr4Runtime} from './gr4-runtime.mjs';
import {defaultConfiguration} from '../web/gr2/native-library-state.mjs';
test('GR2 HTTP import, authenticated preparation, native download and SD pack',async()=>{
 const folder=await mkdtemp(path.join(os.tmpdir(),'m10v-gr2-http-')),server=createServer(new Store(folder),undefined,new Gr4Runtime(path.join(folder,'gr4')));
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base='http://127.0.0.1:'+server.address().port;
 try{
  assert.match(await(await fetch(base+'/gr2/')).text(),/GR II 胶卷工作台/);
  assert.equal((await fetch(base+'/gr2/workbench.js')).status,200);
  assert.match(await(await fetch(base+'/gr2/inspect/')).text(),/GR/);
  const token=(await(await fetch(base+'/api/status')).json()).session_token;
  const post=(route,body={},headers={})=>fetch(base+'/api/gr2/native-library/'+route,{method:'POST',headers:{'x-m10v-token':token,'Content-Type':'application/json',...headers},body:JSON.stringify(body)});
  assert.equal((await post('import-official',{}, {'x-m10v-token':''})).status,403);
  assert.equal((await post('import-official',{}, {origin:'http://evil.example'})).status,403);
  const imported=await post('import-official');assert.equal(imported.status,200);const {project_id}=await imported.json(),configuration=defaultConfiguration();
  const input={project_id,configuration};const p=await post('prepare',input);assert.equal(p.status,200);const plan=await p.json();
  assert.equal((await post('build',{...input,configuration_sha256:'stale'})).status,400);
  const result=await post('build',{...input,configuration_sha256:plan.configuration_sha256});assert.equal(result.status,200,await result.clone().text());
  const receipt=JSON.parse(Buffer.from(result.headers.get('X-M10V-Native-Receipt'),'base64'));assert.equal(receipt.verified,true);assert.equal(receipt.hardware_verified,false);assert.ok((await result.arrayBuffer()).byteLength>14033920);
  const pack=await post('sd-export',{project_id,ids:[33,67,68]});assert.equal(pack.status,200);assert.equal(Buffer.from(await pack.arrayBuffer()).readUInt32LE(),0x04034b50);
 }finally{await new Promise(resolve=>server.close(resolve));await rm(folder,{recursive:true,force:true});}
});
