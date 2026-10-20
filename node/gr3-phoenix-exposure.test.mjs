import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {defaultConfiguration,selectNativeFilm,normalizeConfiguration,resetNativeTexture} from '../web/gr3/native-library-state.mjs';
import {initialState} from './gr3-native-library.mjs';
import {previewHarmanPixels} from '../web/gr3/film-preview.mjs';

test('Phoenix EI120 persists independently per slot and resets on a different stock',()=>{
 let c=selectNativeFilm(defaultConfiguration(),0,67);c=selectNativeFilm(c,1,67);
 c.slots[0].effects.filmExposure=1;
 c=normalizeConfiguration(c);
 const bytes=initialState(c);
 assert.equal(bytes[61],1);assert.equal(bytes[69],0);
 assert.equal(resetNativeTexture(c,0).slots[0].effects.filmExposure,1);
 assert.equal(selectNativeFilm(c,0,67).slots[0].effects.filmExposure,1);
 assert.equal(selectNativeFilm(c,0,68).slots[0].effects.filmExposure,0);
 c.slots[0].effects.filmExposure=2;assert.throws(()=>normalizeConfiguration(c));
});

test('Phoenix EI120 preview raises midtones while preserving black white and source alpha',async()=>{
 const lut=JSON.parse(await readFile(new URL('../web/gr3/harman-luts.json',import.meta.url),'utf8'));
 const input=new Uint8ClampedArray([0,0,0,17,80,80,80,88,255,255,255,199]);
 const base=previewHarmanPixels(input,lut,67,0),low=previewHarmanPixels(input,lut,67,1);
 assert.deepEqual([...low.subarray(0,3)],[0,0,0]);
 assert.ok(low[4]>base[4]+8);
 assert.deepEqual([...low.subarray(8,11)],[...base.subarray(8,11)]);
 assert.deepEqual([low[3],low[7],low[11]],[17,88,199]);
 assert.equal(input[4],80);
 assert.throws(()=>previewHarmanPixels(input,lut,67,2));
});
