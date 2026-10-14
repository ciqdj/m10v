import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync,existsSync } from 'node:fs';
import { createServer } from './server.mjs';
const source=new URL('../fwdc239b.bin',import.meta.url);
test('800T routes require local token and matching preflight before audited BIN download',{skip:!existsSync(source)},async()=>{
 const bytes=readFileSync(source);let reads=0;
 const server=createServer({readOriginal:async(id)=>{assert.equal(id,'a'.repeat(64));reads++;return bytes;}});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 try {
  const status=await(await fetch(base+'/api/status')).json();
  const route=base+'/api/projects/'+'a'.repeat(64)+'/800t/';
  const selection={strength:'strong',timestamp:true};
  assert.equal((await fetch(route+'prepare',{method:'POST',body:JSON.stringify({selection})})).status,403);
  const headers={'X-M10V-Token':status.session_token,'Content-Type':'application/json'};
  const prep=await fetch(route+'prepare',{method:'POST',headers,body:JSON.stringify({selection})});
  assert.equal(prep.status,200);const report=await prep.json();assert.equal(report.ready,true);assert.equal(report.camera_tested,false);
  const stale=await fetch(route+'build',{method:'POST',headers,body:JSON.stringify({selection,accepted_configuration_sha256:'0'.repeat(64),ready:true})});
  assert.equal(stale.status,400);
  const generated=await fetch(route+'build',{method:'POST',headers,body:JSON.stringify({selection,accepted_configuration_sha256:report.configuration_sha256})});
  assert.equal(generated.status,200);assert.match(generated.headers.get('Content-Type'),/octet-stream/);
  const receipt=JSON.parse(Buffer.from(generated.headers.get('X-M10V-800T-Receipt'),'base64'));
  assert.equal(receipt.offline_audit_passed,true);assert.equal(receipt.camera_tested,false);
  assert.equal(receipt.configuration.strength,'strong');assert.equal(receipt.configuration.timestamp,true);
  assert.ok((await generated.arrayBuffer()).byteLength>bytes.length);
  assert.equal((await fetch(route+'prepare',{method:'POST',headers,body:JSON.stringify({selection:{...selection,firmwareReady:true}})})).status,400);
  assert.equal((await fetch(route+'prepare',{method:'POST',headers:{...headers,Origin:'https://example.org'},body:'{}'})).status,403);
  assert.equal(reads,4);
 } finally {await new Promise(r=>server.close(r));}
});
