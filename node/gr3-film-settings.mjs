import {filmToneMap} from './gr3-appended-films.mjs';

const MAGIC=Buffer.from('M10VFSET','ascii');
const HEADER=20, RECORD=64, SCHEMA=1;
const need=(ok,message)=>{if(!ok)throw new Error(message);};
const crcTable=Uint32Array.from({length:256},(_,i)=>{
  let value=i;for(let k=0;k<8;k++)value=(value&1)?(0xedb88320^(value>>>1)):(value>>>1);
  return value>>>0;
});
function crc32(bytes){let crc=0xffffffff;for(let i=0;i<bytes.length;i++)crc=crcTable[(crc^bytes[i])&255]^(crc>>>8);return (crc^0xffffffff)>>>0;}
function checksum(bytes){const copy=Buffer.from(bytes);copy.writeUInt32LE(0,16);return crc32(copy);}

export function encodeFilmSettings(settings,toneMap){
  need(Array.isArray(settings)&&Array.isArray(toneMap)&&settings.length<=6,'胶片参数数量无效');
  const verified=filmToneMap(toneMap.map(({id})=>({id})));
  need(toneMap.every((entry,i)=>['tone','rawEnum','recordSlot'].every(key=>entry[key]===verified[i][key])),
    '胶片模式映射不一致');
  const byId=new Map(verified.map(entry=>[entry.id,entry]));
  const seen=new Set(),out=Buffer.alloc(HEADER+settings.length*RECORD);
  MAGIC.copy(out,0);out.writeUInt16LE(SCHEMA,8);out.writeUInt16LE(settings.length,10);
  out.writeUInt32LE(out.length,12);
  for(const [i,item] of settings.entries()){
    need(item&&typeof item==='object'&&byId.has(item.id)&&item.id.length<=31&&!seen.has(item.id),'胶片参数ID无效或重复');
    seen.add(item.id);
    need(Array.isArray(item.banks)&&item.banks.length===3&&item.banks.every(bank=>
      Array.isArray(bank)&&bank.length===9&&bank.every(value=>Number.isInteger(value)&&value>=-4&&value<=4)),
      '胶片九项参数必须为三组-4至+4整数');
    need(Number.isInteger(item.grain)&&item.grain>=0&&item.grain<=3,'胶片颗粒档位无效');
    const at=HEADER+i*RECORD,entry=byId.get(item.id);
    out.write(item.id,at,32,'ascii');
    out[at+32]=entry.tone;out[at+33]=entry.recordSlot;out[at+34]=entry.rawEnum;
    for(let j=0;j<27;j++)out.writeInt8(item.banks[Math.floor(j/9)][j%9],at+36+j);
    out[at+63]=item.grain;
  }
  out.writeUInt32LE(checksum(out),16);
  return out;
}

export function decodeFilmSettings(bytes,toneMap){
  const fallback=reason=>({settings:[],recovered:true,reason});
  try{
    if(Array.isArray(toneMap)&&toneMap.length===0)return fallback('removed_film');
    const current=filmToneMap(toneMap.map(({id})=>({id})));
    if(!Buffer.isBuffer(bytes)||bytes.length<HEADER||!bytes.subarray(0,8).equals(MAGIC))return fallback('magic');
    if(bytes.readUInt16LE(8)!==SCHEMA)return fallback('schema');
    const count=bytes.readUInt16LE(10);
    if(count>6||bytes.readUInt32LE(12)!==bytes.length||bytes.length!==HEADER+count*RECORD)return fallback('length');
    if(bytes.readUInt32LE(16)!==checksum(bytes))return fallback('crc');
    const byId=new Map(current.map(entry=>[entry.id,entry]));
    const seen=new Set(),settings=[];let removed=false;
    for(let i=0;i<count;i++){
      const at=HEADER+i*RECORD,field=bytes.subarray(at,at+32),end=field.indexOf(0);
      if(end<1||field.subarray(end).some(byte=>byte!==0))return fallback('id');
      const id=field.toString('ascii',0,end);
      if(!/^[a-z][a-z0-9-]{0,30}$/.test(id)||seen.has(id))return fallback('id');
      seen.add(id);
      if(bytes[at+35]!==0)return fallback('flags');
      const oldIndex=bytes[at+32]-25;
      if(oldIndex<0||oldIndex>5||bytes[at+34]!==13+oldIndex||
        bytes[at+33]!==[1,2,3,4,5,7][oldIndex])return fallback('mapping');
      const banks=Array.from({length:3},(_,b)=>Array.from({length:9},(_,j)=>bytes.readInt8(at+36+b*9+j)));
      if(banks.some(bank=>bank.some(value=>value<-4||value>4))||bytes[at+63]>3)return fallback('values');
      const entry=byId.get(id);
      if(!entry){removed=true;continue;}
      settings.push({id,tone:entry.tone,rawEnum:entry.rawEnum,recordSlot:entry.recordSlot,banks,grain:bytes[at+63]});
    }
    return {settings,recovered:removed,reason:removed?'removed_film':null};
  }catch{return fallback('invalid');}
}
