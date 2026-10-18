// Exercise the production GR IV compiler/linker, package, and fresh readback as www.
import assert from 'node:assert/strict';
import {readModelOfficial} from '../node/model-firmware.mjs';
import {prepareGr4Native,generateGr4Native} from '../node/gr4-m10v-native-build.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
const source=await readModelOfficial('gr4');
const input={configuration:defaultConfiguration(),debug_mode:true,
 extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'off'}}};
const plan=await prepareGr4Native(source,input);
const {candidate,receipt}=await generateGr4Native(source,{...input,accepted_configuration_sha256:plan.configuration_sha256});
assert.equal(receipt.model,'GR IV');
assert.equal(receipt.filename,'fwdc248b.bin');
assert.equal(receipt.candidate_bytes,candidate.length);
assert.equal(receipt.camera_tested,false);
console.log(JSON.stringify({model:'GR IV',candidate_sha256:receipt.candidate_sha256,
 candidate_bytes:candidate.length,filename:receipt.filename,camera_tested:false}));
