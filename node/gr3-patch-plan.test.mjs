import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {generateNative,prepareNative} from './gr3-native-library.mjs';import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
import * as patch from './gr3-patch-plan.mjs';import {createStockEdits} from './gr3-stock-presets.mjs';
import {decodeFrameMap} from './gr3-frames.mjs';
const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
test('zero-growth stock overlays are fully read back against independent intent',()=>{
 const edits=createStockEdits(source,{negativeGrainMenu:true,presets:[{slot:2,name:'Summer'}]});
 const result=patch.applyPatchPlan(source,source,edits);assert.equal(result.audit.rtosGrowth,0);
 const {decoded}=decodeFrameMap(result.candidate);assert.equal(decoded.readUInt32LE(0x10870+0xb348c0),10);
 assert.equal(result.audit.changedSections.join(','),'RTOS');
});
test('conflicting preimage, protected sections and overlapping edits are refused',()=>{
 const e={section:'RTOS',offset:0xb348c0,expectedHex:'09000000',replacementHex:'0a000000',owner:'test'};
 assert.throws(()=>patch.applyPatchPlan(source,source,[{...e,expectedHex:'00000000'}]),/前像/);
 assert.throws(()=>patch.applyPatchPlan(source,source,[{...e,section:'CPU'}]),/分区/);
 assert.throws(()=>patch.applyPatchPlan(source,source,[e,e]),/重叠/);
});
test('stock overlay composes onto a freshly audited native candidate without shifting sections',async()=>{
 const config=defaultConfiguration(),plan=prepareNative(source,config);
 const {candidate:base,receipt}=await generateNative(source,config,plan.configuration_sha256);
 const result=patch.applyPatchPlan(source,base,createStockEdits(source,{negativeGrainMenu:true}));
 assert.equal(result.audit.rtosGrowth,receipt.rtos_growth);assert.equal(result.audit.baseCandidateSha256.length,64);
});
test('updater code and version bytes stay protected even inside RTOS',()=>{
 assert.throws(()=>patch.applyPatchPlan(source,source,[{section:'RTOS',offset:0x628578,expectedHex:'1700003a',replacementHex:'0000a0e1',owner:'wrong'}]),/保护/);
});
