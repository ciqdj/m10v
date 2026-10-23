// Read-only GR II reference comparison. Never builds or executes firmware.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {decodeUnity,readUnityModelComponent} from '../node/unity-firmware.mjs';
import {verifyUnityComponentChecksum} from '../node/unity-checksum.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const need=(ok,message)=>{if(!ok)throw Error(message);};
export const REFERENCE_SHA='c8fb8602b92bc7e4727080b538e6530b45fdf527aeb385a1d41f97a3687dbdbe';
export function loadRows(component){
  need(Buffer.isBuffer(component)&&component.length>=512,'executable header missing');
  need(component[16]===1&&component.readUInt32BE(0x168)===component.length,'executable identity/length differs');
  return Array.from({length:16},(_,index)=>{
    const at=32+20*index,source=component.readUInt32BE(at)+512,address=component.readUInt32BE(at+4),length=component.readUInt32BE(at+8);
    const zeroAddress=component.readUInt32BE(at+12),zeroLength=component.readUInt32BE(at+16);
    need(source%512===0&&source+length<=component.length&&address%4===0&&address+length<=0x100000000,'load range invalid');
    return {index,source,address,length,zeroAddress,zeroLength};
  });
}
export function compareLoaded(original,reference){
  const oldRows=loadRows(original),newRows=loadRows(reference),changes=[],added=[],recordExtensions=[],loadOverlaps=[],unmappedOriginal=[];
  for(let i=0;i<newRows.length;i++)for(const b of newRows.slice(i+1)){
    const a=newRows[i],lo=Math.max(a.address,b.address),hi=Math.min(a.address+a.length,b.address+b.length);
    if(hi>lo)loadOverlaps.push({records:[a.index,b.index],address:lo,length:hi-lo});
  }
  for(const old of oldRows){
    // Compare the same logical record when its destination is unchanged.
    // A staged bootstrap tail can temporarily occupy a later record's RAM;
    // it is not that later record's final executable bytes.
    const same=newRows.find(r=>r.index===old.index&&r.address===old.address);
    if(!same){if(old.length)unmappedOriginal.push(old);continue;}
    if(same.length>old.length)recordExtensions.push({oldRecord:old.index,newRecord:same.index,address:old.address+old.length,length:same.length-old.length});
    let covered=0;
    for(const next of [same]){
      const lo=Math.max(old.address,next.address),hi=Math.min(old.address+old.length,next.address+next.length);
      if(hi<=lo)continue;
      const before=original.subarray(old.source+lo-old.address,old.source+hi-old.address);
      const after=reference.subarray(next.source+lo-next.address,next.source+hi-next.address);
      covered+=hi-lo;let start=-1;
      for(let i=0;i<=before.length;i++){
        if(i<before.length&&before[i]!==after[i]){if(start<0)start=i;}
        else if(start>=0){
          changes.push({address:lo+start,length:i-start,oldRecord:old.index,newRecord:next.index,
            beforeHex:before.subarray(start,Math.min(i,start+32)).toString('hex'),afterHex:after.subarray(start,Math.min(i,start+32)).toString('hex')});start=-1;
        }
      }
    }
    need(covered<=old.length,'logical comparison exceeds original record');
  }
  for(const next of newRows){
    let spans=[[next.address,next.address+next.length]];
    for(const old of oldRows)spans=spans.flatMap(([lo,hi])=>{
      const a=Math.max(lo,old.address),b=Math.min(hi,old.address+old.length);
      return b<=a?[[lo,hi]]:[...(lo<a?[[lo,a]]:[]),...(b<hi?[[b,hi]]:[])];
    });
    for(const [lo,hi] of spans)if(hi>lo)added.push({address:lo,length:hi-lo,newRecord:next.index});
  }
  return {oldRows,newRows,recordExtensions,loadOverlaps,unmappedOriginal,changedBytes:changes.reduce((n,r)=>n+r.length,0),changes,added,
    oldEntry:original.readUInt32BE(0x160),newEntry:reference.readUInt32BE(0x160)};
}
export function decodeScatter(source,length,encoded){
  need(Buffer.isBuffer(source)&&Number.isInteger(length)&&length>0&&length%4===0&&length<=16*1024*1024&&typeof encoded==='boolean','invalid scatter arguments');
  const bytes=Buffer.alloc(length);let consumed=0,written=0;
  while(written<length){
    let count=length,zero=false;
    if(encoded){
      need(consumed+4<=source.length,'scatter count truncated');
      const tag=source.readUInt32BE(consumed);consumed+=4;count=tag&0x7fffffff;zero=!!(tag>>>31);
    }
    need(count>0&&count%4===0&&count<=length-written,'scatter count invalid');
    if(!zero){need(consumed+count<=source.length,'scatter literal truncated');source.copy(bytes,written,consumed,consumed+count);consumed+=count;}
    written+=count;
  }
  return {bytes,consumed};
}
function scatterInventory(component){
  // Fixed WNX-L1 table, identified from its early ARM branch and literal pool.
  // This decodes data only; neither the loader nor copied code is executed.
  const early=loadRows(component)[0];
  const off=address=>{const n=early.source+address-early.address;need(n>=early.source&&n+4<=early.source+early.length,'scatter table outside early module');return n;};
  const word=address=>component.readUInt32BE(off(address));
  const first=word(0xa00c4ce4),end=word(0xa00c4ce8);need(end>=first&&(end-first)%12===0&&(end-first)/12<=64,'scatter table size invalid');
  const entries=[];
  for(let cursor=first;cursor<end;cursor+=12){
    const source=word(cursor),address=word(cursor+4),control=word(cursor+8),length=control&0x7fffffff,encoded=!!(control>>>31);
    need(address%4===0&&address+length<=0x100000000,'scatter destination invalid');
    const result=decodeScatter(component.subarray(off(source),early.source+early.length),length,encoded);
    entries.push({source,address,length,encoded,sourceBytes:result.consumed,sha256:sha(result.bytes)});
  }
  return {tableAddress:first,entries,executed:false};
}
export function compareReference(official,reference){
  need(sha(reference)===REFERENCE_SHA,'reference is incomplete or not the pinned WNX-L1 artifact');
  const original=readUnityModelComponent(official,'gr2','b01firm8'),records=[];
  const visit=container=>{for(const row of container.records){records.push(row);if(row.nested)visit(row.nested);}};
  visit(decodeUnity(reference));const code=records.find(r=>r.name==='b01firm8');need(code,'reference executable missing');
  return {schema:'m10v-gr2-reference-diff/v1',referenceSha256:sha(reference),officialSha256:sha(official),
    referenceComponents:records.map(r=>({name:r.name,size:r.size,sha256:r.sha256})),
    scatter:scatterInventory(code.decoded),executableChecksum:verifyUnityComponentChecksum(code.decoded),...compareLoaded(original,code.decoded),
    scope:'Destination-aligned offline differences only; third-party code is not executed, installed or copied into M10V.',canPackage:false};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const [official,reference,out]=process.argv.slice(2);need(official&&reference&&out,'usage: node scripts/compare_gr2_reference.mjs OFFICIAL REFERENCE OUT.json');
  const report=compareReference(readFileSync(official),readFileSync(reference));writeFileSync(out,JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({changedBytes:report.changedBytes,changedRanges:report.changes.length,added:report.added,recordExtensions:report.recordExtensions,loadOverlaps:report.loadOverlaps,oldEntry:report.oldEntry,newEntry:report.newEntry,canPackage:false}));
}
