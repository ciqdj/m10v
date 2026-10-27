import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultConfiguration,normalizeConfiguration,prepareZoomConfigurationForBuild,zoomSummary} from '../web/gr3/native-library-state.mjs';
test('legacy configurations preserve camera focal slots by default',()=>{
 const legacy=defaultConfiguration();delete legacy.zoom;
 assert.deepEqual(normalizeConfiguration(legacy).zoom,{write:false,slots:[35,50],revision:0});
 const a=defaultConfiguration(),b=defaultConfiguration();a.zoom.slots[0]=41;assert.equal(b.zoom.slots[0],35);
});
test('zoom contract rejects malformed fields even with writing disabled',()=>{
 for(const zoom of [null,{}, {write:1,slots:[35,50],revision:0},{write:false,slots:[35],revision:0},{write:false,slots:[28,100.1],revision:0},{write:false,slots:['35',50],revision:0},{write:false,slots:[27,50],revision:0},{write:false,slots:[35,101],revision:0},{write:false,slots:[35,50],revision:-1},{write:false,slots:[35,50],revision:2**32},{write:false,slots:[35,50],revision:0,extra:1}])assert.throws(()=>normalizeConfiguration({...defaultConfiguration(),zoom}));
 assert.deepEqual(normalizeConfiguration({...defaultConfiguration(),zoom:{write:true,slots:[50,28],revision:0xffffffff}}).zoom.slots,[50,28]);
});
test('each opt-in prepare refreshes nonzero revision and snapshots remain independent',()=>{
 const config=defaultConfiguration();config.zoom.write=true;let seed=0;
 const random={getRandomValues(a){a[0]=++seed;return a;}};
 const first=prepareZoomConfigurationForBuild(config,'gr3',random),second=prepareZoomConfigurationForBuild(first,'gr3',random);
 assert.equal(first.zoom.revision,1);assert.equal(second.zoom.revision,2);assert.equal(config.zoom.revision,0);
 for(const model of ['gr4'])assert.throws(()=>prepareZoomConfigurationForBuild(config,model,random),/GR III/);
 const unchanged=defaultConfiguration();assert.deepEqual(prepareZoomConfigurationForBuild(unchanged,'gr4',null),unchanged);
 assert.match(zoomSummary(first),/35 mm.*50 mm/);assert.match(zoomSummary(unchanged),/保留机内/);
});

test('native preflight binds opt-in focal slots and rejects unsupported models',async()=>{
 const {readNativeOfficial,prepareNative}=await import('./gr3-native-library.mjs');
 const {normalizeGr4Request}=await import('./gr4-m10v-native-build.mjs');
 const source=await readNativeOfficial('gr3'),off=defaultConfiguration();
 const original=prepareNative(source,off);assert.equal(original.zoom_seed,null);
 const on={...off,zoom:{write:true,slots:[40,50],revision:1}};
 const first=prepareNative(source,on);assert.deepEqual(first.zoom_seed.slots,[40,50]);
 assert.notEqual(first.configuration_sha256,original.configuration_sha256);
 const second=prepareNative(source,{...on,zoom:{...on.zoom,revision:2}});
 assert.notEqual(first.zoom_seed.id,second.zoom_seed.id);
 assert.throws(()=>prepareNative(source,on,{film_library:false}),/GR III/);
 assert.throws(()=>normalizeGr4Request({configuration:on}),/GR III/);
 const x=await readNativeOfficial('gr3x');assert.deepEqual(prepareNative(x,on).zoom_seed.slots,[40,50]);
});
