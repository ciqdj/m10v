import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {createStockEdits} from './gr3-stock-presets.mjs';import {applyPatchPlan} from './gr3-patch-plan.mjs';import * as audit from './gr3-stock-audit.mjs';
const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
test('configuration intent is checked independently of the patch writer',()=>{
 const config={negativeGrainMenu:true,stockPresets:[{slot:2,name:'Summer'}]};
 const good=applyPatchPlan(source,source,createStockEdits(source,{negativeGrainMenu:true,presets:config.stockPresets})).candidate;
 assert.equal(audit.auditStockIntent(source,good,config).verified,true);
 const wrongSlot=applyPatchPlan(source,source,createStockEdits(source,{negativeGrainMenu:true,presets:[{slot:3,name:'Summer'}]})).candidate;
 assert.throws(()=>audit.auditStockIntent(source,wrongSlot,config),/名称/);
});
