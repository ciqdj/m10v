import {renderPreviewPixels} from './film-preview.mjs';
let source;
self.onmessage=async({data})=>{
 try{
  if(data.kind==='source'){source=new Uint8ClampedArray(data.pixels);return;}
  if(!source)throw new Error('原图尚未准备');
  const pixels=await renderPreviewPixels(source,data.look);
  self.postMessage({id:data.id,pixels:pixels.buffer},[pixels.buffer]);
 }catch(error){self.postMessage({id:data.id,error:error.message});}
};
