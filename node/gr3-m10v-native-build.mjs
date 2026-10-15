// M10V's original runtime is injected into the exact official GR III source.
// No browser compatibility runtime, signed film file or external catalog is used.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { inspectOfficial } from './firmware.mjs';
import { decodeFrameMap, sum32 } from './gr3-frames.mjs';
import { auditGr3Candidate } from './gr3-candidate-audit.mjs';

const LOAD = 0x53000000;
const nativeBases = [0x540b6000, 0x540ba000];
const sha = value => createHash('sha256').update(value).digest('hex');
const need = (condition, message) => { if (!condition) throw new Error(message); };
const hooks = [
  // Private enumeration belongs exclusively to ImageControlController.
  // Global model functions remain stock for ADJ, detail and generic consumers.
  [0x531ab78c,0xeb045cc2,'m10v_menu_count',true],
  [0x531ab7cc,0xeb045d2b,'m10v_menu_index',true],
  [0x531ab814,0xeb045ca0,'m10v_menu_count',true],
  [0x531ab834,0xeb045d11,'m10v_menu_index',true],
  [0x531ab930,0xeb045c59,'m10v_menu_count',true],
  [0x531ab96c,0xeb045cc3,'m10v_menu_index',true],
  [0x531ab9fc,0xeb045c26,'m10v_menu_count',true],
  [0x531abc2c,0xeb045bd2,'m10v_menu_max_count',true],
  [0x531abe34,0xeb045b18,'m10v_menu_count',true],
  [0x531abe88,0xeb045b7c,'m10v_menu_index',true], [0x532922b4,0xe351000a,'m10v_menu_name'],
  [0x532a985c,0xe1a0c00d,'m10v_menu_value_name'], [0x532935dc,0xe351000a,'m10v_menu_icon'],
  [0x532a9988,0xe1a0c00d,'m10v_menu_value_icon'], [0x531ab914,0xe1a0c00d,'m10v_menu_focus'],
  [0x531ac24c,0xe1a0c00d,'m10v_menu_confirm'], [0x531ac270,0xe1a0c00d,'m10v_menu_key'],
  [0x531ac140,0xe1a0c00d,'m10v_menu_enter'], [0x535048e8,0xeb069d0e,'m10v_chain_capture',true],
  [0x5320a834,0xe08ec106,'m10v_icon_pixels'],
  [0x533966e8,0xe3023bac,'m10v_resource_primary'], [0x533970fc,0xe3023bac,'m10v_resource_secondary'],
];
const sources = ['scripts/generate_m10v_icons.py','native/gr3/m10v_icons.rgba','native/gr3/m10v_stock_icon_directory.bin','native/gr3/m10v_legacy_data.h','web/gr3/film-catalog.json','scripts/generate_m10v_catalog.py','native/gr3/halation_core.c','native/gr3/halation_core.h','native/gr3/halation_energy.h','native/gr3/m10v_detail.c','scripts/build_gr3_native_detail.py','scripts/build_gr3_menu_patches.py','native/gr3/m10v_library.c','native/gr3/m10v_library.h',
  'native/gr3/m10v_library_camera.c','native/gr3/m10v_library_menu.c',
  'native/gr3/m10v_library_capture.c','native/gr3/m10v_debug.c','native/gr3/m10v_debug.h','scripts/build_gr3_m10v_library.py'];
