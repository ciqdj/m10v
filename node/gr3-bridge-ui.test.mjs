import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import {normalizeVersionUnlock} from '../web/gr3/version-unlock-state.mjs';
const studio=await readFile(new URL('../web/gr3/studio.js',import.meta.url),'utf8');
const independent=await readFile(new URL('../web/gr3/native-library.js',import.meta.url),'utf8');
function controls(source,model,standalone=false){
 const map=new Map(),$=id=>{if(!map.has(id))map.set(id,{checked:true,value:model==='gr3x'?'1.60.11.18':'2.10.21.40',disabled:false,hidden:false,textContent:''});return map.get(id);};
 $(standalone?'#native-version-known':'version-known').checked=false;
 const context=vm.createContext({$,state:{profile:'native'},normalizeVersionUnlock});
 const declarations=standalone?`let sourceModel='${model}',busy=false;`:`let chosenModel='${model}',saving=false,activeBuildController=null,bridgeBusy=false;`;
 const end=standalone?'function segment(':'function renderLedger()';
 vm.runInContext(declarations+source.slice(source.indexOf('function versionUnlockSnapshot()'),source.indexOf(end)),context);
 return {context,$};
}
test('GR III studio and standalone exporter ignore retired adaptation and guide users to bridge',()=>{
 for(const [source,standalone] of [[studio,false],[independent,true]]){
  const h=controls(source,'gr3',standalone);assert.equal(h.context.renderVersionUnlock(),true);
  assert.deepEqual(JSON.parse(JSON.stringify(h.context.versionUnlockSnapshot())),{enabled:false});
  assert.equal(h.$(standalone?'#native-version-unlock-option':'version-unlock-option').hidden,true);
 }
});
test('GR IIIx keeps its separate opt-in adaptation and never gains a GR III bridge',()=>{
 const h=controls(studio,'gr3x');assert.equal(h.context.renderVersionUnlock(),true);
 assert.equal(h.$('bridge-option').hidden,true);assert.equal(h.$('version-unlock-option').hidden,false);
 assert.equal(h.context.versionUnlockSnapshot().mode,'dsp-package-only');
});
test('formal bridge entry and guidance name user hardware feedback and retain both stages',async()=>{
 const html=await readFile(new URL('../web/gr3/index.html',import.meta.url),'utf8');
 const bridge=html.slice(html.indexOf('<section id="bridge-option"'),html.indexOf('<section class="version-unlock-option" id="version-unlock-option"'));
 assert.match(bridge,/用户实机反馈通过/);assert.match(bridge,/下载两阶段桥接套件/);
 assert.doesNotMatch(bridge,/实机测试|尚未实机验证|测试包/);
 const dialog=html.slice(html.indexOf('<dialog id="bridge-dialog"'),html.indexOf('<dialog id="firmware-disclaimer"'));
 assert.match(dialog,/stage-1-bridge/);assert.match(dialog,/stage-2-official/);assert.match(dialog,/用户实机反馈通过/);assert.doesNotMatch(dialog,/实机未验证/);
 for(const file of ['native-library.html','native-library-controls.html'])assert.match(await readFile(new URL('../web/gr3/'+file,import.meta.url),'utf8'),/href="\/gr3\/#bridge"/);
});

test('source guidance clears once the official project is imported without erasing export status',()=>{
 const h=controls(studio,'gr3');h.context.renderVersionUnlock();assert.match(h.$('bridge-result').textContent,/请先/);
 h.context.state.projectId='official';h.context.renderVersionUnlock();assert.doesNotMatch(h.$('bridge-result').textContent,/请先/);
 h.$('bridge-result').textContent='两阶段桥接套件已生成并发起下载。';h.context.renderVersionUnlock();assert.match(h.$('bridge-result').textContent,/已生成/);
});
