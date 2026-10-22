import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultConfiguration,selectNativeFilm,resetNativeTexture,normalizeConfiguration} from '../web/gr3/native-library-state.mjs';
import {initialState} from './gr3-native-library.mjs';
const off=s=>{assert.equal(s.grain,0);assert.equal(s.soft,0);assert.equal(s.halo.gain,0);assert.equal(s.effects.leakGain,0);};
test('fresh defaults and every film selection leave extra effects off',()=>{
 const c=defaultConfiguration();c.slots.forEach(off);
 for(const film of [...Array.from({length:46},(_,i)=>33+i),289]){
  const next=selectNativeFilm(c,0,film);off(next.slots[0]);
  assert.deepEqual(next.slots.slice(1),c.slots.slice(1));
 }
});
test('switching away from a manually enabled effect resets extras, selecting same film preserves them',()=>{
 const c=defaultConfiguration();Object.assign(c.slots[0],{grain:3});c.slots[0].halo.gain=6;c.slots[0].effects.leakGain=7;
 assert.deepEqual(selectNativeFilm(c,0,34),c);
 for(const film of [33,35,66,67,68,69,78,289])off(selectNativeFilm(c,0,film).slots[0]);
 const kept=normalizeConfiguration(c);assert.equal(kept.slots[0].grain,3);assert.equal(kept.slots[0].halo.gain,6);
 const bytes=initialState(c);assert.equal(bytes[14],3);assert.equal(bytes[16],6);assert.equal(bytes[57],7);
 off(resetNativeTexture(c,0).slots[0]);
});
