import {previewFilmPixels} from './film-preview.mjs';
let sourcePromise;
function loadSource(){
 sourcePromise??=new Promise((resolve,reject)=>{
  const image=new Image();image.onload=()=>{const canvas=document.createElement('canvas');canvas.width=620;canvas.height=413;
   const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(image,0,0,620,413);
   resolve(context.getImageData(0,0,620,413));};image.onerror=()=>{sourcePromise=null;reject(new Error('样张载入失败'));};
  image.src='/gr3/film-street-source.png';
 });return sourcePromise;
}
export function createFilmPreview(){
 let worker=null,source=null,latest=0,pending=null,tick=0,destroyed=false,inFlight=0;
 try{worker=new Worker(new URL('./preview-worker.mjs',import.meta.url),{type:'module'});}catch{}
 function dispatch(){
  if(destroyed||!pending||!source||inFlight)return;
  cancelAnimationFrame(tick);
  tick=requestAnimationFrame(()=>{
   if(destroyed||!pending?.canvas.isConnected)return;
   const {canvas,look}=pending,id=latest;
   if(worker){inFlight=id;worker.postMessage({kind:'render',id,look});}
   else canvas.getContext('2d').putImageData(new ImageData(previewFilmPixels(source.data,look),620,413),0,0);
  });
 }
 if(worker){
  worker.onmessage=({data})=>{
   if(destroyed)return;
   inFlight=0;
   if(data.id===latest&&pending?.canvas.isConnected){
    if(data.error)pending.onError?.(data.error);
    else pending.canvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(data.pixels),620,413),0,0);
   }
   if(data.id!==latest)dispatch();
  };
  worker.onerror=()=>{worker?.terminate();worker=null;inFlight=0;dispatch();};
 }
 return {async request(canvas,look,onError){
  const id=++latest;pending={canvas,look,onError};
  try{source??=await loadSource();if(destroyed||id!==latest)return;
   if(worker&&!worker.sourceSent){worker.postMessage({kind:'source',pixels:source.data.buffer.slice(0)});worker.sourceSent=true;}
   dispatch();
  }catch(error){if(id===latest)onError?.(error.message);}
 },destroy(){destroyed=true;cancelAnimationFrame(tick);worker?.terminate();}};
}
