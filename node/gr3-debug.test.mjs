import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {prepareNative,generateNative} from './gr3-native-library.mjs';
import {nativeSourceFingerprint} from './gr3-m10v-native-build.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
const source=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));

test('debug mode is off by default and changes the accepted firmware plan',async()=>{
 const configuration=defaultConfiguration();
 const normal=prepareNative(source,configuration),debug=prepareNative(source,configuration,{debug_mode:true});
 assert.equal(normal.debug_mode,false);
 assert.equal(debug.debug_mode,true);
 assert.equal(debug.runtime_source_sha256,nativeSourceFingerprint());
 assert.match(debug.runtime_source_sha256,/^[0-9a-f]{64}$/);
 assert.notEqual(normal.configuration_sha256,debug.configuration_sha256);
 assert.deepEqual(debug.debug_log.files,['M10VMN0.BIN','M10VMN1.BIN','M10VCP0.BIN','M10VCP1.BIN']);
 assert.throws(()=>prepareNative(source,configuration,{debug_mode:'true'}),/调试/);
 await assert.rejects(()=>generateNative(source,configuration,normal.configuration_sha256,{debug_mode:true}),/变化/);
});
