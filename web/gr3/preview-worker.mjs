import {renderPreviewPixels} from './film-preview.mjs';
let source,width,height;
self.onmessage=async({data})=>{
 try{
  if(data.kind==='source'){source=new Uint8ClampedArray(data.pixels);width=data.width;height=data.height;return;}
  if(!source)throw new Error('原图尚未准备');
  const pixels=await renderPreviewPixels(source,data.look,width,height);
  self.postMessage({id:data.id,pixels:pixels.buffer},[pixels.buffer]);
 }catch(error){self.postMessage({id:data.id,error:error.message});}
};
