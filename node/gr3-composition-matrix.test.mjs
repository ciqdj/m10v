// Optional local component matrix; each candidate goes through complete byte/readback audit.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdtemp,rm} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import {readNativeOfficial} from './gr3-native-library.mjs';
import {buildNativeLibrary} from './gr3-m10v-native-build.mjs';
import {composeNative,auditIntegratedNative} from './gr3-integrated-components.mjs';
import {decodeFrameMap} from './gr3-frames.mjs';
const root=new URL('..',import.meta.url).pathname;
const study=path.join(root,'builds/gr3-composition-study');
const available=['aspect','level','aspect-level'].every(n=>existsSync(path.join(study,n+'.bin')));
const raw=b=>{const d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;return d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c));};
test('all eight extension combinations preserve selected/unselected bytes in debug and release', {skip:!available,timeout:180000},async()=>{
 const source=await readNativeOfficial(),stock=raw(source),folder=await mkdtemp(path.join(os.tmpdir(),'m10v-composition-matrix-'));
 const components=Object.fromEntries(await Promise.all(['aspect','level','aspect-level'].map(async k=>[k,await readFile(path.join(study,k+'.bin'))])));
 try{
  for(const debug of [false,true]){
   const natives=new Map();
   for(const base of [0x540b6000,0x540ba000]){
    const out=path.join(folder,`${debug}-${base}`);
    execFileSync(path.join(root,'.venv/bin/python'),['scripts/build_gr3_m10v_library.py','--base','0x'+base.toString(16),'--out',out,...(debug?['--debug','--debug-build-id','0x1234abcd']:[])],{cwd:root,stdio:'pipe'});
    const runtime=await readFile(path.join(out,'m10v-library-arm.bin')),manifest=JSON.parse(await readFile(path.join(out,'m10v-library-arm.json')));
    natives.set(base,{runtime,manifest,...buildNativeLibrary(source,runtime,manifest)});
   }
   for(let bits=0;bits<8;bits++){
    const extensions={aspect:!!(bits&1),level:!!(bits&2),negativeGrain:!!(bits&4)};
    const variant=[extensions.aspect?'aspect':null,extensions.level?'level':null].filter(Boolean).join('-');
    const component=components[variant]??null,n=natives.get(component?0x540ba000:0x540b6000);
    const result=composeNative(source,n.candidate,n.runtime,n.manifest,component,extensions),rtos=raw(result.candidate);
    assert.deepEqual(result.composition.extensions,{...extensions,rawNr:{mode:'stock'}});
    assert.equal(result.composition.component_variant,variant||null);
    assert.equal(result.composition.aspect_resource_id,extensions.aspect?930:null);
    assert.equal(result.composition.shared_resource_routes,extensions.aspect?2:0);
    assert.equal(result.composition.negative_grain_sites.length,extensions.negativeGrain?2:0);
    assert.equal(n.manifest.debug_mode,debug);
    assert.deepEqual(rtos.subarray(n.manifest.base-0x53000000),n.runtime);
    // Real hook and data sites, independent of receipt flags.
    assert.equal(rtos.readUInt32LE(0xb2fb60),extensions.level?0x540b99c8:stock.readUInt32LE(0xb2fb60));
    assert.equal(rtos.readUInt32LE(0xb348c0),extensions.negativeGrain?10:9);
    assert.equal(rtos.readUInt16LE(0xb3501e),extensions.negativeGrain?0x0f02:0);
    if(extensions.aspect){
     assert.equal(rtos.readUInt32LE(0x10b9448),0xe30003a2);
     assert.equal(rtos.readUInt32LE(0x10b97e8),2);
     assert.notEqual(rtos.readUInt32LE(0x292544),stock.readUInt32LE(0x292544));
    }else assert.equal(rtos.readUInt32LE(0x292544),stock.readUInt32LE(0x292544));
    assert.equal(auditIntegratedNative(source,result.candidate,n.candidate,n.runtime,n.manifest,component,extensions).verified,true);
    if(bits===7){
     const wrong={...extensions,negativeGrain:false};
     assert.throws(()=>auditIntegratedNative(source,result.candidate,n.candidate,n.runtime,n.manifest,component,wrong),/final bytes differ/);
    }
   }
  }
 }finally{await rm(folder,{recursive:true,force:true});}
});
