import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {renderNavigation} from '../web/shared/navigation.js';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('power images have an independent step between settings and save',()=>{
 const html=read('web/gr3/index.html');
 assert.match(html,/data-step="power"/);
 const power=html.slice(html.indexOf('data-page="power"'),html.indexOf('data-page="source"'));
 assert.match(power,/id="power-images"/);
 assert.match(power,/id="power-next"/);
 assert.match(read('web/gr3/studio.js'),/showStep\('power'\)/);
});
test('all models remain reachable inside one model menu with progress labels',()=>{
 for(const path of ['/','/gr3/','/gr4/','/gr2/']){
  const html=renderNavigation(path);
  assert.match(html,/<details class="model-menu"/);
  assert.match(html,/GR IV.*进行中/);
  assert.match(html,/GR II.*进行中/);
  for(const model of ['gr3','gr4','gr2'])assert.match(html,new RegExp(`href="/${model}/"`));
 }
});
