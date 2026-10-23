// Spatial approximation of the JPEG renderer; source data and alpha are retained.
export function previewPixelWorld(source,width,height){
 if(!Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||source.length!==width*height*4)throw new RangeError('像素预览尺寸无效');
 const out=new Uint8ClampedArray(source),step=Math.max(2,Math.ceil(Math.max(width,height)/320)*2);
 const level=v=>Math.min(255,Math.max(0,(Math.trunc(v)+8)&~15));
 for(let top=0;top<height;top+=step)for(let left=0;left<width;left+=step){
  const right=Math.min(width,left+step),bottom=Math.min(height,top+step),w=right-left,h=bottom-top;
  let light=0,cb=0,cr=0;
  for(let j=0;j<2;j++)for(let i=0;i<2;i++){
   const x=left+Math.floor(w*(1+2*i)/4),y=top+Math.floor(h*(1+2*j)/4),at=(y*width+x)*4;
   const r=source[at],g=source[at+1],b=source[at+2];
   light+=(77*r+150*g+29*b+128)>>8;
   cb+=Math.min(255,Math.max(0,128+((-43*r-85*g+128*b+128)>>8)));
   cr+=Math.min(255,Math.max(0,128+((128*r-107*g-21*b+128)>>8)));
  }
  light=level((light+2)>>2);cb=level(128+Math.trunc((((cb+2)>>2)-128)*9/8))-128;cr=level(128+Math.trunc((((cr+2)>>2)-128)*9/8))-128;
  const rgb=[light+1.402*cr,light-0.344136*cb-0.714136*cr,light+1.772*cb];
  for(let y=top;y<bottom;y++)for(let x=left;x<right;x++){const at=(y*width+x)*4;for(let c=0;c<3;c++)out[at+c]=rgb[c];}
 }
 return out;
}
