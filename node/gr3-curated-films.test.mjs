import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {nativeCatalog} from './gr3-native-library.mjs';
import {buildSdFilmPack,auditSdFilmPack} from './gr3-sd-film-pack.mjs';
import {defaultConfiguration,selectNativeFilm,resetNativeTexture} from '../web/gr3/native-library-state.mjs';

test('requested groups retain stock identities',async()=>{
 const c=await nativeCatalog();
 assert.deepEqual(c.films.slice(0,6).map(f=>f.id),[33,66,62,78,298,77]);
 for(const [id,name] of [[69,'Portra 160'],[70,'Fuji Industrial 100'],[71,'Lucky C200']]){
  const f=c.films.find(f=>f.id===id);assert.equal(f.name,name);assert.equal(f.group,'C41');
  assert.equal(f.camera_calibrated,false);assert.equal(f.film_calibrated,false);
 }
 assert.equal(c.films.length,30);
});
test('SD subsets use requested group order',()=>{
 const a=auditSdFilmPack(buildSdFilmPack([35,71,34,70,69,33]));
 assert.deepEqual(a.ids,[33,69,70,35,34,71]);
 assert.deepEqual(auditSdFilmPack(buildSdFilmPack()).ids.slice(0,6),[33,66,62,78,298,77]);
});
test('SD priority partition cannot silently discard malformed identities',()=>{
 for(const ids of [[NaN],[undefined],Array(1),[33,undefined]])assert.throws(()=>buildSdFilmPack(ids));
});
test('new film defaults keep textures off and retain per-film grain size',()=>{
 const old=selectNativeFilm(defaultConfiguration(),0,68);old.slots[0].effects.filmExposure=2;
 for(const [film,grain] of [[69,0],[70,0],[71,0]]){
  const c=selectNativeFilm(old,0,film);assert.equal(c.slots[0].grain,grain);
  assert.equal(c.slots[0].effects.grainSize,0);
  assert.equal(c.slots[0].effects.filmExposure,0);assert.equal(c.slots[0].halo.gain,0);
  assert.deepEqual(c.slots.slice(1),old.slots.slice(1));
  assert.deepEqual(resetNativeTexture(c,0).slots[0],c.slots[0]);
 }
});
test('curated preview uses shipped RGB LUT vertices and preserves alpha',async()=>{
 const {previewCuratedPixels}=await import('../web/gr3/film-preview.mjs');
 const lut=JSON.parse(await readFile(new URL('../web/gr3/curated-luts.json',import.meta.url)));
 const input=new Uint8ClampedArray([255,0,0,117,0,255,0,200,0,0,255,255]);
 for(const film of [69,70,71]){
  const out=previewCuratedPixels(input,lut,film),table=lut.stocks[film-69].values;
  assert.deepEqual([...out.slice(0,3)],table.slice(14*225*3,14*225*3+3));
  assert.deepEqual([...out.slice(4,7)],table.slice(14*15*3,14*15*3+3));
  assert.deepEqual([...out.slice(8,11)],table.slice(14*3,14*3+3));
  assert.deepEqual([out[3],out[7],out[11]],[117,200,255]);
 }
});
