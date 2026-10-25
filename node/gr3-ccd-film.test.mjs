import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {nativeCatalog} from './gr3-native-library.mjs';
import {buildSdFilmPack,auditSdFilmPack} from './gr3-sd-film-pack.mjs';
import {defaultConfiguration,selectNativeFilm,resetNativeTexture} from '../web/gr3/native-library-state.mjs';
import {previewCuratedPixels} from '../web/gr3/film-preview.mjs';

test('CCD is a stable curated identity carried by the SD pack',async()=>{
 const catalog=await nativeCatalog(),film=catalog.films.find(f=>f.id===72);
 assert.ok(film,'CCD is missing');assert.equal(film.name,'CCD');
 assert.equal(film.group,'创意');assert.equal(film.camera_calibrated,false);
 assert.deepEqual(auditSdFilmPack(buildSdFilmPack([35,72,33])).ids,[33,35,72]);
});
test('CCD selection and texture reset disable film artifacts without touching other slots',()=>{
 const old=selectNativeFilm(defaultConfiguration(),0,68);
 old.slots[0].effects.filmExposure=2;
 const c=selectNativeFilm(old,0,72),s=c.slots[0];
 assert.equal(s.grain,0);assert.equal(s.soft,0);assert.equal(s.halo.gain,0);
 assert.equal(s.effects.leakGain,0);assert.equal(s.effects.filmExposure,0);
 assert.deepEqual(c.slots.slice(1),old.slots.slice(1));
 assert.deepEqual(resetNativeTexture(c,0).slots[0],s);
});
test('CCD preview preserves neutral endpoints, alpha and monotonic grey ramp',async()=>{
 const lut=JSON.parse(await readFile(new URL('../web/gr3/curated-luts.json',import.meta.url)));
 const input=Uint8ClampedArray.from(Array.from({length:256},(_,i)=>[i,i,i,137]).flat());
 const out=previewCuratedPixels(input,lut,72);
 assert.deepEqual([...out.slice(0,4)],[0,0,0,137]);
 assert.deepEqual([...out.slice(-4)],[255,255,255,137]);
 for(let i=0;i<256;i++){
  assert.equal(out[i*4+3],137);
  assert.ok(Math.max(...out.slice(i*4,i*4+3))-Math.min(...out.slice(i*4,i*4+3))<=1);
  if(i)for(let c=0;c<3;c++)assert.ok(out[i*4+c]>=out[(i-1)*4+c]);
 }
 // The IXUS-inspired interpretation darkens the toe and gently restrains bright tones.
 assert.ok(out[32*4]<32);assert.ok(out[224*4]<224);
});
