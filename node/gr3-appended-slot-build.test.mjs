import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareNative,readNativeOfficial} from './gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';

test('GR III preflight preserves factory choices and binds the new slot layout to approval',async()=>{
 const source=await readNativeOfficial(),configuration=defaultConfiguration();
 const plan=prepareNative(source,configuration);
 assert.deepEqual(plan.slot_tone_ids,[25,26,27,28,29]);
 assert.equal(plan.appended_slots,true);
 const legacy=prepareNative(source,configuration,{appended_slots:false});
 assert.deepEqual(legacy.slot_tone_ids,[12,18,19,20,21]);
 assert.notEqual(plan.configuration_sha256,legacy.configuration_sha256);
 assert.deepEqual(plan.configuration.slots,legacy.configuration.slots);
 assert.throws(()=>prepareNative(source,configuration,{appended_slots:1}),/布尔/);
});

test('IIIx shares the appended layout while standalone HDF preserves stock menus',async()=>{
 const configuration=defaultConfiguration();
 const x=await readNativeOfficial('gr3x');
 assert.equal(prepareNative(x,configuration).appended_slots,true);
 assert.equal(prepareNative(x,configuration,{appended_slots:true}).appended_slots,true);
 const source=await readNativeOfficial();
 assert.equal(prepareNative(source,configuration,{film_library:false}).appended_slots,false);
 assert.throws(()=>prepareNative(source,configuration,{film_library:false,appended_slots:true}),/胶卷/);
});
