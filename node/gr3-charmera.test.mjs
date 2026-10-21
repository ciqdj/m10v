import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeCatalog,initialState} from './gr3-native-library.mjs';
import {defaultConfiguration,selectNativeFilm,normalizeConfiguration,resetNativeTexture} from '../web/gr3/native-library-state.mjs';
import {renderPreviewPixels} from '../web/gr3/film-preview.mjs';
import {buildSdFilmPack,auditSdFilmPack,customFilmRecord} from './gr3-sd-film-pack.mjs';
const ID=289;
test('Charmera has an independent identity without stealing existing custom ID 79',async()=>{
 const c=await nativeCatalog();assert.equal(c.films.find(f=>f.id===ID)?.name,'Kodak Charmera');
 assert.deepEqual(c.films.map(f=>f.number),Array.from({length:47},(_,i)=>i+1));assert.equal(c.film_count,47);
 assert.equal(customFilmRecord({name:'Existing',rgb:Buffer.alloc(6591)},79).readUInt32LE(8),79);
 assert.deepEqual(auditSdFilmPack(buildSdFilmPack([33,ID])).ids,[33,ID]);
});
test('four colors persist per slot, texture reset preserves color and switching film clears it',()=>{
 let c=selectNativeFilm(defaultConfiguration(),0,ID);assert.equal(c.slots[0].grain,0);
 for(let color=0;color<4;color++){
 c.slots[0].effects.charmeraColor=color;c=normalizeConfiguration(c);
 assert.equal(initialState(c)[63],color);assert.equal(resetNativeTexture(c,0).slots[0].effects.charmeraColor,color);
 }
 c.slots[0].grain=2;c=selectNativeFilm(c,0,ID);assert.equal(c.slots[0].grain,2);assert.equal(c.slots[0].effects.charmeraColor,3);
 const before=structuredClone(c.slots[1]);c=selectNativeFilm(c,0,33);
 assert.equal(c.slots[0].effects.charmeraColor,undefined);assert.deepEqual(c.slots[1],before);
 c.slots[0].effects.charmeraColor=1;assert.throws(()=>normalizeConfiguration(c));
});
test('Charmera previews threshold independently of source hue, preserve alpha and reject bad color',async()=>{
 const src=new Uint8ClampedArray([0,0,0,7,255,255,255,9,127,127,127,11,128,128,128,13]);
 for(const [color,rgb] of [[0,[253,1,0]],[1,[249,211,78]],[2,[1,0,249]],[3,[224,224,224]]]){
 const out=await renderPreviewPixels(src,{film:ID,effects:{charmeraColor:color}});
 assert.deepEqual([...out.slice(0,4)],[0,0,0,7]);assert.deepEqual([...out.slice(4,8)],[...rgb,9]);
 assert.deepEqual([...out.slice(8,12)],[0,0,0,11]);assert.deepEqual([...out.slice(12,16)],[...rgb,13]);
 }
 await assert.rejects(renderPreviewPixels(src,{film:ID,effects:{charmeraColor:4}}));
});
test('previous custom card identities and canonical reserved bytes survive renderer upgrade',async()=>{
 const {readFileSync}=await import('node:fs');const {sdCrc}=await import('./gr3-sd-film-pack.mjs');
 const prior=JSON.parse(readFileSync(new URL('./gr3-sd-prior-contract.json',import.meta.url)));
 const pack=buildSdFilmPack([],[{name:'Existing',rgb:Buffer.alloc(6591),sha256:'stable'}]),r=pack.subarray(4096);
 Buffer.from(prior.renderer,'hex').copy(r,8448);r.writeUInt32LE(sdCrc(r.subarray(0,-4)),r.length-4);
 pack.writeUInt32LE(r.readUInt32LE(r.length-4),68);pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);
 assert.deepEqual(auditSdFilmPack(pack).ids,[79]);
 r[7000]=1;r.writeUInt32LE(sdCrc(r.subarray(0,-4)),r.length-4);pack.writeUInt32LE(r.readUInt32LE(r.length-4),68);pack.writeUInt32LE(sdCrc(pack.subarray(0,4092)),4092);
 assert.throws(()=>auditSdFilmPack(pack));
});
