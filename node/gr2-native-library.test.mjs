import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {prepareGr2Native,generateGr2Native} from './gr2-native-library.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
const source=()=>readFile(new URL('../bin/rg2_v003.frm',import.meta.url));
test('GR2 plan binds configuration and rejects unsupported initial HDF',async()=>{
 const b=await source(),c=defaultConfiguration(),a=await prepareGr2Native(b,c);c.slots[0].grain=2;
 assert.notEqual((await prepareGr2Native(b,c)).configuration_sha256,a.configuration_sha256);
 await assert.rejects(generateGr2Native(b,c,a.configuration_sha256),/重新预检/);
 c.hdf=1;await assert.rejects(prepareGr2Native(b,c),/相机 HDF/);
 const abort=new AbortController();abort.abort();await assert.rejects(generateGr2Native(b,c,'',{signal:abort.signal}),{name:'AbortError'});
});
test('GR2 actual native build reconstructs and packages exact candidate',async()=>{
 const b=await source(),c=defaultConfiguration(),plan=await prepareGr2Native(b,c),result=await generateGr2Native(b,c,plan.configuration_sha256);
 assert.equal(result.receipt.verified,true);assert.equal(result.receipt.independent_component_reconstruction,true);
 assert.equal(result.receipt.hardware_verified,false);assert.equal(result.receipt.release_ready,false);
 assert.equal(result.runtime.can_package,false);assert.equal(result.audit.activation_ready,false);
});
