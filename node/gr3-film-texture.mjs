// Independent configuration readback of the pinned GRLife texture implementation.
// Verifies emitted code/selection, not camera memory behavior or image quality.
import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {inspectOfficial} from './firmware.mjs';import {decodeFrameMap} from './gr3-frames.mjs';
const need=(v,m)=>{if(!v)throw new Error(m);};
const sites={vivid:0x536db9a8,bleach:0x536dbdac,retro:0x536dbe88,hdr:0x536dbf3c,cross:0x536dc000};
const stored=[0,3,2,1],tones={vivid:12,bleach:18,retro:19,hdr:20,cross:21};
const templateSha='cf378eb62fec13d300c7207ef76422dc405e716503f138c70626003191067449';
export function auditFilmTexture(source,candidate,film,timestamp){
 inspectOfficial(source);
 const {decoded}=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8));
 const original=decodeFrameMap(source).decoded,texture=film.texture||{},diffusionLevel={};
 const word=a=>decoded.readUInt32LE(0x10870+a-0x53000000),old=a=>original.readUInt32LE(0x10870+a-0x53000000);
 for(const [mode,address] of Object.entries(sites)){
  const grain=texture[mode]?.grain||0,level=texture[mode]?.hdf||0;
  if(level)diffusionLevel[mode]=level;
  if(!grain){need(word(address)===old(address),`颗粒关闭位置 ${mode} 被修改`);continue;}
  if(mode!=='vivid')need(word(address)===(0xe3a06000|stored[grain])>>>0,`颗粒档位 ${mode} 不符`);
  else{
   const branch=word(address);need(branch>>>24===0xea,'Vivid颗粒分支无效');
   const target=address+8+((branch<<8)>>8)*4;
   need(target>=0x536ef61c&&target+20<=0x536ef6dc,'Vivid颗粒代码越界');
   need(word(target)===0xe5d3677c&&word(target+4)===0xe356000c&&word(target+8)===(0x03a06000|stored[grain])&&
    word(target+12)===0x13a06000,'Vivid/Positive颗粒分派不符');
   const ret=word(target+16);need(ret>>>24===0xea&&target+24+((ret<<8)>>8)*4===address+4,'Vivid颗粒返回分支不符');
  }
 }
 if(Object.keys(diffusionLevel).length){
  const raw=readFileSync(new URL('../.runtime/grlife/reconstruction/firmware_store/templates/urban160-film-texture.json',import.meta.url));
  need(createHash('sha256').update(raw).digest('hex')===templateSha,'柔光冻结模板摘要不符');
  const pinned=JSON.parse(raw),expected=Buffer.from(pinned.code_hex,'hex');
  const table=pinned.levels;
  for(let tone=11;tone<23;tone++){
   const mode=Object.keys(tones).find(m=>tones[m]===tone);expected[table.code_offset+tone-11]=mode?(texture[mode]?.hdf||0):0;
  }
  if(timestamp)Buffer.from('93fcffea','hex').copy(expected,0);
  const tail=0x10870+0x10b6000;
  need(decoded.subarray(tail+0x5000,tail+0x5000+expected.length).equals(expected),'柔光代码或档位与获准方案不符');
  need(decoded.subarray(tail+0x3380,tail+0x3384).toString('hex')==='200700eb','柔光捕获调用不符');
  need(word(0x535048e8)===0xeb2ed29f,'柔光入口未连接到原厂捕获链');
 }
 return {grain:Object.fromEntries(Object.entries(texture).map(([m,e])=>[m,e.grain])),diffusionLevel,
   codeVerified:true,cameraTested:false,descriptorIsolationVerified:false};
}
