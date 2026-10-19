import test from 'node:test';import assert from 'node:assert/strict';
import {createServer} from './server.mjs';
import {auditSdFilmPack} from './gr3-sd-film-pack.mjs';
test('SD export endpoint is authenticated, serves complete subsets and rejects bad input',async()=>{
 const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=`http://127.0.0.1:${server.address().port}`;
 try{
  const {session_token}=await(await fetch(base+'/api/status')).json();
  const post=(v,token=session_token)=>fetch(base+'/api/gr3/sd-library/export',{method:'POST',headers:{'Content-Type':'application/json','X-M10V-Token':token},body:JSON.stringify(v)});
  assert.equal((await post({ids:[33]},'bad')).status,403);
  for(const v of [{ids:[]},{ids:[1]},{ids:[33,33]},{ids:[33],model:'gr4'},{ids:[33],extra:1},{}])assert.equal((await post(v)).status,400);
  assert.equal((await post({ids:[33],model:'gr3x'})).status,200);
  const res=await post({ids:[65,33,50]});assert.equal(res.status,200);assert.equal(res.headers.get('content-type'),'application/zip');
  const b=Buffer.from(await res.arrayBuffer());let at=0;const entries=new Map();
  while(b.readUInt32LE(at)===0x04034b50){const size=b.readUInt32LE(at+18),nl=b.readUInt16LE(at+26),el=b.readUInt16LE(at+28),start=at+30+nl+el;entries.set(b.toString('utf8',at+30,at+30+nl),b.subarray(start,start+size));at=start+size;}
  assert.deepEqual(auditSdFilmPack(entries.get('SD/M10V/FILMS.M10')).ids,[33,65,50]);assert.ok(entries.get('README.txt').toString().includes('GR III'));
  assert.equal((await fetch(base+'/gr3/sd-library.html')).status,200);
 }finally{await new Promise(r=>server.close(r));}
});
