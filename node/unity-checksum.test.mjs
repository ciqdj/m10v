import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {readUnityModelComponent,inspectUnityModel} from './unity-firmware.mjs';
const moduleURL=new URL('./unity-checksum.mjs',import.meta.url);
async function implementation(){assert.ok(existsSync(moduleURL),'UNITY weighted checksum is missing');return import(moduleURL);}
test('UNITY weighted checksum follows byte positions and unsigned position wrapping',async()=>{
  const {unityWeightedChecksum}=await implementation();
  assert.equal(unityWeightedChecksum(Buffer.from([0,1,2,3,4,5,6,7])),118);
  assert.equal(unityWeightedChecksum(Buffer.from([1,2,3,4,5]),0xfffffffe),52);
  assert.equal(unityWeightedChecksum(Buffer.alloc(0)),0);
  assert.throws(()=>unityWeightedChecksum(Buffer.alloc(1),-1),/position/);
});
test('UNITY component verifier matches factory fields and detects payload corruption',async()=>{
  const {verifyUnityComponentChecksum}=await implementation();
  for(const [model,file,checksums] of [['gr2','rg2_v003.frm',[0xa3a80234,0x826a5e33]],['gr1','rg1_v051.frm',[0x7c565038,0x7b62e1a9]]]){
    const url=new URL('../bin/'+file,import.meta.url);if(!existsSync(url))continue;
    const source=readFileSync(url);
    for(const [i,name] of ['b01firm6','b01firm8'].entries()){
      const decoded=readUnityModelComponent(source,model,name),report=verifyUnityComponentChecksum(decoded);
      assert.equal(report.checksum,checksums[i]);assert.equal(report.payload_bytes,decoded.length-512);
      assert.equal(report.verify_flags.every(v=>v===1),true);
      const changed=Buffer.from(decoded);changed[512]^=1;
      assert.throws(()=>verifyUnityComponentChecksum(changed),/checksum/);
      assert.throws(()=>verifyUnityComponentChecksum(decoded.subarray(0,-1)),/length/);
    }
    assert.equal(inspectUnityModel(source,model).proof.modified_update_checksum,true);
  }
});
