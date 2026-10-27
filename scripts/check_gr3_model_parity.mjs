// Build both product-equivalent candidates through the public native pipeline.
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
import {readNativeOfficial,prepareNative,generateNative} from '../node/gr3-native-library.mjs';
import {defaultConfiguration,normalizeConfiguration} from '../web/gr3/native-library-state.mjs';
import {decodeFrameMap} from '../node/gr3-frames.mjs';
import {buildSdFilmPack,auditSdFilmPack} from '../node/gr3-sd-film-pack.mjs';
const out=path.resolve(process.argv[2]||'builds/gr3-gr3x-parity');
const options={debug_mode:true,hdf_enabled:true,halation_enabled:true,extensions:{aspect:true,level:true,negativeGrain:true,rawNr:{mode:'stock'}}};
const films=[33,66,67,68,294,306,307,308,310,311],plans=[];
const pack=buildSdFilmPack();assert.equal(auditSdFilmPack(pack).count,44);
for(const model of ['gr3','gr3x']){
 const c=defaultConfiguration(model),template=c.slots[0];
 c.slots=films.map(film=>({...structuredClone(template),film}));
 c.slots[1].grain=1;c.zoom.write=true;c.zoom.revision=1;
 const configuration=normalizeConfiguration(c),source=await readNativeOfficial(model);
 const plan=prepareNative(source,configuration,options),r=await generateNative(source,configuration,plan.configuration_sha256,options);
 assert.equal(r.receipt.capture_pipeline,'gr3-native-v8');assert.equal(r.receipt.live_color,true);
 assert.equal(r.manifest.zoom.camera_model,model);assert.equal(r.manifest.zoom.lens_base_mm,model==='gr3x'?40:28);
 assert.equal(r.receipt.active_slots,10);assert.equal(r.manifest.hdf_enabled,true);assert.equal(r.manifest.universal_halation,true);
 if(model==='gr3x'){assert.equal(r.receipt.gr3x_port.model_words.length,19);assert.equal(r.receipt.gr3x_port.checks.cpu_payload_unchanged,true);}
 const folder=path.join(out,model);await mkdir(path.join(folder,'SD/M10V'),{recursive:true});
 const decoded=decodeFrameMap(r.candidate).decoded;
 await Promise.all([
  writeFile(path.join(folder,plan.filename),r.candidate),writeFile(path.join(folder,'M10V-build-receipt.json'),JSON.stringify(r.receipt,null,2)+'\n'),
  writeFile(path.join(folder,'M10V-runtime-manifest.json'),JSON.stringify(r.manifest,null,2)+'\n'),writeFile(path.join(folder,'M10V-runtime-arm.bin'),r.runtime),
  writeFile(path.join(folder,'M10V-configuration.json'),JSON.stringify(plan.configuration,null,2)+'\n'),writeFile(path.join(folder,'M10V-build-options.json'),JSON.stringify(options,null,2)+'\n'),
  writeFile(path.join(folder,'final-rtos.bin'),decoded.subarray(0x10870,0x10870+decoded.readUInt32LE(0x1086c))),writeFile(path.join(folder,'SD/M10V/FILMS.M10'),pack)
 ]);
 plans.push(plan);
 console.log(JSON.stringify({model,folder,sha256:r.receipt.candidate_sha256,bytes:r.candidate.length,build_id:r.receipt.debug_log.build_id,rtos_growth:r.receipt.rtos_growth,camera_tested:false}));
}
for(const key of ['features','stock_detail','slot_tone_ids','capture_pipeline','live_color','hdf_enabled','halation_enabled','initial_state_hex'])assert.deepEqual(plans[0][key],plans[1][key],key+' parity');
console.log('GR3_GR3X_OFFLINE_PARITY_OK');
