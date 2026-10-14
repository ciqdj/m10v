import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import * as custom from './gr3-customization.mjs';
const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
const selection={variant:'street',features:['negativeGrain','presets','rawNr'],negativeGrainMenu:true,
 stockPresets:[{slot:2,name:'Summer'}],rawNr:{mode:'threshold',iso:6400}};
test('native-only customization produces a source-bound zero-growth audited firmware',async()=>{
 const prepared=await custom.prepareCustomization(source,selection);assert.equal(prepared.ready,true);
 const result=await custom.buildCustomization(source,selection,prepared.configuration_sha256);
 assert.equal(result.receipt.audit.rtosGrowth,0);assert.equal(result.receipt.camera_tested,false);
 assert.equal(result.receipt.configuration_sha256,prepared.configuration_sha256);
 await assert.rejects(()=>custom.buildCustomization(source,{...selection,negativeGrainMenu:false},prepared.configuration_sha256),/变化/);
});
test('unknown fields, ignored options and recipe/film stock collisions are refused',()=>{
 assert.throws(()=>custom.normalizeCustomization({...selection,hidden:1}),/字段/);
 assert.throws(()=>custom.normalizeCustomization({...selection,features:['negativeGrain']}),/启用/);
 assert.throws(()=>custom.normalizeCustomization({variant:'street',features:['film','presets'],stockPresets:[{slot:2,name:'Oops'}]}),/占用/);
});
test('retired SD film bay cannot enter a firmware build',()=>{
 assert.throws(()=>custom.normalizeCustomization({variant:'street',features:['filmbay','level']}),/废弃|不可用/);
});
test('diffusion cannot export before independent GR III descriptor isolation evidence',async()=>{
 const configured={variant:'street',features:['film'],filmTexture:{gold200:{grain:0,hdf:1}}};
 const result=await custom.prepareCustomization(source,configured);
 assert.equal(result.ready,false);assert.ok(result.blockers.includes('gr3_diffusion_descriptor_isolation_not_verified'));
 await assert.rejects(()=>custom.buildCustomization(source,configured,result.configuration_sha256),/柔光|预检/);
});
