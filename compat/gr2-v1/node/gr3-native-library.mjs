// GR II v4 catalogue/state extracted from the pinned pre-ten-slot source.
import {readFile} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {normalizeConfiguration} from '../web/gr3/native-library-state.mjs';
const root=fileURLToPath(new URL('..',import.meta.url));
export async function nativeCatalog(){
 const source=await readFile(path.join(root,'native/gr3/m10v_library.c'),'utf8');
 const films=[...source.matchAll(/\{"([^"\n]+)",(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+),(-?\d+)\}/g)].map((m,i)=>({id:i+1,name:m[1]}));
 if(films.length!==33)throw Error('M10V 原生目录不完整');
 const legacy=JSON.parse(await readFile(path.join(root,'web/gr3/film-catalog.json'),'utf8')).looks;
 films.forEach(f=>f.group='M10V精选');
 films.push(...legacy.map((f,i)=>({id:34+i,name:f.name,group:f.group||'胶片模拟',legacy_id:f.id,color_path:'saved-jpeg-rgb-tables'})));
 films.push({id:66,key:'m10v-5207',name:'5207',group:'M10V精选',camera_calibrated:false,film_calibrated:false});
 films.push({id:67,key:'harman-phoenix-ii-200',name:'蓝凤凰',stock:'PhoenixII200',group:'M10V精选',camera_calibrated:false,film_calibrated:false},{id:68,key:'harman-red-125',name:'哈曼 RED',stock:'RED125',group:'M10V精选',camera_calibrated:false,film_calibrated:false});
 films.push(...[{id:69,key:'portra-160',name:'Portra 160'},{id:70,key:'fuji-industrial-100',name:'富士业务用 100'},{id:71,key:'lucky-c200-new',name:'乐凯 C200'},{id:72,key:'ccd-classic',name:'CCD Classic'}].map(f=>({...f,group:'M10V精选',camera_calibrated:false,film_calibrated:false})));
 films.push(...JSON.parse(readFileSync(path.join(root,'web/gr3/newstocks-luts.json'),'utf8')).stocks.map(({values,...f})=>({...f,group:'M10V精选',camera_calibrated:false,film_calibrated:false})));
 const icons=JSON.parse(await readFile(path.join(root,'web/gr3/film-icons/catalog.json'),'utf8'));
 if(icons.length!==films.length||icons.some((v,i)=>v.id!==films[i].id||v.name!==films[i].name))throw Error('M10V 图标目录与胶卷不同步');
 films.forEach((f,i)=>Object.assign(f,{icon_url:icons[i].icon_url,icon_color:icons[i].color}));
 const available=false; // Source availability is supplied by the GR II HTTP adapter.
 return {local_sources:['gr3','gr3x'],films:films.filter(f=>f.id>=33).sort((a,b)=>(a.group==='M10V精选'?0:1)-(b.group==='M10V精选'?0:1)),external_film_pack:true,camera_tested:false,local_source_available:available,
  scope:'保存的静态 JPEG 胶卷效果；取景使用 Standard 基底，尚无实时胶卷色彩；机内 RAW 再开发未接入',slot_tone_ids:[12,18,19,20,21]};
}
export function initialState(configuration){
 const c=normalizeConfiguration(configuration),b=Buffer.alloc(104);b.writeUInt32LE(0x5630314d);b.writeUInt16LE(4,4);b.writeUInt16LE(104,6);
 c.slots.forEach((s,i)=>{b.writeUInt16LE(s.film,12+i*8);b[14+i*8]=s.grain;b[15+i*8]=s.soft;b[16+i*8]=s.halo.gain;b[17+i*8]=s.halo.spread;b[18+i*8]=s.halo.threshold;b[19+i*8]=s.halo.profile;const e=s.effects;b[56+i*8]=e.grainSize;b[57+i*8]=e.leakGain;b[58+i*8]=e.leakPosition;b[59+i*8]=e.leakSpread;b[60+i*8]=e.leakVariation;b[61+i*8]=e.filmExposure;});
 b[52]=c.stamp;b[53]=c.format;b[54]=c.corner;b[55]=c.color;
 b.writeUInt32LE(c.filmNameStamp?1:0,96);
 let crc=0xffffffff;for(const byte of b.subarray(0,100)){crc^=byte;for(let k=0;k<8;k++)crc=(crc>>>1)^(0xedb88320&-(crc&1));}
 b.writeUInt32LE(~crc>>>0,100);return b;
}