const sdSources=['native/gr3/m10v_sd_library.h','native/gr3/m10v_sd_library.c','native/gr3/m10v_sd_camera.c','native/gr3/m10v_sd_contract.h','node/gr3-sd-film-pack.mjs','scripts/generate_gr3_sd_contract.mjs'];
export function nativeSourceFingerprint(){return sha(JSON.stringify([...sources,...sdSources].map(name=>[name,sha(readFileSync(new URL('../'+name,import.meta.url)))])));}
const movw = (register, value) => (0xe3000000 | ((value & 0xf000) << 4) | (register << 12) | (value & 0xfff)) >>> 0;
function branch(address, target, link=false) {
  const delta = target - address - 8;
  need(Number.isSafeInteger(target) && delta % 4 === 0 && delta >= -(2**25) && delta < 2**25,
    'native ARM branch target out of range');
  return ((link ? 0xeb000000 : 0xea000000) | ((delta >> 2) & 0xffffff)) >>> 0;
}
function checkRuntime(runtime, manifest) {
  const BASE=manifest?.base;
  need(nativeBases.includes(BASE), 'native runtime base invalid');
  need(Buffer.isBuffer(runtime) && runtime.length > 4096 && runtime.length <= 524288 && runtime.length % 4 === 0,
    'native runtime size invalid');
  need(manifest?.schema === 'm10v-gr3-native-film-runtime/v2' && manifest.base === BASE &&
    manifest.code_bytes === runtime.length && manifest.code_sha256 === sha(runtime), 'native runtime hash mismatch');
  need(manifest.film_count === 65 && manifest.slots === 5 && Array.isArray(manifest.dependencies) &&
    manifest.dependencies.length === 0 && !runtime.includes(Buffer.from('GRLIFE')), 'native runtime provenance differs');
  const expectedSources=manifest.sd_library?[...sources,...sdSources]:sources;
  need(typeof manifest.sd_library==='boolean','missing SD capability');
  need(!manifest.sd_library||(runtime.includes(Buffer.from('C:\\M10V\\FILMS.M10'))&&['m10v_sd_camera_item','m10v_sd_camera_install'].every(n=>Number.isInteger(manifest.symbols[n])&&manifest.symbols[n]>=BASE&&manifest.symbols[n]<BASE+runtime.length)),'SD runtime incomplete');
  need(Object.keys(manifest.sources || {}).sort().join('|') === [...expectedSources].sort().join('|'), 'native source inventory differs');
  for (const name of expectedSources) need(manifest.sources[name] === sha(readFileSync(new URL('../'+name,import.meta.url))),
    'native source changed since compilation: '+name);
  checkDetail(runtime,manifest);
  const init = Buffer.from(manifest.initial_state_hex || '', 'hex'), initAt = manifest.initial_state_offset;
  need(init.length === 64 && Number.isInteger(initAt) && initAt >= 0 && runtime.subarray(initAt,initAt+64).equals(init), 'native initial settings readback differs');
  need(typeof manifest.debug_mode==='boolean' && (manifest.debug_mode?
    manifest.debug_log?.schema==='m10v-gr3-sd-debug/v1'&&manifest.debug_log?.guard_address===0x5506821f&&
    /^[0-9a-f]{8}$/.test(manifest.debug_log.build_id)&&manifest.debug_log.page_bytes===4096&&manifest.debug_log.records_per_channel===63&&
    JSON.stringify(manifest.debug_log.files)===JSON.stringify(['M10VMN0.BIN','M10VMN1.BIN','M10VCP0.BIN','M10VCP1.BIN'])&&
    manifest.debug_log.files.every(name=>runtime.includes(Buffer.from('C:\\'+name))):
    !manifest.debug_log&&!manifest.symbols?.m10v_debug_log&&!runtime.includes(Buffer.from('C:\\M10VMN'))&&!runtime.includes(Buffer.from('C:\\M10VCP'))),'native debug contract differs');
  for (const name of [...hooks.map(row=>row[2]), 'm10v_capture_library',...(manifest.debug_mode?['m10v_debug_log']:[])]) {
    const address = manifest.symbols?.[name];
    need(Number.isInteger(address) && address % 4 === 0 && address >= BASE + 0x100 && address < BASE + runtime.length,
      'native symbol outside module: '+name);
  }
  const icons=manifest.icons, stock=readFileSync(new URL('../native/gr3/m10v_stock_icon_directory.bin',import.meta.url)), artwork=readFileSync(new URL('../native/gr3/m10v_icons.rgba',import.meta.url));
  need(icons?.first_id===671&&icons.last_id===735&&icons.width===40&&icons.height===40&&artwork.length===65*6400&&icons.sha256===sha(artwork),'native icon inventory differs');
  for(const [address,length] of [[icons.table,736*4],[icons.descriptors,65*8],[icons.pixels,65*6400]])need(Number.isInteger(address)&&address%4===0&&address>=BASE&&address+length<=BASE+runtime.length,'native icon address outside module');
  need(icons.descriptors===icons.table+736*4&&icons.pixels===icons.descriptors+65*8&&runtime.subarray(icons.table-BASE,icons.table-BASE+stock.length).equals(stock)&&runtime.subarray(icons.pixels-BASE,icons.pixels-BASE+artwork.length).equals(artwork),'native icon readback differs');
  for(let i=0;i<65;i++){
    const descriptor=icons.descriptors+i*8,at=descriptor-BASE;
    need(runtime.readUInt32LE(icons.table-BASE+(671+i)*4)===descriptor&&runtime.readUInt16LE(at)===40&&runtime.readUInt16LE(at+2)===40&&runtime.readUInt32LE(at+4)*4===icons.pixels+i*6400,'native icon descriptor differs');
  }
  const resourceCount=manifest.sd_library?129:125;
  need(manifest.resources?.first_id === 786 && manifest.resources.last_id === 785+resourceCount &&
    manifest.resources.texts?.length === resourceCount && manifest.resources.descriptors?.length === resourceCount, 'native resources incomplete');
  for (let i=0;i<resourceCount;i++) {
    const at = manifest.resources.descriptors[i] - BASE, text = manifest.resources.texts[i];
    need(Number.isInteger(at) && at >= 0 && at + 8 < runtime.length && typeof text === 'string', 'native text pointer invalid');
    const encoded = Buffer.from(text+'\0','utf16le');
    need(runtime[at] === encoded.length/2 && runtime[at+1] === 1 && runtime.readUInt16LE(at+2) === 0 &&
      runtime.readUInt32LE(at+4) === BASE + at + 8 && runtime.subarray(at+8,at+8+encoded.length).equals(encoded),
      'native UTF16 resource differs');
  }
}
const detailHooks=[
 [0x531afc20,0xebffffa4,'capacity',true],
 [0x531afa24,0xe345c3b3,'table_ip',true],[0x531afacc,0xe34533b3,'table_r3',true],
 [0x531affa8,0xe345c3b3,'table_ip',true],[0x531b01f8,0xe34533b3,'table_selected',true],
 [0x531b000c,0xea000066,'row',false],[0x531b03f8,0xea000065,'current',false],
 [0x531b05e4,0xea00005c,'setup',false],[0x531b0bf4,0xea000093,'callback',false],
 [0x531acd24,0xeb0456c0,'reset',true]];
