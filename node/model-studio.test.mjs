import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

test('model desk keeps navigation and save availability tied to verified input',async()=>{
 const {deskState}=await import('../web/shared/model-studio.js');
 for(const model of ['gr2','gr4']){
  assert.equal(deskState(model,false,'features').page,'source');
  assert.equal(deskState(model,false,'build').canSave,false);
  assert.equal(deskState(model,true,'features').page,'features');
 }
 assert.equal(deskState('gr2',true,'build').canSave,false);
 assert.equal(deskState('gr4',true,'build').canSave,true);
 assert.equal(deskState('gr4',true,'invalid').page,'source');
});
test('both additional models share GR III styles and the same desk entry',async()=>{
 for(const model of ['gr2','gr4']){
  const html=await readFile(new URL(`../web/${model}/index.html`,import.meta.url),'utf8');
  assert.match(html,/href="\/gr3\/styles.css"/);
  assert.match(html,/src="\/shared\/model-studio.js"/);
  assert.match(html,new RegExp(`data-studio-model="${model}"`));
 }
});
