import test from 'node:test';
import assert from 'node:assert/strict';
import {readNativeOfficial,prepareNative} from './gr3-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
test('local preview candidate binds a distinct pipeline and rejects unsupported combinations',async()=>{
 const source=await readNativeOfficial('gr3'),value=defaultConfiguration();
 const normal=prepareNative(source,value,{debug_mode:true,live_color:false});
 const live=prepareNative(source,value,{debug_mode:true,live_color:true});
 assert.equal(live.capture_pipeline,'gr3-native-v8');assert.equal(live.live_color,true);
 assert.notEqual(normal.configuration_sha256,live.configuration_sha256);
 assert.equal(normal.capture_pipeline,'gr3-native-v7');
 assert.equal(prepareNative(source,value).capture_pipeline,'gr3-native-v8');
 assert.equal(prepareNative(source,value).debug_mode,false);
 const combined=prepareNative(source,{...value,hdf:1},{debug_mode:true,live_color:true});
 assert.equal(combined.capture_pipeline,'gr3-native-v8');assert.equal(combined.hdf_enabled,true);
 assert.notEqual(combined.configuration_sha256,live.configuration_sha256);
 const x=await readNativeOfficial('gr3x');assert.throws(()=>prepareNative(x,value,{debug_mode:true,live_color:true}),/原生色调预览/);
});
