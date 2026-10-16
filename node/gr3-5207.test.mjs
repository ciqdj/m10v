import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeCatalog,initialState} from './gr3-native-library.mjs';
import {defaultConfiguration,normalizeConfiguration} from '../web/gr3/native-library-state.mjs';
test('5207 has its own curated ID while legacy 5207 stays intact',async()=>{
 const c=await nativeCatalog();assert.equal(c.films.find(f=>f.id===66)?.name,'5207');
 assert.equal(c.films.find(f=>f.id===66)?.group,'M10V精选');assert.equal(c.films.find(f=>f.id===64)?.name,'V3 5207');
});
test('old web configuration migrates into v3 and validates effect ranges',()=>{
 const old=defaultConfiguration();old.slots[0].film=66;
 const c=normalizeConfiguration(old);assert.deepEqual(c.slots[0].effects,{grainSize:1,leakGain:0,leakPosition:0,leakSpread:4,leakVariation:0});
 const bytes=initialState(c);assert.equal(bytes.readUInt16LE(4),3);assert.equal(bytes.length,104);
 c.slots[0].effects.leakGain=9;assert.throws(()=>normalizeConfiguration(c));
});

test('all films pack shared texture and resetting it preserves film and special controls',async()=>{
 const {resetNativeTexture}=await import('../web/gr3/native-library-state.mjs');
 for(let film=1;film<=66;film++){
  const c=defaultConfiguration();Object.assign(c.slots[0],{film,grain:3,soft:2});
  c.slots[0].effects={grainSize:2,leakGain:8,leakPosition:5,leakSpread:8,leakVariation:1};
  const bytes=initialState(c);assert.deepEqual([...bytes.subarray(56,61)],[2,8,5,8,1]);
  const reset=resetNativeTexture(c,0);assert.equal(reset.slots[0].film,film);
  assert.deepEqual(reset.slots[0].halo,c.slots[0].halo);assert.equal(reset.slots[0].effects.leakGain,0);
  assert.equal(c.slots[0].effects.leakGain,8);assert.deepEqual(reset.slots.slice(1),c.slots.slice(1));
 }
});
