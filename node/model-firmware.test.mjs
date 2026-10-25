import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {createServer} from './server.mjs';
const gr2 = new URL('../bin/rg2_v003.frm',import.meta.url);
const gr1 = new URL('../bin/rg1_v051.frm',import.meta.url);
const gr4 = new URL('../bin/fwdc248b-gr4-officical.bin',import.meta.url);
const implementation = new URL('./model-firmware.mjs',import.meta.url);
async function module(){assert.ok(existsSync(implementation),'multi-model firmware inspection is not implemented');return import(implementation);}
test('local GR II source uses the supplied root sample path',{skip:!existsSync(gr2)},async()=>{
  const {readModelOfficial}=await module();
  assert.deepEqual(await readModelOfficial('gr2'),readFileSync(gr2));
});
test('GR content identity selects its own inventory and local source',{skip:!existsSync(gr1)},async()=>{
  const {inspectModelFirmware,readModelOfficial}=await module();
  const source=readFileSync(gr1),report=await inspectModelFirmware(source);
  assert.equal(report.model,'GR');assert.equal(report.workspace_url,'/gr1/');
  assert.equal(report.resources.length,119);
  assert.deepEqual(await readModelOfficial('gr1'),source);
});
test('content identity selects GR II regardless of original filename', {skip:!existsSync(gr2)}, async()=>{
  const {inspectModelFirmware}=await module();
  const report=await inspectModelFirmware(readFileSync(gr2));
  assert.equal(report.model,'GR II');assert.equal(report.workspace_url,'/gr2/');
  assert.equal(report.capabilities.native_film_library.can_build,false);
});
test('GR IV inspection proves complete decode and exposes its separate workspace', {skip:!existsSync(gr4)},async()=>{
  const {inspectModelFirmware}=await module();
  const report=await inspectModelFirmware(readFileSync(gr4));
  assert.equal(report.internal_version,'1.11.10.7');assert.equal(report.workspace_url,'/gr4/');
  assert.equal(report.proof.byte_exact_roundtrip,true);
  assert.equal(report.capabilities.native_film_library.can_build,false);
});
test('model inspector rejects unsupported bytes without starting a native writer',async()=>{
  const {inspectModelFirmware}=await module();
  await assert.rejects(inspectModelFirmware(Buffer.alloc(4096)),/unsupported|identity/);
});
test('platform inspection HTTP requires authorization and accepts exact GR II upload', {skip:!existsSync(gr2)},async()=>{
  const server=createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));
  try{
    const base=`http://127.0.0.1:${server.address().port}`,route=base+'/api/platform/inspect';
    assert.equal((await fetch(route,{method:'POST',body:readFileSync(gr2)})).status,403);
    const {session_token}=await (await fetch(base+'/api/status')).json();
    const response=await fetch(route,{method:'POST',body:readFileSync(gr2),headers:{'X-M10V-Token':session_token}});
    assert.equal(response.status,200);assert.equal((await response.json()).resources.length,121);
    assert.equal((await fetch(base+'/gr2/')).status,200);
    const catalog=await(await fetch(base+'/api/platform/adapters')).json();
    assert.equal(catalog.adapters.find(r=>r.id==='gr2').capabilities.inspect.can_read,true);
    assert.equal(catalog.adapters.find(r=>r.id==='gr2').capabilities.update_checksum.status,'verified_offline');
    assert.equal(catalog.adapters.find(r=>r.id==='gr2').capabilities.native_film_library.status,'researching');
  }finally{await new Promise(r=>server.close(r));}
});
