import test from 'node:test';
import assert from 'node:assert/strict';
import {buildSdFilmPack,auditSdFilmPack,sdFilmRecord,SD_RECORD_BYTES,sdCrc,sdExpectedHeader} from './gr3-sd-film-pack.mjs';
import {parseCustomCube} from './gr3-custom-lut.mjs';
test('SD pack contains every current platform recipe, independent of five active slots',()=>{
 const b=buildSdFilmPack();const a=auditSdFilmPack(b);assert.equal(a.count,55);assert.deepEqual(a.ids,[33,66,67,68,69,70,71,72,73,74,75,76,77,78,289,290,291,292,293,294,295,296,297,...Array.from({length:32},(_,i)=>34+i)]);
 assert.equal(b.length,4096+55*SD_RECORD_BYTES);
});
test('arbitrary subsets prioritize curated stocks and preserve group order, full payloads and identity',()=>{
 for(const ids of [[66,67,68],[68], [65],[50,33,42,60,34,35],[65,64,63,62,61,60,59,58,57]]){
  const ordered=[...ids.filter(id=>id===33||id>=66),...ids.filter(id=>id!==33&&id<66)];
  const b=buildSdFilmPack(ids);assert.deepEqual(auditSdFilmPack(b).ids,ordered);
  ordered.forEach((id,i)=>assert.deepEqual(b.subarray(4096+i*SD_RECORD_BYTES,4096+(i+1)*SD_RECORD_BYTES),sdFilmRecord(id)));
 }
});
test('empty duplicate unknown noninteger and excessive input rejected',()=>{
 for(const ids of [[],[33,33],[1],[79],[33.5],['33'],null,Array(300).fill(33)])assert.throws(()=>buildSdFilmPack(ids));
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
 assert.match(sdExpectedHeader(),/m10v_sd_hashes\[55\]\[32\]/);
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

test('v1 built-in pack from the preceding release remains readable',()=>{
 const oldRenderer=Buffer.from('52c0e9f5e8bc84b0430702ecd187c0a9dc816822f20ec8d5de670b9e97276d59','hex');
 const pack=buildSdFilmPack([33,66,34]);
 for(let i=0;i<3;i++){
  const record=pack.subarray(4096+i*SD_RECORD_BYTES,4096+(i+1)*SD_RECORD_BYTES);
  oldRenderer.copy(record,8448);
  record.writeUInt32LE(sdCrc(record.subarray(0,-4)),SD_RECORD_BYTES-4);
  pack.writeUInt32LE(record.readUInt32LE(SD_RECORD_BYTES-4),68+i*12);
 }
 pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);
 assert.deepEqual(auditSdFilmPack(pack).ids,[33,66,34]);
});

test('mixed pack carries a named portable LUT while preserving built-in records',()=>{
 const cube=Buffer.from('LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n');
 const custom=parseCustomCube(cube,'identity.cube','My Film');
 const pack=buildSdFilmPack([33],[custom]);
 const audit=auditSdFilmPack(pack);
 assert.equal(audit.count,2);
 assert.deepEqual(audit.ids,[33,79]);
 assert.deepEqual(pack.subarray(4096,4096+SD_RECORD_BYTES),sdFilmRecord(33));
 assert.equal(pack.subarray(4096+SD_RECORD_BYTES+16,4096+SD_RECORD_BYTES+23).toString(),'My Film');
});
test('CRC repaired custom record with changed reserved byte is rejected',()=>{
 const custom=parseCustomCube(Buffer.from('LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n'),'identity.cube','My Film');
 const pack=buildSdFilmPack([],[custom]),record=pack.subarray(4096);record[7000]^=1;
 record.writeUInt32LE(sdCrc(record.subarray(0,-4)),SD_RECORD_BYTES-4);
 pack.writeUInt32LE(record.readUInt32LE(SD_RECORD_BYTES-4),68);
 pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);
 assert.throws(()=>auditSdFilmPack(pack));
});

test('last delivered 47-film and named custom packs remain readable after opt-in defaults',async()=>{
 const {readFileSync}=await import('node:fs');
 const old=JSON.parse(readFileSync(new URL('./gr3-sd-20261021-contract.json',import.meta.url)));
 const custom=parseCustomCube(Buffer.from('LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n'),'old.cube','Old custom');
 for(const pack of [buildSdFilmPack(old.ids),buildSdFilmPack([33,289],[custom])]){
  const count=pack.readUInt32LE(16);
  for(let i=0;i<count;i++){
   const r=pack.subarray(4096+i*SD_RECORD_BYTES,4096+(i+1)*SD_RECORD_BYTES);
   Buffer.from(old.renderer,'hex').copy(r,8448);
   r.writeUInt32LE(sdCrc(r.subarray(0,-4)),SD_RECORD_BYTES-4);pack.writeUInt32LE(r.readUInt32LE(SD_RECORD_BYTES-4),68+i*12);
  }
  pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);
  assert.equal(auditSdFilmPack(pack).count,count);
  const bad=Buffer.from(pack);bad[4096+64]^=1;assert.throws(()=>auditSdFilmPack(bad));
 }
});
