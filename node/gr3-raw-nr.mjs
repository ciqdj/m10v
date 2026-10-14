// RAW/Bayer NR layout documented by gr3-film-mods 04d5d5d, MIT.
import {officialResources} from './gr3-stock-presets.mjs';
const thresholds=[400,800,1600,3200,5000,6400,8000,10000,12800];
const need=(v)=>{if(!v)throw new Error('RAW 降噪配置或原厂表无效');};
export function rawNrCapabilities(){return {modes:['stock','off','threshold'],thresholds:[...thresholds],jpegNr:'stock'};}
export function planRawNr(source,config={mode:'stock'}){
 need(config&&typeof config==='object'&&!Array.isArray(config)&&Object.keys(config).every(k=>['mode','iso'].includes(k))&&
 ['stock','off','threshold'].includes(config.mode));
 need(config.mode==='threshold'?thresholds.includes(config.iso):config.iso===undefined);
 if(config.mode==='stock')return [];
 const {decoded,sections}=officialResources(source),rtos=decoded.subarray(sections.RTOS.offset,sections.RTOS.offset+sections.RTOS.size);
 const edits=[];
 const put=(offset,expected,replacement)=>{need(rtos.subarray(offset,offset+expected.length).equals(expected));
 edits.push({section:'RTOS',offset,expectedHex:expected.toString('hex'),replacementHex:replacement.toString('hex'),owner:'raw-nr'});};
 if(config.mode==='off'){
 for(const [offset,expect,repl] of [[0x43326c,0x02266001,0xe3a06000],[0x433284,0x02277001,0xe3a07000],[0x642ac4,0x13834018,0x13834010]]){
  const a=Buffer.alloc(4),b=Buffer.alloc(4);a.writeUInt32LE(expect);b.writeUInt32LE(repl);put(offset,a,b);
 }
 }else{
 const first=Math.round(8*(Math.log2(config.iso/3.125)-1));
 for(let variant=0;variant<2;variant++){
  const table=rtos.readUInt32LE(0x107b540+0x375ec+variant*4);need(table>>>16===0x53ef);
  for(let index=0;index<first;index++){
   const offset=table-0x53000000+index*20,enable=rtos[offset];
   need(enable===(index<36?0:1));if(enable)put(offset,Buffer.from([1]),Buffer.from([0]));
  }
 }
 }
 return edits;
}
