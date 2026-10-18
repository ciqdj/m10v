import test from 'node:test';import assert from 'node:assert/strict';import{readFileSync}from'node:fs';
import{buildGr3Bridge,prepareGr3Bridge,exportGr3Bridge}from'./gr3-bridge.mjs';
const official=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
test('bridge exceeds the 2.10.32.27 DSP measured in both user photos without changing major minor or tail',()=>{
 const {candidate,receipt}=buildGr3Bridge(official);const observed=0x020a201b;
 assert.ok(candidate.readUInt32BE(0x38)>observed);assert.equal(candidate.readUInt32BE(0x38),0x020a211b);assert.equal(candidate.readUInt32BE(0x50),0x020a211b);
 assert.equal(receipt.camera_verified,false);assert.equal(receipt.hardware_verification.status,'pending');
 const plan=prepareGr3Bridge(official);assert.equal(plan.download_available,true);
 assert.throws(()=>exportGr3Bridge(official,{accepted_plan_id:'old-plan',acknowledge_instructions:true}),/预检/);
});
