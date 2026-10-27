import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {FILM_GROUPS,FILM_DIRECTORY} from './gr3-film-directory.mjs';
import {initialState,nativeCatalog,prepareNative,readNativeOfficial} from './gr3-native-library.mjs';
import {defaultConfiguration,normalizeConfiguration,selectNativeFilm} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack} from './gr3-sd-film-pack.mjs';
import {normalizeGr4Request} from './gr4-m10v-native-build.mjs';

test('E6 follows C41 and seven visible additions preserve stable identities',async()=>{
 const c=await nativeCatalog(),groups=FILM_GROUPS.map(g=>g.name);
 assert.equal(groups[groups.indexOf('C41')+1],'E6');
 assert.deepEqual(FILM_GROUPS.find(g=>g.name==='E6').films.map(f=>[f.id,f.name]),[[294,'Fuji Velvia 50'],[309,'Fuji Provia 100F'],[310,'Kodak Ektachrome E100'],[311,'5294']]);
 assert.equal(c.film_count,44);assert.equal(FILM_DIRECTORY.length,44);
 assert.deepEqual(c.films.filter(f=>f.id>=306&&f.id<=308).map(f=>f.name),['Makoto Shinkai','Ghibli','1970s']);
});
test('anime mode defaults off and only explicit valid per-anime states serialize',()=>{
 for(const film of [306,307,308]){
  const c=defaultConfiguration();c.slots[0].film=film;
  assert.equal(normalizeConfiguration(c).slots[0].effects.animeMode,0);
  for(let animeMode=0;animeMode<=3;animeMode++){
   c.slots[0].effects.animeMode=animeMode;
   const b=initialState(c);assert.equal(b.length,184);assert.equal(b.readUInt16LE(4),5);assert.equal(b[103],animeMode);
  }
  c.slots[0].effects.animeMode=4;assert.throws(()=>normalizeConfiguration(c));
 }
 const c=defaultConfiguration();c.slots[0].effects.animeMode=1;assert.throws(()=>normalizeConfiguration(c));
});
test('new SD package roundtrips and authentic main package still audits',()=>{
 const old=gunzipSync(readFileSync(new URL('../tests/fixtures/gr3-pre-anime-e6-films.m10.gz',import.meta.url)));
 assert.equal(auditSdFilmPack(old).count,37);
 const pack=buildSdFilmPack([294,306,307,308,309,310,311]);
 const result=auditSdFilmPack(pack);assert.equal(result.count,7);
});
test('new looks reject exports without the proven GR III ISP still path',async()=>{
 const source=await readNativeOfficial();const c=defaultConfiguration();c.slots[0].film=306;
 assert.throws(()=>prepareNative(source,c,{live_color:false,debug_mode:false}),/ISP/);
 const p=prepareNative(source,c);assert.equal(p.capture_pipeline,'gr3-native-v8');
 assert.equal(p.stock_detail.anime_mode.default,0);assert.ok(p.stock_detail.ids.includes(30));assert.ok(p.stock_detail.fields.includes('animeMode'));
});
test('all seven looks reject GR IV before any firmware build or CPU fallback',()=>{
 for(const film of [294,306,307,308,309,310,311]){
  const c=defaultConfiguration();c.slots[0].film=film;
  assert.throws(()=>normalizeGr4Request({configuration:c}),/ISP/);
 }
});
