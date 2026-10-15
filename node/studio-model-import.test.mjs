import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {nativeSelection} from '../web/gr3/native-library-state.mjs';
const app=await readFile(new URL('../web/gr3/studio.js',import.meta.url),'utf8');
const method=app.slice(app.indexOf('async function importSource('),app.indexOf('async function download('));
function harness(){
 const nodes=new Map(),node=id=>{if(!nodes.has(id))nodes.set(id,{value:'gr3',hidden:true,disabled:true,textContent:'',append(){},replaceChildren(){}});return nodes.get(id);};
 const state={profile:'native',features:new Set(['film']),nativeConfig:{slots:[{film:33}]},projectId:'',source:null};
 let imported;const calls=[],messages=[];
 const context=vm.createContext({nativeSelection,nativeEditor:{setConfiguration(c){state.nativeConfig=c;}},state,$:node,document:{title:'',querySelector:()=>node('hero')},notice:(...v)=>messages.push(v),invalidate(){},renderFeatures(){},showStep(){},showSettingsTab(){},textNode:()=>node('text'),
 api:async(path,options={})=>{calls.push({path,options});return {json:async()=>path.endsWith('import-official')?{project_id:imported.sha256}:path.endsWith('stock-presets')?[]:imported};}});
 vm.runInContext("let chosenModel='gr3';let modelLabel='GR III';"+app.slice(app.indexOf('function enterNativeSelection()'),app.indexOf('function renderFeatures()'))+method,context);
 const report=(model,sha)=>({model,sha256:sha.repeat(64),public_version:model==='GR IIIx'?'1.60':'2.10',internal_version:'test',size:100,sections:[{}]});
 return {state,nodes,node,calls,messages,report,context,run:async(r,local=false)=>{imported=r;await context.importSource(local?null:{},local);}};
}
test('the same import handler accepts both models and updates target labels from official identity',async()=>{
 const h=harness();await h.run(h.report('GR IIIx','a'));
 assert.equal(h.state.source.model,'GR IIIx');assert.equal(vm.runInContext('chosenModel',h.context),'gr3x');assert.equal(h.node('build-model').textContent,'GR IIIx · 1.60');
 const config=h.state.nativeConfig;await h.run(h.report('GR III','b'));
 assert.equal(h.state.source.model,'GR III');assert.equal(vm.runInContext('chosenModel',h.context),'gr3');assert.equal(h.node('build-model').textContent,'GR III · 2.10');assert.equal(h.state.nativeConfig,config);
});
test('local sample selection does not override the loaded target until import completes',async()=>{
 const h=harness();await h.run(h.report('GR IIIx','a'));h.node('local-source-model').value='gr3';
 assert.equal(vm.runInContext('chosenModel',h.context),'gr3x');await h.run(h.report('GR III','b'),true);
 const call=h.calls.find(c=>c.path.endsWith('import-official'));assert.equal(JSON.parse(call.options.body).model,'gr3');assert.equal(h.state.source.model,'GR III');
});
test('unsupported identity leaves the previous verified source and configuration intact',async()=>{
 const h=harness();await h.run(h.report('GR III','a'));const previous=h.state.source;await h.run(h.report('GR IV','b'));
 assert.equal(h.state.source,previous);assert.equal(vm.runInContext('chosenModel',h.context),'gr3');assert.match(h.messages.at(-1)[0],/仅支持/);
});
