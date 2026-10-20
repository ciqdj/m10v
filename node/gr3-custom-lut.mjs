import {createHash} from 'node:crypto';

const fail=message=>{throw Error(message);};
const token=/^(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$|^\.\d+(?:[eE][+-]?\d+)?$/;
export function parseCustomCube(bytes,filename,name){
 if(!Buffer.isBuffer(bytes)||!bytes.length||bytes.length>8*1024*1024)fail('LUT 文件必须非空且不超过 8 MiB');
 if(!/^[^/\\\0]{1,100}\.cube$/i.test(filename))fail('请选择 .cube 文件');
 if(typeof name!=='string'||name.trim()!==name||!/^[\x20-\x7e]{1,23}$/.test(name))fail('胶卷名称须为 1–23 个英文字符');
 const lines=bytes.toString('utf8').replace(/^\uFEFF/,'').split(/\r?\n/);let size=0,domainMin=false,domainMax=false;const values=[];
 for(const raw of lines){const line=raw.split('#',1)[0].trim();if(!line)continue;
  const parts=line.split(/\s+/),key=parts[0].toUpperCase();
  if(key==='TITLE')continue;
  if(key==='LUT_3D_SIZE'){
   if(size||parts.length!==2||!/^\d+$/.test(parts[1]))fail('LUT 尺寸无效');
   size=Number(parts[1]);if(size<2||size>65)fail('LUT 尺寸须为 2–65');continue;
  }
  if(key==='DOMAIN_MIN'||key==='DOMAIN_MAX'){
   const exact=key==='DOMAIN_MIN'?'0':'1';if(parts.length!==4||parts.slice(1).some(v=>Number(v)!==Number(exact)))fail('仅支持 sRGB 0–1 输入范围');
   if(key==='DOMAIN_MIN')domainMin=true;else domainMax=true;continue;
  }
  if(parts.length!==3||parts.some(v=>!token.test(v)))fail('仅支持完整的 3D .cube 数值表');
  const row=parts.map(Number);if(row.some(v=>!Number.isFinite(v)||v<0||v>1))fail('LUT 输出须在 0–1 范围');
  values.push(...row);
 }
 if(!size||values.length!==size**3*3)fail('LUT 数据行数与尺寸不符');
 const sample=(r,g,b,c)=>{
  const at=(x,y,z)=>values[((z*size+y)*size+x)*3+c];
  const rx=r*(size-1),gx=g*(size-1),bx=b*(size-1),x=Math.floor(rx),y=Math.floor(gx),z=Math.floor(bx);
  const xx=Math.min(x+1,size-1),yy=Math.min(y+1,size-1),zz=Math.min(z+1,size-1),fx=rx-x,fy=gx-y,fz=bx-z;
  const a=at(x,y,z)*(1-fx)+at(xx,y,z)*fx,d=at(x,yy,z)*(1-fx)+at(xx,yy,z)*fx;
  const e=at(x,y,zz)*(1-fx)+at(xx,y,zz)*fx,f=at(x,yy,zz)*(1-fx)+at(xx,yy,zz)*fx;
  return ((a*(1-fy)+d*fy)*(1-fz)+(e*(1-fy)+f*fy)*fz);
 };
 const rgb=Buffer.alloc(13**3*3);let at=0;
 for(let b=0;b<13;b++)for(let g=0;g<13;g++)for(let r=0;r<13;r++)for(let c=0;c<3;c++)rgb[at++]=Math.round(sample(r/12,g/12,b/12,c)*255);
 return {name,rgb,sha256:createHash('sha256').update(name+'\0').update(rgb).digest('hex'),sourceSize:size,downsampled:size>13};
}
