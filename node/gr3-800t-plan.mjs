import { readFileSync } from 'node:fs';
const catalog=JSON.parse(readFileSync(new URL('../web/gr3/film-catalog.json',import.meta.url))).looks;
const base=catalog.find((film)=>film.id==='v3-500t');
const modes=['vivid','retro','hdr','cross','bleach'];
export function normalize800T(input) {
  if (!input || typeof input!=='object' || Array.isArray(input) ||
      Object.keys(input).some((key)=>!['strength','timestamp','slot'].includes(key)) ||
      !['weak','strong'].includes(input.strength) ||
      (input.timestamp!==undefined && typeof input.timestamp!=='boolean') ||
      (input.slot!==undefined && !modes.includes(input.slot))) throw new Error('800T 配置无效：请选择弱/强档、胶片槽位与时间戳。');
  return { strength:input.strength,timestamp:input.timestamp??false,slot:input.slot??'bleach' };
}
export function create800TFilm() {
  if (!base) throw new Error('800T reference film data missing');
  const film=structuredClone(base);
  // Cyan shadows, chroma separation and a mild negative-film contrast curve.
  // Unpaired scans do not determine an exact emulsion response or camera ISP LUT.
  film.id='lut-800t';film.name='800T';film.home=null;
  film.curves=film.curves.map((curve,channel)=>{
    let last=0;
    return curve.map((value,index)=>{
      const t=index/255,u=value/16383;
      const contrast=u+0.12*(u-0.5)*4*u*(1-u);
      const delta=[-0.020,0.025,0.006][channel]*16383*Math.sin(Math.PI*t)*(1-t);
      last=Math.max(last,Math.min(16383,Math.max(0,Math.round(contrast*16383+delta))));return last;
    });
  });
  // Compose a neutral-preserving saturation matrix after the trusted tables.
  const luma=[0.2126,0.7152,0.0722],saturation=1.16;
  const post=film.postQ512;
  film.postQ512=Array.from({length:9},(_,i)=>{
    const row=Math.floor(i/3),column=i%3;
    return Math.round([0,1,2].reduce((sum,k)=>sum+
      ((row===k?saturation:0)+(1-saturation)*luma[k])*post[k*3+column],0));
  });
  for(let row=0;row<3;row++)film.postQ512[row*3+row]+=512-
    film.postQ512.slice(row*3,row*3+3).reduce((sum,v)=>sum+v,0);
  film.knots=film.curves.map((curve)=>Array.from({length:33},(_,i)=>curve[Math.round(i*255/32)]));
  film.provenance={baseId:'v3-500t',calibration:'experimental_unpaired_reference',
    shaping:'balanced-blue-cyan/v4',redHalation:'separate_native_spatial_kernel'};
  return film;
}
