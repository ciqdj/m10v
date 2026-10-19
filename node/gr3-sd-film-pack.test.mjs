import test from 'node:test';
import assert from 'node:assert/strict';
import {buildSdFilmPack,auditSdFilmPack,sdFilmRecord,SD_RECORD_BYTES,sdCrc,sdExpectedHeader} from './gr3-sd-film-pack.mjs';
test('SD pack contains every current platform recipe, independent of five active slots',()=>{
 const b=buildSdFilmPack();const a=auditSdFilmPack(b);assert.equal(a.count,39);assert.deepEqual(a.ids,[33,66,67,68,69,70,71,...Array.from({length:32},(_,i)=>34+i)]);
 assert.equal(b.length,4096+39*SD_RECORD_BYTES);
});
test('arbitrary subsets prioritize curated stocks and preserve group order, full payloads and identity',()=>{
 for(const ids of [[66,67,68],[68], [65],[50,33,42,60,34,35],[65,64,63,62,61,60,59,58,57]]){
  const ordered=[...ids.filter(id=>id===33||id>=66),...ids.filter(id=>id!==33&&id<66)];
  const b=buildSdFilmPack(ids);assert.deepEqual(auditSdFilmPack(b).ids,ordered);
  ordered.forEach((id,i)=>assert.deepEqual(b.subarray(4096+i*SD_RECORD_BYTES,4096+(i+1)*SD_RECORD_BYTES),sdFilmRecord(id)));
 }
});
test('empty duplicate unknown noninteger and excessive input rejected',()=>{
 for(const ids of [[],[33,33],[1],[72],[33.5],['33'],null,Array(300).fill(33)])assert.throws(()=>buildSdFilmPack(ids));
});
test('truncation appended bytes and any corrupt header or recipe fail closed',()=>{
 const b=buildSdFilmPack([33,65]);
 for(const c of [b.subarray(0,-1),Buffer.concat([b,Buffer.from([0])])])assert.throws(()=>auditSdFilmPack(c));
 for(const at of [0,16,24,64,4092,4096,4096+80,4096+2048,b.length-1]){const c=Buffer.from(b);c[at]^=1;assert.throws(()=>auditSdFilmPack(c));}
});

test('new builtin LUT records retain names icons and source contract identity',()=>{
 const names=['5207','Phoenix II','HARMAN RED'];
 for(let id=66;id<=68;id++){
  const r=sdFilmRecord(id);assert.equal(r.readUInt32LE(12),3);
  assert.equal(r.subarray(16,40).toString('ascii').replace(/\0+$/,''),names[id-66]);
  assert.ok(r.subarray(64,96).some(v=>v));assert.ok(r.subarray(2048,8448).some(v=>v));
 }
 assert.notDeepEqual(sdFilmRecord(67).subarray(64,96),sdFilmRecord(68).subarray(64,96));
 assert.match(sdExpectedHeader(),/m10v_sd_hashes\[39\]\[32\]/);
});
test('CRC-repaired new LUT identities and renderer contracts fail closed',()=>{
 for(const id of [66,67,68])for(const offset of [64,2048,8448]){
  const b=buildSdFilmPack([id]),record=b.subarray(4096);record[offset]^=1;
  record.writeUInt32LE(sdCrc(record.subarray(0,-4)),SD_RECORD_BYTES-4);
  b.writeUInt32LE(record.readUInt32LE(SD_RECORD_BYTES-4),68);
  b.writeUInt32LE(sdCrc(b.subarray(0,4092)),4092);
  assert.throws(()=>auditSdFilmPack(b),/配方版本不兼容/);
 }
});

test('packs carrying the preceding renderer contract are rejected even with repaired CRCs',async()=>{
 const {readFileSync}=await import('node:fs');const {createHash}=await import('node:crypto');
 const oldContract=createHash('sha256').update(readFileSync(new URL('../native/gr3/m10v_library.c',import.meta.url))).update(readFileSync(new URL('../native/gr3/halation_energy.h',import.meta.url))).digest();
 const b=buildSdFilmPack([33,65]);
 for(let i=0;i<2;i++){
  const r=b.subarray(4096+i*SD_RECORD_BYTES,4096+(i+1)*SD_RECORD_BYTES);oldContract.copy(r,8448);
  r.writeUInt32LE(sdCrc(r.subarray(0,-4)),SD_RECORD_BYTES-4);b.writeUInt32LE(r.readUInt32LE(SD_RECORD_BYTES-4),68+i*12);
 }
 b.writeUInt32LE(sdCrc(b.subarray(0,4092)),4092);assert.throws(()=>auditSdFilmPack(b),/配方版本不兼容/);
});
