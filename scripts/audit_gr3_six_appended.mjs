// Read-only audit of an exact GR III 2.10 six-film research candidate.
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {inspectOfficial} from '../node/firmware.mjs';
import {auditGr3Candidate} from '../node/gr3-candidate-audit.mjs';
import {decodeFrameMap} from '../node/gr3-frames.mjs';

const [sourcePath,candidatePath]=process.argv.slice(2);
if(!sourcePath||!candidatePath)throw new Error('usage: node scripts/audit_gr3_six_appended.mjs official.bin candidate.bin');
const source=await readFile(sourcePath),candidate=await readFile(candidatePath);
const official=inspectOfficial(source),report=auditGr3Candidate(source,candidate);
const old=decodeFrameMap(source,source.readUInt32LE(source.length-8)).decoded;
const fresh=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8)).decoded;
const need=(ok,message)=>{if(!ok)throw new Error(message);};
need(report.rtosGrowth>0&&report.rtosGrowth<=65536&&
  report.changedSections.length===2&&report.changedSections.includes('RTOS')&&report.changedSections.includes('ICONBIN'),
  'candidate sections differ from the allowed six-film research scope');
let oldAt=0,newAt=0,rtosAt=0,oldRtosAt=0;
for(const row of official.sections){
  const oldName=old.toString('ascii',oldAt,oldAt+8).split('\0')[0];
  const newName=fresh.toString('ascii',newAt,newAt+8).split('\0')[0];
  need(oldName===row.name&&newName===row.name,'section order changed');
  const size=row.size+(row.name==='RTOS'?report.rtosGrowth:0);
  if(!['RTOS','ICONBIN'].includes(row.name))need(
    fresh.subarray(newAt,newAt+size).equals(old.subarray(oldAt,oldAt+row.size)),
    `unexpected ${row.name} change`);
  if(row.name==='RTOS'){rtosAt=newAt+16;oldRtosAt=oldAt+16;}
  oldAt+=row.size;newAt+=size;
}
need(newAt+4===fresh.length,'candidate section boundaries differ');
for(const [start,end] of [[0x620000,0x640000],[0x820000,0x840000],[0x2038,0x203c]])need(
  fresh.subarray(rtosAt+start,rtosAt+end).equals(old.subarray(oldRtosAt+start,oldRtosAt+end)),
  'protected updater/version area changed');
const word=address=>fresh.readUInt32LE(rtosAt+address-0x53000000);
const decodeMov=value=>((value>>>4)&0xf000)|(value&0xfff);
const pointer=(low,high)=>decodeMov(word(low))+(decodeMov(word(high))*65536);
const count=6;
const rtosEnd=0x53000000+official.sections.find(row=>row.name==='RTOS').size-16+report.rtosGrowth;
const inRtos=(address,length)=>address>=0x53000000&&address+length<=rtosEnd;
need(word(0x532c2acc)===((0x93a00000|(12+count))>>>0),'still menu count is not 18');
need(word(0x53283c08)===((0xe3a00000|(12+count))>>>0),'RAW development count is not 18');
need(word(0x53283360)===((0x13a00000|(15+count))>>>0)&&
  word(0x53283364)===((0x03a00000|(14+count))>>>0)&&
  word(0x532833bc)===((0xe3a00000|(15+count))>>>0),'RAW option capacity is not 21');
const indexPairs=[[0x532c2d60,0x532c2d64],[0x532c2d80,0x532c2d84],[0x532c2d00,0x532c2d04],
  [0x532c2f58,0x532c2f60],[0x532c2ff0,0x532c2ff8],[0x532c3074,0x532c307c]];
const indexTables=indexPairs.map(([low,high])=>pointer(low,high));
need(indexTables.every(address=>address===indexTables[0])&&inRtos(indexTables[0],18),
  'six still menu consumers do not share an in-range index table');
const stockOrder=old.subarray(oldRtosAt+0x53b59224-0x53000000,oldRtosAt+0x53b59224-0x53000000+12);
const expectedOrder=Buffer.concat([stockOrder,Buffer.from([25,26,27,28,29,30])]);
need(fresh.subarray(rtosAt+indexTables[0]-0x53000000,
  rtosAt+indexTables[0]-0x53000000+18).equals(expectedOrder),
  'still menu index-to-tone entries do not preserve stock and append six films');
for(const at of [0x5324b338,0x5324b400,0x5324b4a4,0x5324b5b8,0x5324b6e0])
  need(word(at)===0xe3001b28,'record allocation differs from stock 0xB28 size');
const unchangedHooks=[0x5323f274,0x5324b42c,0x5326cc40,
  0x5327b3a4,0x5327b3c4,0x5327b3e4,0x53826c54,0x53827218];
for(const at of unchangedHooks)need(word(at)===old.readUInt32LE(oldRtosAt+at-0x53000000),
  `candidate lifecycle/FS hook ${at.toString(16)} unexpectedly changed`);
const exif=pointer(0x53599e20,0x53599e2c);
need(inRtos(exif,72),
  'EXIF ImageTone table pointer outside RTOS');
const pairs=Array.from({length:count},(_,i)=>{
  const at=rtosAt+exif-0x53000000+48+4*i;
  return {tone:fresh[at],reserved:fresh[at+1],code:fresh.readUInt16LE(at+2)};
});
need(pairs.every((entry,i)=>entry.tone===25+i&&entry.reserved===0&&entry.code===0x10c+i),
  'EXIF ImageTone pair map differs');
console.log(JSON.stringify({source_sha256:official.sha256,
  candidate_sha256:createHash('sha256').update(candidate).digest('hex'),
  rtos_growth:report.rtosGrowth,changed_sections:report.changedSections,
  still_count:18,raw_count:18,raw_option_capacity:21,
  still_index_to_tone:[...expectedOrder],image_tone:pairs,
  record_allocation_bytes:0xb28,unchanged_lifecycle_and_fs_hooks:unchangedHooks.map(at=>`0x${at.toString(16)}`),
  independent_film_storage:false,
  protected_windows_unchanged:true,camera_tested:false,settings_persistence_verified:false},null,2));
