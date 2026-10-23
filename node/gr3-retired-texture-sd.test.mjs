import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {buildSdFilmPack,auditSdFilmPack,sdCrc} from './gr3-sd-film-pack.mjs';
const prior=JSON.parse(readFileSync(new URL('./gr3-sd-texture-prior-contract.json',import.meta.url)));
const sha=b=>createHash('sha256').update(b).digest('hex');
function oldPack(custom=[]){
 const pack=buildSdFilmPack([...prior.ids],custom),count=pack.readUInt32LE(16);
 for(let i=0;i<count;i++){
  const r=pack.subarray(4096+i*12288,4096+(i+1)*12288),id=r.readUInt32LE(8);
  Buffer.from(prior.renderer,'hex').copy(r,8448);
  r.writeUInt32LE(sdCrc(r.subarray(0,-4)),r.length-4);
  if(prior.ids.includes(id))assert.equal(sha(r),prior.hashes[prior.ids.indexOf(id)]);
  pack.writeUInt32LE(r.readUInt32LE(r.length-4),68+i*12);
 }
 pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);return pack;
}
test('deleting texture processing retains all48 last-published film records',()=>{
 assert.deepEqual(auditSdFilmPack(oldPack()).ids,auditSdFilmPack(buildSdFilmPack()).ids);
});
test('prior renderer custom LUTs remain accepted while repaired-CRC tampering is rejected',()=>{
 const rgb=Buffer.alloc(6591),film={name:'Old LUT',rgb,sha256:sha(rgb)};
 const pack=oldPack([film]);assert.equal(auditSdFilmPack(pack).count,49);
 const r=pack.subarray(pack.length-12288);r[7000]=1;r.writeUInt32LE(sdCrc(r.subarray(0,-4)),12284);
 pack.writeUInt32LE(r.readUInt32LE(12284),68+48*12);pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);
 assert.throws(()=>auditSdFilmPack(pack));
});
