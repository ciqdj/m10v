// Compose reviewed camera components with the native library, then compare every final byte.
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {inspectOfficial} from './firmware.mjs';
import {decodeFrameMap,sum32} from './gr3-frames.mjs';
import {auditGr3Candidate} from './gr3-candidate-audit.mjs';
import {auditNativeLibrary} from './gr3-m10v-native-build.mjs';
import {createStorePlan} from './gr3-store-plan.mjs';
import {runGr3Runtime} from './gr3-runtime.mjs';
import {planRawNr,rawNrEvidence} from './gr3-raw-nr.mjs';
import {normalizeExtensions,activeExtensions} from '../web/gr3/native-library-state.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const sha=b=>createHash('sha256').update(b).digest('hex');
const LOAD=0x53000000, COMPONENT_BASE=0x540b6000, COMPONENT_END=0x540ba000;
const pins={
 aspect:'c89c128aada72194d7282355a5f2f06409515ce8cea3a0da97e047bc9e046b82',
 level:'52a7c4d254cb6f117b2c891373c99ad6357a5df94519e038481c68f4661307ed',
 'aspect-level':'e8d9416c7c594e6af9934e91c63ae2880ca445c865a0b5123e66c034d5b24cec',
};
const resourceAdaptations=[
 [0x540b9448,0xe300032a,0xe30003a2],
 [0x540b8a18,0xe300c32a,0xe300c3a2],
 [0x540b8be4,0xe300c32a,0xe300c3a2],
 [0x540b8a4c,0xe3003311,0xe30033a1],
 [0x540b8a6c,0xe3003311,0xe30033a1],
 [0x540b8c14,0xe3003311,0xe30033a1],
];
export function integrationFingerprint(){
 return sha(JSON.stringify(['gr3-integrated-components.mjs','gr3-raw-nr.mjs','gr3-stock-presets.mjs','gr3-native-library.mjs','gr3-m10v-native-build.mjs','gr3-runtime.mjs','gr3-runtime-worker.py','gr3-store-plan.mjs','../web/gr3/native-library-state.mjs'].map(n=>[n,sha(readFileSync(new URL(n,import.meta.url)))])));
}
function parts(source,candidate){
 const report=inspectOfficial(source),decoded=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8)).decoded;
 let at=0;const sections={};
 for(const section of report.sections){
  need(decoded.toString('ascii',at,at+8).split('\0')[0]===section.name,'composition section order differs');
  const size=section.name==='RTOS'?decoded.readUInt32LE(at+12):section.size-16;
  need(at+16+size<=decoded.length-4,'composition section bounds differ');
  sections[section.name]={offset:at+16,size};at+=size+16;
 }
 need(at+4===decoded.length,'composition trailer differs');
 const r=sections.RTOS;return {decoded,sections,rtos:decoded.subarray(r.offset,r.offset+r.size)};
}
const variant=e=>[e.aspect?'aspect':null,e.level?'level':null].filter(Boolean).join('-');
export async function buildCameraComponents(source,requested,{signal}={}){
 const e=normalizeExtensions(requested),key=variant(e);if(!key)return null;
 need(inspectOfficial(source).model==='GR III','组合扩展当前仅支持 GR III');
 const {candidate}=await runGr3Runtime(source,createStorePlan({variant:'street',features:key.split('-')}),'build',undefined,{signal});
 validateComponent(source,candidate,e);return candidate;
}
function validateComponent(source,component,e){
 const key=variant(e);if(!key){need(component===null,'unexpected camera component');return null;}
 need(Buffer.isBuffer(component),'camera component missing');
 const structural=auditGr3Candidate(source,component);
 need(structural.changedSections.join('|')==='RTOS','camera component changed unrelated section');
 const p=parts(source,component);
 need(p.rtos.length===COMPONENT_END-LOAD&&sha(p.rtos)===pins[key],'camera component source pin differs');
 return p;
}
function expectedImage(source,nativeCandidate,runtime,manifest,component,requested){
 const e=normalizeExtensions(requested),nativeReceipt=auditNativeLibrary(source,nativeCandidate,runtime,manifest);
 need(inspectOfficial(source).model==='GR III'||!activeExtensions(e).length,'组合扩展当前仅支持 GR III');
 const original=parts(source,source),native=parts(source,nativeCandidate),c=validateComponent(source,component,e);
 need(manifest.base===(c?COMPONENT_END:COMPONENT_BASE),'composition native placement differs');
 const target=Buffer.from(native.decoded),rtos=target.subarray(native.sections.RTOS.offset,native.sections.RTOS.offset+native.sections.RTOS.size);
 let stockWords=0;
 if(c){
  for(let off=0;off<original.rtos.length;off+=4){
   const stock=original.rtos.subarray(off,off+4),addition=c.rtos.subarray(off,off+4);
   if(addition.equals(stock))continue;
   const current=rtos.subarray(off,off+4),address=LOAD+off;
   const router=e.aspect&&[0x533966d4,0x533970ec].includes(address);
   need(current.equals(stock)||(router&&current.readUInt32LE()===0xe30033a1),'camera components overlap native patch at '+address.toString(16));
   addition.copy(rtos,off);stockWords++;
  }
  need(rtos.subarray(original.rtos.length,COMPONENT_END-LOAD).every(v=>v===0),'camera component allocation overlaps native module');
  c.rtos.subarray(original.rtos.length).copy(rtos,original.rtos.length);
  if(e.aspect){
   need(rtos.readUInt32LE(0x540b97e8-LOAD)===2,'component must disable its timestamp renderer');
   for(const [address,before,after] of resourceAdaptations){const off=address-LOAD;need(rtos.readUInt32LE(off)===before,'aspect resource preimage differs');rtos.writeUInt32LE(after,off);}
  }
 }
 if(e.negativeGrain){
  need(rtos.readUInt32LE(0xb348c0)===9&&rtos.readUInt16LE(0xb3501e)===0,'negative grain preimage differs');
  rtos.writeUInt32LE(10,0xb348c0);rtos.writeUInt16LE(0x0f02,0xb3501e);
 }
 const rawEdits=planRawNr(source,e.rawNr);
 for(const edit of rawEdits){
  const expected=Buffer.from(edit.expectedHex,'hex'),replacement=Buffer.from(edit.replacementHex,'hex');
  need(rtos.subarray(edit.offset,edit.offset+expected.length).equals(expected),'RAW NR patch overlaps another component');
  replacement.copy(rtos,edit.offset);
 }
 target.writeUInt32LE(0,target.length-4);target.writeUInt32LE(-sum32(target)>>>0,target.length-4);
 return {target,nativeReceipt,composition:{schema:'m10v-gr3-integrated-components/v1',verified:true,extensions:e,
  component_variant:variant(e)||null,component_rtos_sha256:c?sha(c.rtos):null,
  component_range:c?[COMPONENT_BASE,COMPONENT_END]:null,native_range:[manifest.base,manifest.base+runtime.length],
  native_resource_range:[786,929],aspect_resource_id:e.aspect?930:null,
  shared_resource_routes:e.aspect?2:0,adapted_resource_words:e.aspect?6:0,component_stock_words:stockWords,
  negative_grain_sites:e.negativeGrain?[0x53b348c0,0x53b3501e]:[],
  raw_nr:{configuration:e.rawNr,...rawNrEvidence(source,e.rawNr),patch_count:rawEdits.length,
   patched_bytes:rawEdits.reduce((n,p)=>n+p.replacementHex.length/2,0),
   patches_sha256:sha(JSON.stringify(rawEdits)),
   code_sites:e.rawNr.mode==='off'?rawEdits.map(({offset,expectedHex,replacementHex})=>({address:LOAD+offset,expected_hex:expectedHex,replacement_hex:replacementHex})):[],
   table_cleared_index_range:e.rawNr.mode==='threshold'?[36,Math.round(8*(Math.log2(e.rawNr.iso/3.125)-1))]:null},
  camera_tested:false}};
}
// Reuse compressed frames only when their entire backward-reference history is unchanged.
function encode(base,target){
 const {decoded,frames}=decodeFrameMap(base,base.readUInt32LE(base.length-8));
 need(decoded.length===target.length,'composition must retain allocated extent');const chunks=[];
 for(const f of frames){const from=f.decoded_start,to=f.decoded_end,history=Math.min(2047,from),bytes=target.subarray(from,to);
  if(target.subarray(from-history,to).equals(decoded.subarray(from-history,to)))chunks.push(base.subarray(128+f.encoded_start,128+f.encoded_end));
  else for(let at=0;at<bytes.length;at+=0x6000){const part=bytes.subarray(at,at+0x6000),prefix=Buffer.alloc(2);prefix.writeUInt16BE(0x8000|part.length);chunks.push(prefix,part);}
 }
 chunks.push(Buffer.alloc(2));const payload=Buffer.concat(chunks),footer=Buffer.from(base.subarray(-24));
 footer.writeUInt32LE(payload.length,12);footer.writeUInt32LE(target.length,16);footer.writeUInt32LE(0,20);
 const candidate=Buffer.concat([base.subarray(0,128),payload,Buffer.alloc(-(128+payload.length)&3),footer]);
 candidate.writeUInt32LE(-sum32(candidate)>>>0,candidate.length-4);return candidate;
}
export function auditIntegratedNative(source,candidate,nativeCandidate,runtime,manifest,component,extensions){
 auditGr3Candidate(source,candidate,{maxRtosGrowth:544*1024});
 const {target,composition}=expectedImage(source,nativeCandidate,runtime,manifest,component,extensions);
 need(parts(source,candidate).decoded.equals(target),'integrated final bytes differ from verified components');
 return composition;
}
export function composeNative(source,nativeCandidate,runtime,manifest,component,extensions){
 const {target}=expectedImage(source,nativeCandidate,runtime,manifest,component,extensions),candidate=encode(nativeCandidate,target);
 const composition=auditIntegratedNative(source,candidate,nativeCandidate,runtime,manifest,component,extensions);
 const structure=auditGr3Candidate(source,candidate,{maxRtosGrowth:544*1024});
 return {candidate,composition,structure};
}
