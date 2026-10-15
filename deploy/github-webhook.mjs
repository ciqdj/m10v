import http from 'node:http';
import {createHmac,timingSafeEqual} from 'node:crypto';
import {readFileSync,writeFileSync,mkdirSync,renameSync} from 'node:fs';
import {execFile} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

export function verifyDelivery(body,headers,secret){
 const signature=headers['x-hub-signature-256'];
 if(!secret||!/^sha256=[0-9a-f]{64}$/.test(signature||''))return {status:401};
 const expected=createHmac('sha256',secret).update(body).digest();
 if(!timingSafeEqual(expected,Buffer.from(signature.slice(7),'hex')))return {status:401};
 if(headers['x-github-event']==='ping')return {status:200};
 if(headers['x-github-event']!=='push')return {status:202,ignored:true};
 let p;try{p=JSON.parse(body);}catch{return {status:400};}
 if(p.repository?.full_name!=='zhaoo/m10v'||p.ref!=='refs/heads/main'||p.deleted)return {status:202,ignored:true};
 if(!/^[0-9a-f]{40}$/.test(p.after||'')||/^0+$/.test(p.after))return {status:400};
 return {status:202,sha:p.after};
}
export function createReceiver({secret,stateDir,deploy}){
 mkdirSync(stateDir,{recursive:true,mode:0o700});
 const stateFile=path.join(stateDir,'state.json');
 let state={pending:null,running:null,deployed:null,lastResult:null},active=false;
 try{state=JSON.parse(readFileSync(stateFile));if(state.running&&!state.pending)state.pending=state.running;state.running=null;}catch{}
 const save=()=>{writeFileSync(stateFile+'.tmp',JSON.stringify(state,null,2),{mode:0o600});renameSync(stateFile+'.tmp',stateFile);};
 async function drain(){
  if(active)return;active=true;
  try{while(state.pending){const sha=state.pending;state.pending=null;state.running=sha;save();
   try{await deploy(sha);state.deployed=sha;state.lastResult={sha,ok:true,time:new Date().toISOString()};}
   catch(error){state.lastResult={sha,ok:false,error:String(error.message).slice(-1200),time:new Date().toISOString()};}
   state.running=null;save();
  }}finally{active=false;}
 }
 const server=http.createServer(async(req,res)=>{
  const reply=(status,value)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
  if(req.method!=='POST'||req.url!=='/hooks/github')return reply(404,{error:'not found'});
  try{
   const chunks=[];let bytes=0;
   for await(const chunk of req){bytes+=chunk.length;if(bytes>1024*1024)return reply(413,{error:'payload too large'});chunks.push(chunk);}
   const result=verifyDelivery(Buffer.concat(chunks),req.headers,secret);
   if(result.sha&&result.sha!==state.deployed&&result.sha!==state.running){state.pending=result.sha;save();}
   reply(result.status,{accepted:result.status<300,queued:!!result.sha,ignored:!!result.ignored});
   if(result.sha)setImmediate(drain);
  }catch{reply(500,{error:'queue unavailable'});}
 });
 server.requestTimeout=15000;server.headersTimeout=10000;
 server.on('listening',()=>{if(state.pending)setImmediate(drain);});
 return server;
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1])){
 const secret=readFileSync('/etc/m10v-deploy/secret','utf8').trim();
 if(secret.length<32)throw Error('webhook secret must have at least 32 characters');
 const deploy=sha=>new Promise((resolve,reject)=>{
  console.log('DEPLOY_START',sha);
  execFile('bash',['/usr/local/lib/m10v-deploy/update-server.sh','--deploy',sha],{timeout:600000,maxBuffer:2*1024*1024},(error,stdout,stderr)=>{
   console.log(stdout);if(stderr)console.error(stderr);
   if(error){console.error('DEPLOY_FAILED',sha);reject(error);}else{console.log('DEPLOY_FINISHED',sha);resolve();}
  });
 });
 createReceiver({secret,stateDir:'/var/lib/m10v-deploy',deploy}).listen(3001,'127.0.0.1',()=>console.log('WEBHOOK_READY 127.0.0.1:3001'));
}
