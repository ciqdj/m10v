import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as stock from './gr3-stock-presets.mjs';
const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
test('negative grain menu has exact independent changes and no unrelated bytes',()=>{
  const edits=stock.createStockEdits(source,{negativeGrainMenu:true,presets:[]});
  assert.deepEqual(edits.map(e=>[e.section,e.offset,e.expectedHex,e.replacementHex]),[
    ['RTOS',0xb348c0,'09000000','0a000000'],['RTOS',0xb3501e,'0000','020f']]);
  assert.deepEqual(stock.createStockEdits(source,{negativeGrainMenu:false,presets:[]}),[]);
});
test('stock preset names respect actual storage and Standard shared name',()=>{
  const caps=stock.stockPresetCapabilities(source);
  assert.equal(caps.length,12);assert.equal(caps[0].canRename,false);
  assert.equal(caps.find(p=>p.slot===2).nameMax,12);
  assert.throws(()=>stock.createStockEdits(source,{presets:[{slot:1,name:'Other'}]}),/名称/);
  assert.throws(()=>stock.createStockEdits(source,{presets:[{slot:2,name:'Too long preset'}]}),/长度/);
  const edits=stock.createStockEdits(source,{presets:[{slot:2,name:'Summer'}]});
  assert.ok(edits.length>=3); assert.ok(edits.every(e=>e.section==='RTOS'));
  assert.ok(edits.some(e=>e.replacementHex.includes(Buffer.from('Summer\0','utf16le').toString('hex'))));
});
test('bad icon alpha, extra fields and duplicate presets are refused',()=>{
  assert.throws(()=>stock.createStockEdits(source,{presets:[{slot:2,iconPixelsBase64:Buffer.alloc(6400).toString('base64')}]}),/透明/);
  assert.throws(()=>stock.createStockEdits(source,{presets:[{slot:2,name:'A',unknown:1}]}),/字段/);
  assert.throws(()=>stock.createStockEdits(source,{presets:[{slot:2,name:'A'},{slot:2,name:'B'}]}),/重复/);
});
