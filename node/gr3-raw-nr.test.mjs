import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import * as nr from './gr3-raw-nr.mjs';
const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
test('RAW NR off patches all three still paths and stock changes nothing',()=>{
 assert.deepEqual(nr.planRawNr(source,{mode:'stock'}),[]);
 const edits=nr.planRawNr(source,{mode:'off'});
 assert.deepEqual(edits.map(e=>[e.offset,e.expectedHex,e.replacementHex]),[
 [0x43326c,'01602602','0060a0e3'],[0x433284,'01702702','0070a0e3'],[0x642ac4,'18408313','10408313']]);
});
test('threshold applies to both variant tables and invalid thresholds are rejected',()=>{
 const edits=nr.planRawNr(source,{mode:'threshold',iso:6400});
 assert.equal(edits.length,88);assert.ok(edits.every(e=>e.expectedHex==='01'&&e.replacementHex==='00'));
 for(const c of [{mode:'threshold',iso:6300},{mode:'off',iso:6400},{mode:'stock',extra:1},{mode:'bad'}])
 assert.throws(()=>nr.planRawNr(source,c),/降噪/);
});

test('every supported threshold changes only enable bytes below its exact index in both pinned tables',async()=>{
 const {officialResources}=await import('./gr3-stock-presets.mjs');
 const {decoded,sections}=officialResources(source),rtos=decoded.subarray(sections.RTOS.offset);
 const expectedFirsts=new Map([[400,48],[800,56],[1600,64],[3200,72],[5000,77],[6400,80],[8000,83],[10000,85],[12800,88]]);
 for(const [iso,first] of expectedFirsts){
  const edits=nr.planRawNr(source,{mode:'threshold',iso}),copy=Buffer.from(rtos);
  assert.equal(edits.length,2*(first-36));
  for(const e of edits){assert.equal(e.replacementHex,'00');assert.equal(e.expectedHex,'01');copy[e.offset]=0;}
  for(const address of [0x53ef9720,0x53ef6868])for(let i=0;i<144;i++){
   const off=address-0x53000000+i*20;
   assert.equal(copy[off],i<first?0:1);
   assert.deepEqual(copy.subarray(off+1,off+20),rtos.subarray(off+1,off+20));
  }
 }
 const x=readFileSync(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url));
 assert.throws(()=>nr.planRawNr(x,{mode:'off'}),/GR III/);
 assert.throws(()=>nr.planRawNr(x,{mode:'threshold',iso:6400}),/GR III/);
});
