// Intent checker reads actual candidate pointers/text/pixels; never imports edit planner.
import {inspectOfficial} from './firmware.mjs';import {decodeFrameMap} from './gr3-frames.mjs';
const ids=[[358,4],[548,268],[354,269],[357,270],[350,271],[352,272],[232,274],[346,275],[356,276],[351,277],[50,278],[23,273]];
const need=(v,m)=>{if(!v)throw new Error(m);};
export function auditStockIntent(source,candidate,selection){
 const report=inspectOfficial(source),{decoded}=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8));
 let position=0;const rows={};
 for(const section of report.sections){const size=section.name==='RTOS'?decoded.readUInt32LE(position+12):section.size-16;
  need(decoded.toString('ascii',position,position+8).split('\0')[0]===section.name&&position+16+size<=decoded.length-4,'分区意图回读失败');
  rows[section.name]={start:position+16,size};position+=16+size;}
 const off=(va,size=4)=>{if(va>=0x55000000&&va<0x5503a080)va=va-0x55000000+0x5407b540;
  const offset=va-0x53000000;need(offset>=0&&offset+size<=rows.RTOS.size,'名称指针越界');return rows.RTOS.start+offset;};
 const word=va=>decoded.readUInt32LE(off(va));
 const text=(id,lang)=>{const record=off(word(word(0x55002bac+lang*4)+id*4),8),count=decoded[record];
  need(count>=2&&decoded[record+1]===1&&decoded.readUInt16LE(record+2)===0,'名称格式无效');
  const at=off(decoded.readUInt32LE(record+4),count*2);need(decoded.readUInt16LE(at+(count-1)*2)===0,'名称终止符无效');
  return decoded.toString('utf16le',at,at+(count-1)*2);};
 need(word(0x53b348bc)===0x53b3500c&&word(0x53b348c0)===(selection.negativeGrainMenu?10:9),'负片颗粒菜单与选择不符');
 if(selection.negativeGrainMenu)need(decoded.subarray(off(0x53b3501e,2),off(0x53b3501e,2)+2).toString('hex')==='020f','负片颗粒项不符');
 for(const preset of selection.stockPresets||[]){
  const [iconId,stringId]=ids[preset.slot-1];
  if(preset.name!==undefined)need(text(stringId,1)===preset.name&&text(stringId,19)===preset.name,'机内名称与获准配置不符');
  if(preset.iconPixelsBase64){
   const descriptor=off(word(0x550020fc+iconId*4),8),width=decoded.readUInt16LE(descriptor),height=decoded.readUInt16LE(descriptor+2);
   const at=rows.ICONBIN.start+decoded.readUInt32LE(descriptor+4)*4;
   need(width===40&&height===40&&at+6400<=rows.ICONBIN.start+rows.ICONBIN.size&&
    decoded.subarray(at,at+6400).equals(Buffer.from(preset.iconPixelsBase64,'base64')),'机内图标与获准配置不符');
  }
 }
 return {verified:true,negativeGrainMenu:!!selection.negativeGrainMenu,presetCount:(selection.stockPresets||[]).length};
}
