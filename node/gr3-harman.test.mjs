import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {nativeCatalog,initialState} from './gr3-native-library.mjs';
import {defaultConfiguration,normalizeConfiguration,selectNativeFilm,resetNativeTexture,migrateSimulationSelection} from '../web/gr3/native-library-state.mjs';

test('Harman films append stable IDs and shared 40px icon records',async()=>{
 const c=await nativeCatalog();assert.equal(c.films.length,39);
 for(const [id,name] of [[67,'蓝凤凰'],[68,'哈曼 RED']]){
  const f=c.films.find(f=>f.id===id);assert.equal(f.name,name);assert.equal(f.group,'M10V精选');
  assert.equal(f.camera_calibrated,false);assert.equal(f.film_calibrated,false);
 }
 const icons=JSON.parse(await readFile(new URL('../web/gr3/film-icons/catalog.json',import.meta.url)));
 assert.equal(icons.length,71);assert.equal((await readFile(new URL('../native/gr3/m10v_icons.rgba',import.meta.url))).length,71*40*40*4);
 assert.equal(icons[66].color,'#397ac4');assert.equal(icons[67].color,'#c74435');
});
test('film selection supplies the two stock defaults without changing other slots',()=>{
 for(const [film,grain,grainSize,gain] of [[67,1,0,2],[68,2,1,0]]){
  const old=defaultConfiguration(),c=selectNativeFilm(old,0,film),s=c.slots[0];
  assert.equal(s.film,film);assert.equal(s.grain,grain);assert.equal(s.soft,0);assert.equal(s.effects.grainSize,grainSize);
  assert.equal(s.effects.leakGain,0);assert.equal(s.effects.filmExposure,0);assert.equal(s.halo.gain,gain);
  if(film===67)assert.deepEqual(s.halo,{gain:2,spread:3,threshold:5,profile:2});
  assert.deepEqual(c.slots.slice(1),old.slots.slice(1));assert.equal(old.slots[0].film,34);
 }
});
test('old effects upgrade and RED alone accepts bounded integer simulated EI',()=>{
 const old=defaultConfiguration();delete old.slots[0].effects.filmExposure;
 assert.equal(normalizeConfiguration(old).slots[0].effects.filmExposure,0);
 for(const bad of [-1,3,0.5,'1',null,undefined]){
  const c=selectNativeFilm(old,0,68);c.slots[0].effects.filmExposure=bad;assert.throws(()=>normalizeConfiguration(c));
 }
 for(const film of [33,66,67]){
  const c=selectNativeFilm(old,0,film);c.slots[0].effects.filmExposure=1;assert.throws(()=>normalizeConfiguration(c));
 }
 const c=selectNativeFilm(old,0,68);c.slots[0].effects.filmExposure=2;
 assert.equal(selectNativeFilm(c,0,67).slots[0].effects.filmExposure,0);
 assert.equal(selectNativeFilm(c,0,33).slots[0].effects.filmExposure,0);
});
test('schema4 packs EI in each effects reserved byte and common reset preserves it and halo',()=>{
 let c=selectNativeFilm(defaultConfiguration(),0,68);c=selectNativeFilm(c,1,68);
 c.slots[0].effects.filmExposure=2;c.slots[1].effects.filmExposure=1;
 c.slots[0].effects.leakGain=8;c.slots[0].halo.gain=5;
 const b=initialState(c);assert.equal(b.readUInt16LE(4),4);assert.equal(b.length,104);
 assert.equal(b[61],2);assert.equal(b[69],1);assert.equal(b[57],8);assert.equal(b[62],0);
 const reset=resetNativeTexture(c,0);assert.equal(reset.slots[0].effects.filmExposure,2);
 assert.equal(reset.slots[0].effects.leakGain,0);assert.deepEqual(reset.slots[0].halo,c.slots[0].halo);
});
test('both UI surfaces keep stock controls alongside shared texture',async()=>{
 for(const file of ['native-library.html','native-library-controls.html']){
  const html=await readFile(new URL('../web/gr3/'+file,import.meta.url),'utf8');
  assert.match(html,/39 套/);assert.match(html,/id="effect-filmExposure"/);assert.match(html,/模拟曝光EI/);
  for(const ei of [125,64,250])assert.match(html,new RegExp('EI '+ei));
  assert.match(html,/非机身 ISO|不改变机身 ISO/);assert.match(html,/非 push|不模拟增感冲洗/);
 }
});
test('Harman preview uses the same 15-cube for each RED EI and preserves source alpha',async()=>{
 const {previewHarmanPixels}=await import('../web/gr3/film-preview.mjs');
 const lut=JSON.parse(await readFile(new URL('../web/gr3/harman-luts.json',import.meta.url),'utf8'));
 const source=new Uint8ClampedArray([255,0,0,127,0,255,0,200,0,0,255,255]);
 const original=source.slice();
 for(const [film,exposure,table] of [[67,0,0],[68,0,1],[68,1,2],[68,2,3]]){
  const out=previewHarmanPixels(source,lut,film,exposure),values=lut.stocks[table].values;
  assert.deepEqual([...out.subarray(0,3)],values.slice((14*15*15)*3,(14*15*15)*3+3));
  assert.deepEqual([...out.subarray(4,7)],values.slice((14*15)*3,(14*15)*3+3));
  assert.deepEqual([...out.subarray(8,11)],values.slice(14*3,14*3+3));
  assert.deepEqual([out[3],out[7],out[11]],[127,200,255]);
 }
 assert.deepEqual(source,original);
 assert.notDeepEqual(previewHarmanPixels(source,lut,68,0),previewHarmanPixels(source,lut,68,2));
});
test('Harman tetrahedral preview interpolates all six fractional orderings',async()=>{
 const {previewHarmanPixels}=await import('../web/gr3/film-preview.mjs');
 const size=15,values=Array(size**3*3).fill(0);
 const set=(r,g,b,v)=>{const p=((r*size+g)*size+b)*3;values.splice(p,3,...v);};
 set(0,0,0,[10,20,30]);set(1,0,0,[240,0,0]);set(0,1,0,[0,210,0]);set(0,0,1,[0,0,180]);
 set(1,1,0,[120,90,0]);set(1,0,1,[100,0,70]);set(0,1,1,[0,80,60]);set(1,1,1,[200,180,160]);
 const lut={size,bits:8,stocks:[{values}]};
 // Weights are (45,70,70,70)/255 for each ordering; asymmetric corners
 // distinguish tetrahedral interpolation from trilinear interpolation.
 for(const [rgb,expected] of [
  [[15,10,5],[155,78,49]],[[15,5,10],[150,53,68]],
  [[10,15,5],[90,135,49]],[[5,15,10],[57,133,66]],
  [[10,5,15],[84,53,118]],[[5,10,15],[57,75,115]],
 ])assert.deepEqual([...previewHarmanPixels(new Uint8ClampedArray([...rgb,255]),lut,67,0)].slice(0,3),expected);
});

test('legacy draft migration clears RED EI when replacing a slot with a legacy film',()=>{
 const c=selectNativeFilm(defaultConfiguration(),0,68);c.slots[0].effects.filmExposure=2;
 const migrated=migrateSimulationSelection(['legacy'],{},[{legacy_id:'legacy',id:34}],c);
 assert.equal(migrated.configuration.slots[0].film,34);assert.equal(migrated.configuration.slots[0].effects.filmExposure,0);
});
