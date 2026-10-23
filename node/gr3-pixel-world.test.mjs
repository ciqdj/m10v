import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeCatalog,initialState} from './gr3-native-library.mjs';
import {defaultConfiguration,selectNativeFilm} from '../web/gr3/native-library-state.mjs';
import {renderPreviewPixels} from '../web/gr3/film-preview.mjs';
import {buildSdFilmPack,auditSdFilmPack} from './gr3-sd-film-pack.mjs';
test('Pixel World can be selected and exported without changing other slots',async()=>{
 const catalog=await nativeCatalog(),film=catalog.films.find(f=>f.id===290);
 assert.equal(film?.name,'方块世界');assert.equal(film.group,'M10V精选');
 const original=defaultConfiguration(),c=selectNativeFilm(original,0,290);
 assert.equal(initialState(c).readUInt16LE(12),290);assert.deepEqual(c.slots.slice(1),original.slots.slice(1));
 assert.equal(c.slots[0].grain,0);assert.deepEqual(auditSdFilmPack(buildSdFilmPack([290,289,33])).ids,[290,289,33]);
});
test('Pixel World preview creates flat square cells, keeps alpha and rejects absent dimensions',async()=>{
 const src=new Uint8ClampedArray(6*3*4);
 for(let y=0;y<3;y++)for(let x=0;x<6;x++){const i=(y*6+x)*4;src.set([x<2?100:x<4?180:240, x<2?100:x<4?180:240,x<2?100:x<4?180:240,i%255],i);}
 const before=src.slice(),out=await renderPreviewPixels(src,{film:290},6,3);
 assert.deepEqual([...out.slice(0,3)],[96,96,96]);assert.deepEqual([...out.slice(8,11)],[176,176,176]);
 for(let y=0;y<3;y++)for(let x=0;x<6;x++){const i=(y*6+x)*4;assert.equal(out[i+3],src[i+3]);assert.equal(out[i],out[(y*6+(x&~1))*4]);}
 assert.deepEqual(src,before);
 await assert.rejects(renderPreviewPixels(src,{film:290}));
 await assert.rejects(renderPreviewPixels(src,{film:290},5,3));
});
