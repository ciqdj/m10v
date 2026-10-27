import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {nativeCatalog,prepareNative,readNativeOfficial} from './gr3-native-library.mjs';
import {buildSdFilmPack,auditSdFilmPack,sdFilmRecord} from './gr3-sd-film-pack.mjs';
import {defaultConfiguration,retainCatalogFilms} from '../web/gr3/native-library-state.mjs';

// Literal acceptance list supplied by the user, independently of production data.
const groups=[
 ['ECN2',[[33,'800T'],[66,'5207'],[62,'5219'],[78,'5203'],[298,'5213'],[77,'2460']]],
 ['C41',[[69,'Portra 160'],[37,'Portra 400'],[70,'Fuji Industrial 100'],[73,'Fuji C200'],[56,'Fuji Superia 200'],[36,'Fuji Pro 400H'],[35,'Kodak Gold 200'],[58,'Kodak UltraMax 400'],[74,'ProImage 100'],[34,'Ektar 100'],[71,'Lucky C200'],[67,'Harman Phoenix II'],[68,'Harman Red'],[292,'Lomography']]],
 ['E6',[[294,'Fuji Velvia 50'],[309,'Fuji Provia 100F'],[310,'Kodak Ektachrome E100'],[311,'5294']]],
 ['D76',[[75,'T-Max 100'],[299,'Tri-X 400'],[300,'Ilford Delta 100'],[301,'Ilford Pan 400'],[302,'Rollei Infrared 400'],[303,'Ilford SFX 200'],[304,'Fomapan 400'],[305,'CatLABS X Film 80']]],
 ['创意',[[289,'Kodak Charmera'],[72,'CCD'],[293,'Polaroid'],[296,'Cyanotype'],[290,'Pixel Worlds'],[76,'Aerochrome'],[306,'Makoto Shinkai'],[307,'Ghibli'],[308,'1970s']]],
 ['影像',[[291,'Leica Monochrome'],[297,'German Cool'],[65,'GR2']]],
];
const rows=groups.flatMap(([group,films])=>films.map(([id,name])=>({id,name,group})));
test('backend exposes exactly the requested forty-four identities, names and group order',async()=>{
 const c=await nativeCatalog();
 assert.equal(c.film_count,44);
 assert.deepEqual(c.films.map(({id,name,group})=>({id,name,group})),rows);
 assert.deepEqual(c.films.map(f=>f.number),Array.from({length:44},(_,i)=>i+1));
 assert.ok(c.films.every(f=>f.icon_url));
});
test('default SD export and every record retain the requested names and order',()=>{
 const pack=buildSdFilmPack();assert.deepEqual(auditSdFilmPack(pack).ids,rows.map(f=>f.id));
 for(const {id,name} of rows)assert.equal(sdFilmRecord(id).subarray(16,40).toString('ascii').split('\0')[0],name);
});
test('a shuffled subset follows the requested order instead of old curated or numeric order',()=>{
 assert.deepEqual(auditSdFilmPack(buildSdFilmPack([65,72,37,77,33,75])).ids,[33,77,37,75,72,65]);
});
test('removed films cannot be exported as current selectable films',()=>{
 for(const id of [38,39,57,59,60,61,63,64,295])assert.throws(()=>buildSdFilmPack([id]));
});
test('stale full backend drafts release retired slots while preserving surviving settings',()=>{
 const c=defaultConfiguration();c.slots=Array.from({length:10},(_,i)=>({...c.slots[0],film:38+i}));
 const empty=retainCatalogFilms(c,rows);assert.deepEqual(empty.slots,[]);assert.equal(c.slots.length,10);
 c.slots[3]={...c.slots[3],film:77,grain:2};c.slots[7]={...c.slots[7],film:290};
 const kept=retainCatalogFilms(c,rows);assert.deepEqual(kept.slots.map(s=>s.film),[77,290]);assert.equal(kept.slots[0].grain,2);
});
test('native builds reject retired slots while journal normalization stays compatible',async()=>{
 const c=defaultConfiguration();c.slots[0].film=38;const source=await readNativeOfficial();
 assert.throws(()=>prepareNative(source,c),/已停用/);
});
test('authentic full pre-directory card stays readable without allowing new retired exports',()=>{
 const pack=gunzipSync(readFileSync(new URL('../tests/fixtures/gr3-pre-directory-films.m10.gz',import.meta.url)));
 const old=auditSdFilmPack(pack);assert.equal(old.count,55);assert.ok(old.ids.includes(38)&&old.ids.includes(294));assert.ok(!old.ids.includes(298));
 assert.throws(()=>buildSdFilmPack(old.ids),/当前平台目录/);
});
