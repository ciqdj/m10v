import test from 'node:test';import assert from 'node:assert/strict';
import {defaultConfiguration,normalizeConfiguration,migrateSimulationSelection} from '../web/gr3/native-library-state.mjs';
import {initialState,nativeCatalog} from './gr3-native-library.mjs';
test('one catalogue accepts every legacy simulation as a real camera slot',async()=>{
 const c=await nativeCatalog();assert.equal(c.films.length,46);assert.deepEqual(c.films.filter(f=>f.group==='M10V精选').map(f=>f.id),[33,66,67,68,69,70,71,72,73,74,75,76,77,78]);
 assert.equal(c.films.find(f=>f.legacy_id==='ektar100').id,34);
 const cfg=defaultConfiguration();cfg.slots[0].film=34;cfg.slots[1].film=65;
 assert.equal(normalizeConfiguration(cfg).slots[0].film,34);
});
test('four halo controls and grain/soft are packed in each version4 slot',()=>{
 const cfg=defaultConfiguration();cfg.slots[4].halo={gain:8,spread:1,threshold:7,profile:3};
 const normalized=normalizeConfiguration(cfg);const bytes=initialState(normalized);
 assert.equal(bytes.length,104);assert.equal(bytes.readUInt16LE(4),4);
 assert.deepEqual([...bytes.subarray(48,52)],[8,1,7,3]);
 assert.throws(()=>normalizeConfiguration({...cfg,slots:cfg.slots.map((s,i)=>i===4?{...s,halo:{...s.halo,gain:9}}:s)}));
});
test('film name stamp migrates off and packs independently from date',()=>{
 const old=defaultConfiguration();delete old.filmNameStamp;
 assert.equal(normalizeConfiguration(old).filmNameStamp,false);
 const selected=normalizeConfiguration({...old,stamp:0,filmNameStamp:true});
 assert.equal(initialState(selected).readUInt32LE(96),1);
 assert.equal(initialState(selected).readUInt8(52),0);
 assert.equal(selected.slots[0].film,old.slots[0].film);
});

test('legacy simulation draft migrates into the same slots and flags unknown LUTs',async()=>{
 const {films}=await nativeCatalog();const migrated=migrateSimulationSelection(['ektar100','gold200','lut-private','portra400','vision3-250d'],{ektar100:{grain:2,hdf:1}},films);
 assert.equal(migrated.configuration.slots[0].film,34);assert.equal(migrated.configuration.slots[0].grain,2);assert.equal(migrated.configuration.slots[0].soft,0);
 assert.deepEqual(migrated.unresolved,[{slot:2,id:'lut-private'}]);
});
test('both colour views edit a single native configuration and do not restore the legacy film builder',async()=>{
 const {readFile}=await import('node:fs/promises');const app=await readFile(new URL('../web/gr3/studio.js',import.meta.url),'utf8');
 const detail=app.slice(app.indexOf('function renderFilmDetail'),app.indexOf('function openRecipe'));
 assert.ok(detail.includes('state.nativeConfig.slots'));assert.ok(detail.includes('nativeEditor.setFilm'));assert.ok(!detail.includes('state.filmIds'));
 const tab=app.slice(app.indexOf('function showSettingsTab'),app.indexOf("$('tab-imaging').onclick"));
 assert.ok(tab.includes('enterNativeSelection()'));assert.ok(!tab.includes("?'native':'custom'"));
});
