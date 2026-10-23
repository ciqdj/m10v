import test from 'node:test';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {existsSync} from 'node:fs';
import {mkdtemp,rm,symlink} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const run=promisify(execFile);
const root=fileURLToPath(new URL('..',import.meta.url));
test('web debug export uses the running Node when the service PATH contains no node',async()=>{
 const compiler=process.env.M10V_LLVM_CLANG||['/opt/homebrew/opt/llvm/bin/clang','/usr/bin/clang'].find(existsSync);
 const script=`
  import assert from 'node:assert/strict';
  import {mkdtemp,rm} from 'node:fs/promises';
  import os from 'node:os';import path from 'node:path';
  import {createHash} from 'node:crypto';
  import {createServer} from './node/server.mjs';
  import {Store} from './node/storage.mjs';
  import {defaultConfiguration} from './web/gr3/native-library-state.mjs';
  const dir=await mkdtemp(path.join(os.tmpdir(),'m10v-no-node-path-'));
  const server=createServer(new Store(dir));await new Promise(r=>server.listen(0,'127.0.0.1',r));
  try {
   const base='http://127.0.0.1:'+server.address().port;
   const {session_token}=await(await fetch(base+'/api/status')).json();
   const post=(url,body)=>fetch(base+url,{method:'POST',headers:{'Content-Type':'application/json','X-M10V-Token':session_token},body:JSON.stringify(body)});
   const imported=await post('/api/gr3/native-library/import-official',{model:'gr3'});
   assert.equal(imported.status,200);const {project_id}=await imported.json();
   const route='/api/projects/'+project_id+'/native-library/';
   const configuration=defaultConfiguration();
   const options={configuration,debug_mode:true,extensions:{aspect:true,level:true,negativeGrain:true}};
   const prepared=await post(route+'prepare',options);assert.equal(prepared.status,200);
   const plan=await prepared.json();
   const built=await post(route+'build',{...options,accepted_configuration_sha256:plan.configuration_sha256});
   if(built.status!==200)throw Error('WEB_BUILD_FAILED '+built.status+' '+await built.text());
   const bytes=Buffer.from(await built.arrayBuffer());
   const receipt=JSON.parse(Buffer.from(built.headers.get('X-M10V-Native-Receipt'),'base64'));
   assert.equal(receipt.candidate_sha256,createHash('sha256').update(bytes).digest('hex'));
   assert.equal(receipt.debug_mode,true);assert.equal(receipt.sd_film_library.supported_films,55);
   assert.equal(receipt.capture_pipeline,'gr3-native-v8');assert.equal(receipt.live_view_base.film_color_preview,true);assert.equal(receipt.experimental_capture.native_color,true);assert.equal(receipt.experimental_capture.native_grain,true);
   assert.equal(receipt.composition.verified,true);assert.equal(receipt.composition.aspect_resource_id,1111);
   console.log('WEB_BUILD_OK bytes='+bytes.length);
  } finally {await new Promise(r=>server.close(r));await rm(dir,{recursive:true,force:true});}
 `;
 // Production has clang on PATH, while its Node service is launched by an
 // absolute executable path. Reproduce that distinction without changing PATH
 // in the test runner or relying on /usr/bin/node being absent on Linux.
 const tools=await mkdtemp(path.join(os.tmpdir(),'m10v-service-path-'));
 try {
  await symlink(compiler,path.join(tools,'clang'));
  const {stdout}=await run(process.execPath,['--input-type=module','-e',script],{
   cwd:root,env:{...process.env,PATH:tools,M10V_NODE:'',M10V_LLVM_CLANG:compiler},
   timeout:180000,maxBuffer:2*1024*1024,
  });
  assert.match(stdout,/WEB_BUILD_OK bytes=/);
 } finally {await rm(tools,{recursive:true,force:true});}
});
