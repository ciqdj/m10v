import test from 'node:test';
import assert from 'node:assert/strict';
import {buildSdFilmPack,auditSdFilmPack,sdFilmRecord,SD_RECORD_BYTES} from './gr3-sd-film-pack.mjs';
test('SD pack contains every current platform recipe, independent of five active slots',()=>{
 const b=buildSdFilmPack();const a=auditSdFilmPack(b);assert.equal(a.count,33);assert.deepEqual(a.ids,Array.from({length:33},(_,i)=>33+i));
 assert.equal(b.length,4096+33*SD_RECORD_BYTES);
});
test('arbitrary subsets preserve order, full payloads and identity',()=>{
 for(const ids of [[65],[50,33,42,60,34,35],[65,64,63,62,61,60,59,58,57]]){
  const b=buildSdFilmPack(ids);assert.deepEqual(auditSdFilmPack(b).ids,ids);
  ids.forEach((id,i)=>assert.deepEqual(b.subarray(4096+i*SD_RECORD_BYTES,4096+(i+1)*SD_RECORD_BYTES),sdFilmRecord(id)));
 }
});
test('empty duplicate unknown noninteger and excessive input rejected',()=>{
 for(const ids of [[],[33,33],[1],[66],[33.5],['33'],null,Array(300).fill(33)])assert.throws(()=>buildSdFilmPack(ids));
});
test('truncation appended bytes and any corrupt header or recipe fail closed',()=>{
 const b=buildSdFilmPack([33,65]);
 for(const c of [b.subarray(0,-1),Buffer.concat([b,Buffer.from([0])])])assert.throws(()=>auditSdFilmPack(c));
 for(const at of [0,16,24,64,4092,4096,4096+80,4096+2048,b.length-1]){const c=Buffer.from(b);c[at]^=1;assert.throws(()=>auditSdFilmPack(c));}
});