const detailInstructions={"capacity":[0xe3a00010,0xe12fff1e],"table_ip":[3912065023,3775856640,3912040451,3852271624,[14,true,"m10v_detail_table"],3851223096,3904700419,3777818624,0xe3a0e00c,3904741375],"table_r3":[3912065023,3775856640,3912040451,3852271624,[14,true,"m10v_detail_table"],3851223060,3904700419,3777818624,3904741375],"table_selected":[3912065023,3775856640,3912040451,3852271640,[14,true,"m10v_detail_table"],3851223060,3904700419,3777818624,3904741375],"row":[3796090898,3814457348,[8,false,1394278828],3912060943,3785359365,[14,true,"m10v_detail_table"],3808741516,3813000115,3780116492,3904720911,[0,false,1394278828],3796049938,3785369602,3783401476,3785363461,3818913795,[14,true,"m10v_detail_control"],[14,false,1394278500]],"current":[3796156434,3814457348,[8,false,1394279828],3912060943,3785359365,[14,true,"m10v_detail_table"],3808741516,3813000115,3780116492,3904720911,[0,false,1394279828],3796115474,3785363461,3818913793,[14,true,"m10v_detail_control"],3785375744,[14,false,1394279516]],"default":[3785363456,3818913796,3818921984,[14,false,"m10v_detail_control"]],"setup":[3795894290,3814457348,[8,false,1394280284],3912060943,3785359364,[14,true,"m10v_detail_table"],3808741516,3813000115,3780116492,3904720911,[0,false,1394280284],3813670933,3785359364,3796619280,3902629904,[3,false,"slider8"],[14,false,"slider3"]],"callback":[3796221970,3814457348,[8,false,1394282056],3912060943,3785359364,[14,true,"m10v_detail_table"],3808741516,3813000115,3780116492,3904720911,[0,false,1394282056],3796181010,3785368578,3783401478,3785363460,3818913794,[14,true,"m10v_detail_control"],3813670912,[1,false,1394281580],3796619292,3902646512],"reset":[3912056848,[14,true,1395402796],3785363461,3818913799,3818921984,[14,true,"m10v_detail_control"],3904733200]};
function checkDetail(runtime,manifest,raw) {
 const d=manifest.detail,base=manifest.base;
 need(d?.schema==='m10v-gr3-native-detail/v1'&&d.backend==='m10v_camera_library_detail'&&
  JSON.stringify(d.ids)==='[18,19,20,21,22]'&&JSON.stringify(d.fields)===JSON.stringify(['Halation Gain','Halation Spread','Highlight Gate','Film Grain','Soft Diffusion']), 'native detail contract differs');
 const read=(a,n)=>{need(Number.isInteger(a)&&a%4===0&&a>=base&&a+n<=base+runtime.length,'native detail address outside module');return runtime.subarray(a-base,a-base+n);};
 const table=read(d.tables,288),captions=read(d.captions,92);
 const expectedIds=[862,863,864,827,828];
 for(let i=0;i<5;i++)need(captions.readUInt16LE(72+i*4)===expectedIds[i]&&captions.readUInt16LE(74+i*4)===expectedIds[i],'native detail caption differs');
 for(const name of ['m10v_detail_table','m10v_detail_control','m10v_camera_library_detail'])read(manifest.symbols[name],4);
 for(const [name,template] of Object.entries(detailInstructions)){
  const at=d.entries?.[name],code=read(at,template.length*4);
  for(let i=0;i<template.length;i++){
   const instruction=template[i];let word=instruction;
   if(Array.isArray(instruction)){
    const [condition,link,target]=instruction,to=typeof target==='string'?(manifest.symbols[target]??d[target]):target;
    word=((branch(at+i*4,to,link)&0x0fffffff)|(condition<<28))>>>0;
   }
   need(code.readUInt32LE(i*4)===word,'native detail instruction differs: '+name+' '+i);
  }
 }
 // Exact stock entry bytes and list prefix are compared to the freshly decoded
 // official source, never to a manifest-supplied preimage or instruction list.
 if(raw){
  need(captions.subarray(0,72).equals(raw.subarray(0xb34bd8,0xb34c20)),'native detail stock captions differ');
  for(let i=0;i<36;i++){
   const old=0xb3488c+i*8,p=raw.readUInt32LE(old),n=raw.readUInt32LE(old+4),fresh=table.readUInt32LE(i*8);
   need(table.readUInt32LE(i*8+4)===n+5,'native detail count differs');
   const list=read(fresh,n*2+10);
   need(list.subarray(0,n*2).equals(raw.subarray(p-LOAD,p-LOAD+n*2))&&list.subarray(n*2).equals(Buffer.from([0,18,0,19,0,20,0,21,0,22])),'native detail list differs');
  }
  for(const [target,maximum] of [[d.slider8,8],[d.slider3,3]]){
   const start=0x531acfec,stop=0x531ad12c,code=read(target,stop-start+8),mapped=a=>target+a-start+(a>=0x531ad0b4?8:0);
   for(let a=start;a<stop;a+=4){
    const at=mapped(a);let word=raw.readUInt32LE(a-LOAD);
    if((word&0x0e000000)===0x0a000000){let delta=(word&0xffffff)<<2;if(delta&0x2000000)delta-=0x4000000;let to=a+8+delta;if(to>=start&&to<=stop)to=mapped(to);word=((word&0xf0000000)|((word&0x1000000)?0x0b000000:0x0a000000)|(((to-at-8)>>2)&0xffffff))>>>0;}
    if(a===0x531ad01c)word=0xe1a00006;
    if(a===0x531ad020)word=branch(at,d.entries.default,true);
    if(a===0x531ad024)word=0xe1a00000;
    if(a===0x531ad03c&&maximum===3)word=0xe3a03039;
    if(a===0x531ad060)word=(0xe3a02000|maximum)>>>0;
    if(a===0x531ad064&&maximum===3)word=0xe3a03078;
    need(code.readUInt32LE(at-target)===word,'native detail slider relocation differs at '+a.toString(16)+' expected '+word.toString(16)+' got '+code.readUInt32LE(at-target).toString(16));
   }
   const guard=0x531ad0b4-start;
   need(code.readUInt32LE(guard)===0xe3500000&&code.readUInt32LE(guard+4)===(branch(target+guard+4,mapped(0x531ad110))&0x0fffffff),'native detail null guard differs');
  }
 }
}
function patchList(manifest) {
  const table=manifest.icons.table, movt=(reg,v)=>(0xe3400000|((v&0xf000)<<4)|(reg<<12)|(v&0xfff))>>>0;
  const iconPatches=[[0x53209fcc,0xe30230fc,3,false],[0x53209fd0,0xe3453500,3,true],[0x5320a000,0xe30230fc,3,false],[0x5320a004,0xe3453500,3,true],[0x5320a804,0xe30220fc,2,false],[0x5320a808,0xe3452500,2,true]].map(([address,expected,reg,upper])=>({address,expected,replacement:upper?movt(reg,table>>>16):movw(reg,table&65535),name:'M10V icon directory '+address.toString(16)}));
  for(const [address,expected,reg] of [[0x53209fb8,0xe300329e,3],[0x53209fec,0xe300329e,3],[0x5320a7cc,0xe300129e,1]])iconPatches.push({address,expected,replacement:movw(reg,735),name:'M10V icon maximum '+address.toString(16)});
  const detailPatches=detailHooks.map(([address,expected,name,link])=>({address,expected,replacement:branch(address,manifest.detail.entries[name],link),name:'native detail '+name}));
  detailPatches.push({address:0x531b0248,expected:0xe3043bd8,replacement:movw(3,manifest.detail.captions&65535),name:'detail captions low'},{address:0x531b024c,expected:0xe34533b3,replacement:movt(3,manifest.detail.captions>>>16),name:'detail captions high'});
  return [...detailPatches,...iconPatches,...hooks.map(([address,expected,name,link])=>({address, expected,
    replacement:branch(address,manifest.symbols[name],link),name})),
    {address:0x533966d4,expected:0xe3003311,replacement:movw(3,manifest.resources.last_id),name:'resource maximum primary'},
    {address:0x533970ec,expected:0xe3003311,replacement:movw(3,manifest.resources.last_id),name:'resource maximum secondary'},
    {address:0x531abd24,expected:0xe300110a,replacement:movw(1,823),name:'M10V menu title'}];
}
function sectionMap(decoded, report, growth=0) {
  let offset=0; const rows=[];
  for (const original of report.sections) {
    const size=original.size+(original.name==='RTOS'?growth:0);
    need(decoded.toString('ascii',offset,offset+8).split('\0')[0]===original.name && offset+size<=decoded.length-4,
      'native section boundaries differ');
    rows.push({name:original.name,offset,size}); offset+=size;
  }
  need(offset+4===decoded.length,'native decoded trailer position differs'); return rows;
}
function encodeExtended(source, original, target, insertion, growth) {
  const frames=decodeFrameMap(source).frames, chunks=[];
  for (const frame of frames) {
    const start=frame.decoded_start+(frame.decoded_start>insertion?growth:0);
    const end=frame.decoded_end+(frame.decoded_end>insertion?growth:0);
    const bytes=target.subarray(start,end), old=original.subarray(frame.decoded_start,frame.decoded_end);
    // Back references may cross frame boundaries. Reuse only when the entire
    // 2047-byte history window remains identical after insertion or a patch.
    const history=Math.min(2047,frame.decoded_start);
    const sameHistory=target.subarray(start-history,start).equals(original.subarray(frame.decoded_start-history,frame.decoded_start));
    if(bytes.equals(old)&&sameHistory) chunks.push(source.subarray(128+frame.encoded_start,128+frame.encoded_end));
    else for(let at=0;at<bytes.length;at+=0x6000){
      const part=bytes.subarray(at,at+0x6000),prefix=Buffer.alloc(2);
      prefix.writeUInt16BE(0x8000|part.length);chunks.push(prefix,part);
    }
  }
  chunks.push(Buffer.alloc(2)); const payload=Buffer.concat(chunks),footer=Buffer.from(source.subarray(-24));
  footer.writeUInt32LE(payload.length,12);footer.writeUInt32LE(target.length,16);footer.writeUInt32LE(0,20);
  const candidate=Buffer.concat([source.subarray(0,128),payload,Buffer.alloc(-(128+payload.length)&3),footer]);
  candidate.writeUInt32LE(-sum32(candidate)>>>0,candidate.length-4);
  need(decodeFrameMap(candidate,target.length).decoded.equals(target),'native fresh decode differs'); return candidate;
}
export function buildNativeLibrary(source,runtime,manifest) {
  const BASE=manifest?.base;
  const report=inspectOfficial(source);need(report.model==='GR III','native detail requires exact GR III 2.10 official source');checkRuntime(runtime,manifest);
  const {decoded}=decodeFrameMap(source),rows=sectionMap(decoded,report),rtos=rows.find(row=>row.name==='RTOS');
  const programOffset=BASE-LOAD,newPayload=programOffset+runtime.length;
  const growth=newPayload-(rtos.size-16);need(growth>0&&growth<=524288,'native RTOS growth invalid');
  const insertion=rtos.offset+rtos.size;
  const target=Buffer.concat([decoded.subarray(0,insertion),Buffer.alloc(growth),decoded.subarray(insertion)]);
  target.writeUInt32LE(newPayload,rtos.offset+12);
  runtime.copy(target,rtos.offset+16+programOffset);
  for(const patch of patchList(manifest)) {
    const at=rtos.offset+16+patch.address-LOAD;
    need(decoded.readUInt32LE(at)===patch.expected,'official native hook preimage differs: '+patch.name);
    target.writeUInt32LE(patch.replacement,at);
  }
  target.writeUInt32LE(0,target.length-4);target.writeUInt32LE(-sum32(target)>>>0,target.length-4);
  const candidate=encodeExtended(source,decoded,target,insertion,growth);
  return {candidate,receipt:auditNativeLibrary(source,candidate,runtime,manifest)};
}
export function auditNativeLibrary(source,candidate,runtime,manifest) {
  const BASE=manifest?.base;
  const report=inspectOfficial(source);need(report.model==='GR III','native detail requires exact GR III 2.10 official source');checkRuntime(runtime,manifest);
  const structural=auditGr3Candidate(source,candidate,{maxRtosGrowth:512*1024});
  const before=decodeFrameMap(source).decoded,after=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8)).decoded;
  const oldRows=sectionMap(before,report),newRows=sectionMap(after,report,structural.rtosGrowth);
  const old=oldRows.find(row=>row.name==='RTOS'),fresh=newRows.find(row=>row.name==='RTOS');
  const raw=before.subarray(old.offset+16,old.offset+old.size);
  checkDetail(runtime,manifest,raw);
  const stockDirectory=raw.subarray(0x107b540+0x20fc,0x107b540+0x20fc+671*4);
  need(stockDirectory.equals(runtime.subarray(manifest.icons.table-BASE,manifest.icons.table-BASE+671*4)),'official icon directory differs');
  const table=raw.readUInt32LE(0x434)-LOAD,domains=raw.readUInt32LE(0x438);
  for(let address=BASE;address<BASE+runtime.length;address=(address&0xfff00000)+0x100000){
    const descriptor=raw.readUInt32LE(table+(address>>>20)*4),domain=(descriptor>>>5)&15;
    need((descriptor&3)===2&&!(descriptor&16)&&((descriptor>>>10)&3)===2&&(descriptor&(1<<15))&&((domains>>>(domain*2))&3)===1&&
      (descriptor>>>20)===(address>>>20),'native full runtime/data mapping differs');
  }

  need(fresh.size-16===BASE-LOAD+runtime.length,'native RTOS extent differs');
  need(after.readUInt32LE(fresh.offset+8)===before.readUInt32LE(old.offset+8),'native RTOS flags differ');
  const expected=Buffer.from(before.subarray(old.offset+16,old.offset+old.size));
  for(const patch of patchList(manifest)) {
    const at=patch.address-LOAD;
    need(expected.readUInt32LE(at)===patch.expected,'native audit stock preimage differs');
    expected.writeUInt32LE(patch.replacement,at);
  }
  need(after.subarray(fresh.offset+16,fresh.offset+old.size).equals(expected),'native RTOS non-target bytes changed');
  const padding=after.subarray(fresh.offset+old.size,fresh.offset+16+BASE-LOAD);
  need(padding.every(value=>value===0),'native extension gap is not zero');
  need(after.subarray(fresh.offset+16+BASE-LOAD,fresh.offset+fresh.size).equals(runtime),'native full module readback differs');
  for(let i=0;i<oldRows.length;i++)if(oldRows[i].name!=='RTOS') {
    const a=oldRows[i],b=newRows[i];need(after.subarray(b.offset,b.offset+b.size).equals(before.subarray(a.offset,a.offset+a.size)),
      'native changed unrelated section '+a.name);
  }
  for(const [a,b] of [[0x620000,0x640000],[0x820000,0x840000],[0x2038,0x203c]])
    need(after.subarray(fresh.offset+16+a,fresh.offset+16+b).equals(before.subarray(old.offset+16+a,old.offset+16+b)),
      'native updater/version protection differs');
  return {schema:'m10v-gr3-native-library-candidate/v2',source_sha256:report.sha256,candidate_sha256:sha(candidate),
    candidate_bytes:candidate.length,runtime_sha256:sha(runtime),runtime_bytes:runtime.length,
    rtos_growth:structural.rtosGrowth,changed_sections:structural.changedSections,
    verified_hooks:patchList(manifest).length,icon_count:65,icon_dimensions:[40,40],icon_storage:'embedded RTOS; original ICONBIN unchanged',mapping_verified:true,state_version:2,film_count:65,active_slots:5,external_film_pack:manifest.sd_library,sd_film_library:manifest.sd_library?{format:1,path:"M10V/FILMS.M10",supported_films:33,max_records:256,page_rows:8}:null,
    menu_entry:manifest.sd_library?'MENU > Image Control > 胶卷库':'MENU > Image Control > M10V Library',adj_scope:'12 stock entries only; no private IDs',
    camera_tested:false,debug_mode:manifest.debug_mode,debug_log:manifest.debug_log,status:'OFFLINE_VERIFIED_EXPERIMENTAL_CANDIDATE',
    camera_scope:'still JPEG; original RAW pixels protected; live-view color and RAW-development effects not integrated'};
}
