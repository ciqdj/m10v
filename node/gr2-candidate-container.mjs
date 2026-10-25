// Experimental GR II container assembly and independent byte readback.
// Native correctness is the caller's responsibility; this grants no release gate.
import {createHash} from 'node:crypto';
import {decodeUnity,xorUnityPayload,readUnityModelComponent} from './unity-firmware.mjs';
import {verifyUnityComponentChecksum} from './unity-checksum.mjs';
const need=(ok,message)=>{if(!ok)throw Error(message);};
const sha=b=>createHash('sha256').update(b).digest('hex');
const aligned=n=>Math.ceil(n/512)*512;
function inputs(official,component){
 const original=readUnityModelComponent(official,'gr2','b01firm8');
 need(Buffer.isBuffer(component)&&component.length%4===0&&component.length<=0x81fc00,'GR2 executable bounds differ');
 need(component.subarray(0,32).equals(original.subarray(0,32))&&component.subarray(0x160,0x164).equals(original.subarray(0x160,0x164)),'GR2 executable identity or entry differs');
 need(component.subarray(0x170,0x180).equals(original.subarray(0x170,0x180)),'GR2 verification policy differs');
 need(component.subarray(32+15*20,32+16*20).equals(original.subarray(32+15*20,32+16*20)),'GR2 deferred record differs');
 verifyUnityComponentChecksum(component);
 return decodeUnity(official);
}
function replaceLast(template,index,payload){
 const parsed=decodeUnity(template),row=parsed.records[index];need(index===parsed.records.length-1,'only the last GR2 record may grow');
 const tail=template.subarray(row.offset+row.size),out=Buffer.alloc(aligned(row.offset+payload.length+tail.length));
 template.copy(out,0,0,row.offset);payload.copy(out,row.offset);tail.copy(out,row.offset+payload.length);
 out.writeUInt32BE(out.length,32);out.writeUInt32BE(payload.length,64+64*index+4);return out;
}
function checkContainer(original,candidate,index,expectedPayload){
 const a=decodeUnity(original),b=decodeUnity(candidate);
 need(a.records.length===b.records.length&&index===a.records.length-1,'GR2 record count differs');
 for(let i=0;i<a.records.length;i++){
  const x=a.records[i],y=b.records[i];
  need(x.name===y.name&&x.offset===y.offset&&x.type===y.type&&x.encoding===y.encoding,'GR2 record identity/layout differs');
  if(i!==index)need(x.size===y.size&&original.subarray(x.offset,x.offset+x.size).equals(candidate.subarray(y.offset,y.offset+y.size)),'GR2 untouched component changed');
 }
 const x=a.records[index],y=b.records[index];need(y.size===expectedPayload.length&&candidate.subarray(y.offset,y.offset+y.size).equals(expectedPayload),'GR2 executable payload differs');
 const header=Buffer.from(candidate.subarray(0,x.offset)),expected=original.subarray(0,x.offset);
 header.writeUInt32BE(expected.readUInt32BE(32),32);header.writeUInt32BE(expected.readUInt32BE(64+64*index+4),64+64*index+4);
 need(header.equals(expected),'GR2 unexpected header/prefix edit');
 const tail=original.subarray(x.offset+x.size),actual=candidate.subarray(y.offset+y.size);
 need(actual.length>=tail.length&&actual.subarray(0,tail.length).equals(tail)&&actual.subarray(tail.length).every(v=>v===0),'GR2 trailing bytes changed');
 need(candidate.length===aligned(y.offset+y.size+tail.length),'GR2 noncanonical container length');return b;
}
export function verifyGr2Candidate(official,candidate,expectedComponent){
 const source=inputs(official,expectedComponent);need(Buffer.isBuffer(candidate),'GR2 candidate bytes required');
 const decoded=decodeUnity(candidate),nested=decoded.records[1];
 need(source.records.length===2&&nested?.name==='rg2_v001up'&&nested.nested,'GR2 nested container differs');
 checkContainer(source.records[1].decoded,nested.decoded,0,xorUnityPayload(expectedComponent));
 checkContainer(official,candidate,1,nested.decoded);
 need(nested.nested.records[0].decoded.equals(expectedComponent),'GR2 decoded executable readback differs');
 return {verified:true,source_sha256:sha(official),candidate_sha256:sha(candidate),component_sha256:sha(expectedComponent),
   resource_unchanged:true,verification_policy_unchanged:true,deferred_record_unchanged:true,hardware_verified:false,release_ready:false};
}
export function packGr2Candidate(official,component){
 const source=inputs(official,component);
 const nested=replaceLast(source.records[1].decoded,0,xorUnityPayload(component));
 const candidate=replaceLast(official,1,nested),audit=verifyGr2Candidate(official,candidate,component);
 return {candidate,receipt:{schema:'m10v-gr2-experimental-candidate/v1',status:'experimental_offline',filename:'rg2_v003.frm',...audit}};
}
