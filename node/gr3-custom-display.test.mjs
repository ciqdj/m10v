import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {buildNativeLibrary} from './gr3-m10v-native-build.mjs';
test('custom display resources preserve stock cards and independently reject LUT icon tampering',async()=>{
 const dir=await mkdtemp(path.join(tmpdir(),'m10v-custom-display-'));
 try{
  const manifest=JSON.parse(execFileSync(new URL('../.venv/bin/python',import.meta.url).pathname,['scripts/build_gr3_m10v_library.py','--sd-library','--out',dir],{cwd:new URL('..',import.meta.url).pathname}));
  const runtime=await readFile(path.join(dir,'m10v-library-arm.bin'));
  const source=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
  assert.deepEqual(manifest.custom_film_display.name_resources,[1007,1011]);
  assert.deepEqual(manifest.resources.texts.slice(988-786,991-786),['胶卷名称：关闭','胶卷名称：开启','胶卷名称水印']);
  assert.equal(buildNativeLibrary(source,runtime,manifest).receipt.camera_tested,false);
  for(const offset of [manifest.icons.pixels+78*6400-manifest.base,manifest.icons.descriptors+83*8+4-manifest.base]){
   const changed=Buffer.from(runtime);changed[offset]^=1;
   assert.throws(()=>buildNativeLibrary(source,changed,{...manifest,code_sha256:createHash('sha256').update(changed).digest('hex')}),/custom LUT icon differs/);
  }
 }finally{await rm(dir,{recursive:true,force:true});}
});
