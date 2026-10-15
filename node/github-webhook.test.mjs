import test from 'node:test';import assert from 'node:assert/strict';
import {createHmac} from 'node:crypto';import {mkdtemp,rm,readFile} from 'node:fs/promises';import os from 'node:os';import path from 'node:path';
import {verifyDelivery,createReceiver} from '../deploy/github-webhook.mjs';
const secret='a'.repeat(64),sha='b'.repeat(40);
const payload=(after=sha)=>Buffer.from(JSON.stringify({repository:{full_name:'zhaoo/m10v'},ref:'refs/heads/main',after}));
const headers=body=>({'x-github-event':'push','x-hub-signature-256':'sha256='+createHmac('sha256',secret).update(body).digest('hex')});
test('webhook requires exact raw HMAC, repository, main branch and SHA',()=>{
 const b=payload();assert.equal(verifyDelivery(b,headers(b),secret).sha,sha);
 assert.equal(verifyDelivery(Buffer.concat([b,Buffer.from(' ')]),headers(b),secret).status,401);
 assert.equal(verifyDelivery(b,{},secret).status,401);
 for(const change of [{ref:'refs/heads/develop'},{deleted:true},{repository:{full_name:'evil/repo'}}]){
  const p=Buffer.from(JSON.stringify({...JSON.parse(b),...change}));assert.equal(verifyDelivery(p,headers(p),secret).ignored,true);
 }
 const p=payload('$(touch /tmp/evil)');assert.equal(verifyDelivery(p,headers(p),secret).status,400);
 const broken=Buffer.from('{');assert.equal(verifyDelivery(broken,headers(broken),secret).status,400);
 assert.equal(verifyDelivery(b,{...headers(b),'x-github-event':'ping'},secret).status,200);
});
test('queue serializes deployments, coalesces new pushes and survives duplicate delivery',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-hooks-')),calls=[];let release;
 const server=createReceiver({secret,stateDir:dir,deploy:async value=>{calls.push(value);if(calls.length===1)await new Promise(r=>release=r);}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const post=async s=>{const b=payload(s);return fetch(`http://127.0.0.1:${server.address().port}/hooks/github`,{method:'POST',headers:headers(b),body:b});};
 try{
  assert.equal((await post(sha)).status,202);
  while(!release)await new Promise(r=>setTimeout(r,5));
  await post(sha);await post('c'.repeat(40));await post('d'.repeat(40));release();
  let state;for(let i=0;i<100;i++){state=JSON.parse(await readFile(path.join(dir,'state.json')));if(state.deployed==='d'.repeat(40))break;await new Promise(r=>setTimeout(r,5));}
  assert.deepEqual(calls,[sha,'d'.repeat(40)]);assert.equal(state.lastResult.ok,true);
  await post('d'.repeat(40));assert.equal(calls.length,2);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
test('public hook proxy reaches signature receiver without exposing the browser session token',async()=>{
 const {createServer}=await import('./server.mjs');
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-hook-proxy-'));
 const receiver=createReceiver({secret,stateDir:dir,deploy:async()=>{}});
 await new Promise((r,j)=>{receiver.once('error',j);receiver.listen(3001,'127.0.0.1',r);});
 const app=createServer();await new Promise(r=>app.listen(0,'127.0.0.1',r));
 const url=`http://127.0.0.1:${app.address().port}/hooks/github`;
 try{
  assert.equal((await fetch(url,{method:'POST',body:payload()})).status,401);
  const b=payload();assert.equal((await fetch(url,{method:'POST',headers:headers(b),body:b})).status,202);
  assert.equal((await fetch(url)).status,405);
 }finally{await new Promise(r=>app.close(r));await new Promise(r=>receiver.close(r));await rm(dir,{recursive:true,force:true});}
});
test('receiver restores interrupted deployments and persists failures',async()=>{
 const {writeFile}=await import('node:fs/promises');
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-hook-restart-'));
 await writeFile(path.join(dir,'state.json'),JSON.stringify({pending:null,running:sha,deployed:null,lastResult:null}));
 let called=false;
 const server=createReceiver({secret,stateDir:dir,deploy:async value=>{assert.equal(value,sha);called=true;throw Error('build failed');}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 try{
  let state;for(let i=0;i<100;i++){state=JSON.parse(await readFile(path.join(dir,'state.json')));if(state.lastResult)break;await new Promise(r=>setTimeout(r,5));}
  assert.equal(called,true);assert.equal(state.deployed,null);assert.equal(state.running,null);assert.equal(state.lastResult.ok,false);assert.match(state.lastResult.error,/build failed/);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
test('signed bundle is persisted and passed to fixed deployment executor',async()=>{
 const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-hook-bundle-'));let seen;
 const bundle=Buffer.from('# v2 git bundle\nfixture');
 const b=Buffer.from(JSON.stringify({...JSON.parse(payload()),bundle:bundle.toString('base64')}));
 const server=createReceiver({secret,stateDir:dir,deploy:async(value,file)=>{assert.equal(value,sha);assert.deepEqual(await readFile(file),bundle);seen=true;}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 try{
  const response=await fetch(`http://127.0.0.1:${server.address().port}/hooks/github`,{method:'POST',headers:headers(b),body:b});assert.equal(response.status,202);
  const status=await fetch(`http://127.0.0.1:${server.address().port}/hooks/github`,{method:'POST',headers:{...headers(b),'x-github-event':'m10v-status'},body:b});assert.equal(status.status,200);assert.ok('deployed' in await status.json());
  for(let i=0;i<100&&!seen;i++)await new Promise(r=>setTimeout(r,5));assert.equal(seen,true);
  const bad=Buffer.from(JSON.stringify({...JSON.parse(payload()),bundle:'not a bundle'}));assert.equal(verifyDelivery(bad,headers(bad),secret).status,400);
 }finally{await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
});
