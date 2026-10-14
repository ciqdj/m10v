import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
const gr4=await readFile(new URL('../web/gr4/app.js',import.meta.url),'utf8');
const localHandler=gr4.slice(gr4.indexOf('$("import-official").onclick'),gr4.indexOf('$("firmware-file").onchange'));
test('GR IV local import saves current edits before replacing the active project',async()=>{
  const button={},events=[],context=vm.createContext({$:()=>button,
    operation:(_label,action)=>action(),saveDraft:async()=>events.push('save'),
    request:async()=>{events.push('import');return {};},acceptProject:()=>events.push('accept')});
  vm.runInContext(localHandler,context);await button.onclick();
  assert.deepEqual(events,['save','import','accept']);
});
test('GR IV local import does not replace a project when pending crop changes cannot be saved',async()=>{
  const button={},events=[],context=vm.createContext({$:()=>button,
    operation:(_label,action)=>action(),saveDraft:async()=>{throw new Error('unconfirmed crop');},
    request:async()=>events.push('import'),acceptProject:()=>events.push('accept')});
  vm.runInContext(localHandler,context);
  await assert.rejects(button.onclick(),/unconfirmed crop/);assert.deepEqual(events,[]);
});
test('a rejected GR II upload cannot leave a previous successful proof visible',async()=>{
  const app=await readFile(new URL('../web/gr2/inspect.js',import.meta.url),'utf8'),nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{hidden:true,disabled:false,textContent:'',files:[],append(){},replaceChildren(){},addEventListener(){}});return nodes.get(id);};
  const context=vm.createContext({document:{getElementById:node,createElement:()=>node('generated')},
    fetch:async url=>({ok:url.endsWith('inspect-official')||url.endsWith('status'),json:async()=>url.endsWith('status')?{session_token:'token'}:
      url.endsWith('inspect-official')?{model:'GR II',public_version:'3.00',sha256:'a'.repeat(64),proof:{byte_exact_roundtrip:true},components:[],resources:[]}:{error:'unsupported firmware identity'}})});
  vm.runInContext(app,context);await context.inspect(true);assert.equal(node('report').hidden,false);
  node('firmware').files=[{arrayBuffer:async()=>new ArrayBuffer(4)}];await context.inspect();
  assert.equal(node('report').hidden,true);assert.equal(node('notice').textContent,'unsupported firmware identity');
});
