import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync,readFileSync } from 'node:fs';
import { prepare800T,build800T } from './gr3-800t-build.mjs';
const sample=new URL('../fwdc239b.bin',import.meta.url);
test('800T preflight binds exact source, code and selection; stale or forged plans fail',{skip:!existsSync(sample)},async()=>{
 const official=readFileSync(sample);const weak=prepare800T(official,{strength:'weak'});const strong=prepare800T(official,{strength:'strong',timestamp:true});
 assert.equal(weak.ready,true);assert.equal(weak.camera_tested,false);assert.equal(weak.blockers.length,0);
 assert.notEqual(weak.configuration_sha256,strong.configuration_sha256);
 assert.equal(strong.configuration.timestamp,true);assert.equal(strong.color_plan.custom[0].name,'800T');
 await assert.rejects(()=>build800T(official,{strength:'weak'},strong.configuration_sha256), /方案已变化/);
 assert.throws(()=>prepare800T(official,{strength:'weak',evidence:{firmwareReady:true}}), /800T/);
});
test('800T weak without timestamp produces an independently audited container',{skip:!existsSync(sample)},async()=>{
 const official=readFileSync(sample),selection={strength:'weak',timestamp:false};
 const prepared=prepare800T(official,selection);
 const result=await build800T(official,selection,prepared.configuration_sha256);
 assert.ok(Buffer.isBuffer(result.candidate));assert.notDeepEqual(result.candidate,official);
 assert.equal(result.audit.exactExpectedPayloads,true);
 assert.equal(result.audit.acceptedPlanBound,true);
 assert.equal(result.receipt.camera_tested,false);
 assert.equal(result.receipt.configuration.timestamp,false);
 assert.equal(result.receipt.chroma_order,'CbCr');
});
