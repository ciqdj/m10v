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
