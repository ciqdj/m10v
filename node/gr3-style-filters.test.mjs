import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {nativeCatalog,initialState} from './gr3-native-library.mjs';
import {defaultConfiguration,selectNativeFilm,resetNativeTexture} from '../web/gr3/native-library-state.mjs';
import {buildSdFilmPack,auditSdFilmPack,customFilmRecord} from './gr3-sd-film-pack.mjs';
const ids=[291,292,293,294,295,296,297];
test('five retained style filters keep their identities and requested group names',async()=>{
 const c=await nativeCatalog();
 assert.deepEqual(c.films.filter(f=>ids.includes(f.id)).map(f=>f.name),['Lomography','Polaroid','Cyanotype','Leica Monochrome','German Cool']);
 for(const id of [291,292,293,296,297]){
  const f=c.films.find(f=>f.id===id);assert.equal(f.group,[291,297].includes(id)?'影像':id===292?'C41':'创意');assert.equal(f.camera_calibrated,false);
  const before=defaultConfiguration(),after=selectNativeFilm(before,0,id);
  assert.equal(after.slots[0].film,id);assert.equal(initialState(after).readUInt16LE(12),id);
  assert.deepEqual(after.slots.slice(1),before.slots.slice(1));
  assert.equal(resetNativeTexture(after,0).slots[0].film,id);
 }
 assert.throws(()=>selectNativeFilm(defaultConfiguration(),0,299));
});
test('SD round trip includes sparse filter IDs and coexists with custom LUT records',()=>{
 const pack=buildSdFilmPack([291,292,293,296,297]);assert.deepEqual(auditSdFilmPack(pack).ids,[292,293,296,291,297]);
 const rgb=Buffer.alloc(6591,128),custom={name:'Own LUT',rgb,sha256:'a'.repeat(64)};
 assert.equal(customFilmRecord(custom,79).readUInt32LE(8),79);
 assert.deepEqual(auditSdFilmPack(buildSdFilmPack([33,291,297],[custom])).ids,[33,291,297,79]);
});
test('filter previews preserve alpha and monochrome/blueprint colour constraints',async()=>{
 const preview=await import('../web/gr3/film-preview.mjs');assert.equal(typeof preview.previewStyleFiltersPixels,'function');
 const lut=JSON.parse(await readFile(new URL('../web/gr3/style-filters-luts.json',import.meta.url)));
 const input=new Uint8ClampedArray([200,50,10,17,20,160,90,180,0,0,0,255,255,255,255,201]);
 for(const id of ids){const out=preview.previewStyleFiltersPixels(input,lut,id);assert.deepEqual([out[3],out[7],out[11],out[15]],[17,180,255,201]);assert.notDeepEqual(out,input);}
 const mono=preview.previewStyleFiltersPixels(input,lut,291);for(let i=0;i<mono.length;i+=4)assert.ok(mono[i]===mono[i+1]&&mono[i+1]===mono[i+2]);
 const blue=preview.previewStyleFiltersPixels(input,lut,296);assert.ok(blue[10]>blue[8]);assert.ok(blue[12]>240&&blue[13]>240&&blue[14]>240);
});

test('fresh journals preserve independent timestamp corner and colour bytes',()=>{
 const c={...defaultConfiguration(),corner:3,color:1};const b=initialState(c);assert.equal(b[54],3);assert.equal(b[55],1);
});
