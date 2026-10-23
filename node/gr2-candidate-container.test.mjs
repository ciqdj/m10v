import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {packGr2Candidate,verifyGr2Candidate} from './gr2-candidate-container.mjs';
import {readUnityModelComponent,decodeUnity} from './unity-firmware.mjs';
import {unityWeightedChecksum} from './unity-checksum.mjs';
const official=readFileSync(new URL('../bin/rg2_v003.frm',import.meta.url));
function research(){const b=Buffer.from(readUnityModelComponent(official,'gr2','b01firm8'));b[0x200]^=1;b.writeUInt32BE(unityWeightedChecksum(b.subarray(512),b.readUInt32BE(32)),0x16c);return b;}
test('GR2 experimental container roundtrips exact component and preserves resources and update policy',()=>{
 const component=research(),r=packGr2Candidate(official,component);
 assert.equal(r.receipt.release_ready,false);assert.equal(r.receipt.hardware_verified,false);
 assert.equal(r.receipt.status,'experimental_offline');assert.equal(r.receipt.filename,'rg2_v003.frm');
 assert.equal(verifyGr2Candidate(official,r.candidate,component).verified,true);
 const a=decodeUnity(official),b=decodeUnity(r.candidate);
 assert.deepEqual(a.records[0].decoded,b.records[0].decoded);
 assert.deepEqual(b.records[1].nested.records[0].decoded,component);
});
test('GR2 independent verifier rejects tampering, changed policy and wrong source binding',()=>{
 const component=research(),r=packGr2Candidate(official,component);
 const damaged=Buffer.from(r.candidate);damaged[damaged.length-100]^=1;
 assert.throws(()=>verifyGr2Candidate(official,damaged,component));
 const flags=Buffer.from(component);flags.writeUInt32BE(0,0x178);assert.throws(()=>packGr2Candidate(official,flags),/policy/);
 const source=Buffer.from(official);source[100]^=1;assert.throws(()=>packGr2Candidate(source,component),/identity/);
});
test('GR2 grown component is packed without truncating payload or borrowing the resource component',()=>{
 const original=research(),component=Buffer.concat([original,Buffer.alloc(1000,0x5a)]);
 component.writeUInt32BE(component.length-512,0x164);component.writeUInt32BE(component.length,0x168);
 component.writeUInt32BE(unityWeightedChecksum(component.subarray(512),component.readUInt32BE(32)),0x16c);
 const r=packGr2Candidate(official,component);assert.ok(r.candidate.length>official.length);
 assert.equal(verifyGr2Candidate(official,r.candidate,component).verified,true);
});
