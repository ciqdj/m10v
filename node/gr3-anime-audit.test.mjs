import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {buildNativeLibrary} from './gr3-m10v-native-build.mjs';

test('all six film icons and five FN enum resources have independent immutable readback',()=>{
 const folder=mkdtempSync(path.join(tmpdir(),'m10v-anime-audit-'));
 try{
  const m=JSON.parse(execFileSync(new URL('../.venv/bin/python',import.meta.url).pathname,['scripts/build_gr3_m10v_library.py','--sd-library','--out',folder],{cwd:new URL('..',import.meta.url).pathname}));
  const r=readFileSync(path.join(folder,'m10v-library-arm.bin')),source=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
  assert.equal(buildNativeLibrary(source,r,m).receipt.camera_tested,false);
  for(let id=858;id<=868;id++){
   const descriptor=r.readUInt32LE(m.icons.table-m.base+id*4)-m.base;
   const pixel=r.readUInt32LE(descriptor+4)*4-m.base;
   for(const at of [descriptor,descriptor+4,pixel]){
    const changed=Buffer.from(r);changed[at]^=1;
    assert.throws(()=>buildNativeLibrary(source,changed,{...m,code_sha256:createHash('sha256').update(changed).digest('hex')}),/anime artwork|anime icon/);
   }
  }
  for(const film of m.film_d76){
   assert.equal(film.storage,'mono-u8');assert.equal(film.stored_bytes,3375);
   const changed=Buffer.from(r);changed[film.offset]^=1;
   assert.throws(()=>buildNativeLibrary(source,changed,{...m,code_sha256:createHash('sha256').update(changed).digest('hex')}),/D76 lossless mono readback/);
  }
 }finally{rmSync(folder,{recursive:true,force:true});}
});
