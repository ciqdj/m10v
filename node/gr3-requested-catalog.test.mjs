import test from 'node:test';
import assert from 'node:assert/strict';
import {nativeCatalog} from './gr3-native-library.mjs';
import {buildSdFilmPack,auditSdFilmPack,sdFilmRecord} from './gr3-sd-film-pack.mjs';

// Literal acceptance list supplied by the user, independently of production data.
const groups=[
 ['ECN2',[[33,'800T'],[66,'5207'],[62,'5219'],[78,'5203'],[298,'5213'],[77,'2460']]],
 ['C41',[[69,'Portra 160'],[37,'Portra 400'],[70,'Fuji Industrial 100'],[73,'Fuji C200'],[56,'Fuji Superia 200'],[36,'Fuji Pro 400H'],[35,'Kodak Gold 200'],[58,'Kodak UltraMax 400'],[74,'ProImage 100'],[34,'Ektar 100'],[71,'Lucky C200'],[67,'Harman Phoenix II'],[68,'Harman Red'],[292,'Lomography']]],
 ['D76',[[75,'T-Max 100']]],
 ['创意',[[289,'Kodak Charmera'],[72,'CCD'],[293,'Polaroid'],[296,'Cyanotype'],[290,'Pixel Worlds'],[76,'Aerochrome']]],
 ['影像',[[291,'Leica Monochrome'],[297,'German Cool'],[65,'GR2']]],
];
const rows=groups.flatMap(([group,films])=>films.map(([id,name])=>({id,name,group})));
test('backend exposes exactly the requested thirty identities, names and group order',async()=>{
 const c=await nativeCatalog();
 assert.equal(c.film_count,30);
 assert.deepEqual(c.films.map(({id,name,group})=>({id,name,group})),rows);
 assert.deepEqual(c.films.map(f=>f.number),Array.from({length:30},(_,i)=>i+1));
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
 for(const id of [38,39,57,59,60,61,63,64,294,295])assert.throws(()=>buildSdFilmPack([id]));
});
