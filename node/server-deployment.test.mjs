import http from 'node:http';
import test from 'node:test';import assert from 'node:assert/strict';import {createServer} from './server.mjs';
function rawFetch(url,options={}){return new Promise((resolve,reject)=>{const req=http.request(url,{method:options.method||'GET',headers:{...options.headers,...(options.body?{'Content-Length':Buffer.byteLength(options.body)}:{})}},res=>{const chunks=[];res.on('data',v=>chunks.push(v));res.on('end',()=>resolve({status:res.statusCode,json:async()=>JSON.parse(Buffer.concat(chunks))}));});req.on('error',reject);req.end(options.body);});}
test('explicit public origin permits the proxy Host but rejects foreign hosts and browser origins',async()=>{
 const origin='https://m10v.izhaoo.com',server=createServer(undefined,undefined,undefined,{publicOrigin:origin});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{
  const headers={Host:'m10v.izhaoo.com'},status=await rawFetch(base+'/api/status',{headers});assert.equal(status.status,200);const token=(await status.json()).session_token;
  assert.equal((await rawFetch(base+'/',{headers:{Host:'evil.example'}})).status,403);
  const endpoint=base+'/api/gr3/film-bay/pack',body=JSON.stringify({films:['a']});
  const requestHeaders={...headers,'X-M10V-Token':token,'Content-Type':'application/json',Origin:origin};
  assert.equal((await rawFetch(endpoint,{method:'POST',headers:requestHeaders,body})).status,410); // retired endpoint reached, not rejected by origin middleware
  assert.equal((await rawFetch(endpoint,{method:'POST',headers:{...requestHeaders,Origin:'https://evil.example'},body})).status,403);
  assert.equal((await rawFetch(endpoint,{method:'POST',headers:{...requestHeaders,'X-M10V-Token':'wrong'},body})).status,403);
  assert.equal((await rawFetch(base+'/')).status,200); // loopback health probe
 }finally{await new Promise(r=>server.close(r));}
});
test('public origin cannot contain credentials, arbitrary paths or URL payloads',()=>{
 for(const publicOrigin of ['ftp://example.com','https://user:pass@example.com','https://example.com/path','https://example.com?x=1','https://example.com#x'])assert.throws(()=>createServer(undefined,undefined,undefined,{publicOrigin}));
});
test('CLI rejects invalid configured ports instead of silently picking a random port',async()=>{
 const {spawnSync}=await import('node:child_process');
 for(const M10V_PORT of ['0','abc','65536']){
  const result=spawnSync(process.execPath,['node/server.mjs'],{cwd:new URL('..',import.meta.url).pathname,env:{...process.env,M10V_PORT,M10V_NO_BROWSER:'1'},encoding:'utf8',timeout:5000});
  assert.notEqual(result.status,0);assert.match(result.stderr,/M10V_PORT must/);
 }
});
