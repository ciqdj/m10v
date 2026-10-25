import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {defaultConfiguration,normalizeConfiguration,selectNativeFilm} from '../web/gr3/native-library-state.mjs';
import {initialState,prepareNative,readNativeOfficial} from './gr3-native-library.mjs';
import {normalizeGr4Request} from './gr4-m10v-native-build.mjs';
test('legacy retired effects migrate to neutral without losing other slot settings',()=>{
 const c=selectNativeFilm(defaultConfiguration(),0,67);c.slots[0].grain=3;c.slots[0].halo.gain=6;c.slots[0].effects={grainSize:2,leakGain:8,leakPosition:5,leakSpread:8,leakVariation:1,filmExposure:1};c.stamp=2;
 const clean=normalizeConfiguration(c);
 assert.deepEqual(clean.slots[0].effects,{grainSize:0,leakGain:0,leakPosition:0,leakSpread:4,leakVariation:0,filmExposure:1});
 assert.equal(clean.slots[0].grain,3);assert.equal(clean.slots[0].halo.gain,6);assert.equal(clean.stamp,2);assert.deepEqual(clean.slots.slice(1),c.slots.slice(1));
 const state=initialState(c);assert.equal(state.length,104);assert.deepEqual([...state.subarray(56,62)],[0,0,0,4,0,1]);
});
test('nonzero grain exports require the supported GR III native graph',async()=>{
 const c=defaultConfiguration();c.slots[0].grain=1;const gr3=await readNativeOfficial('gr3'),x=await readNativeOfficial('gr3x');
 assert.equal(prepareNative(gr3,c).capture_pipeline,'gr3-native-v8');
 assert.throws(()=>prepareNative(x,c),/颗粒.*GR III/);
 assert.throws(()=>prepareNative(gr3,c,{live_color:false}),/颗粒.*GR III/);
 assert.throws(()=>prepareNative(gr3,{...c,hdf:1},{live_color:false}),/颗粒.*GR III/);
 assert.throws(()=>normalizeGr4Request({configuration:c}),/颗粒.*GR III/);
 for(const film of [289,290]){const special=selectNativeFilm(c,0,film);special.slots[0].grain=1;assert.throws(()=>prepareNative(gr3,special),/颗粒/);}
 assert.ok(!prepareNative(x,defaultConfiguration()).features.includes('grain'));
});
test('web controls remove retired effect widgets and promises',()=>{
 for(const file of ['native-library.html','native-library-controls.html']){
  const html=readFileSync(new URL('../web/gr3/'+file,import.meta.url),'utf8');
  assert.doesNotMatch(html,/effect-(?:grainSize|leak)|漏光|颗粒尺寸/);assert.match(html,/原厂.*颗粒/);
 }
});
