import test from 'node:test';
import assert from 'node:assert/strict';
import { normalize800T, create800TFilm } from './gr3-800t-plan.mjs';
import { createFilmPlan } from './gr3-film-plan.mjs';
import {readFileSync} from 'node:fs';
import {previewFilmPixels} from '../web/gr3/film-preview.mjs';
test('800T has two fixed presets and rejects forged readiness and invalid choices', () => {
  assert.deepEqual(normalize800T({ strength: 'weak' }), { strength: 'weak', timestamp: false, slot: 'bleach' });
  assert.equal(normalize800T({ strength: 'strong', timestamp: true }).timestamp, true);
  for (const value of [{strength:'medium'},{strength:'weak',firmwareReady:true},{strength:'strong',slot:'raw'}, {strength:'strong',timestamp:1}])
    assert.throws(() => normalize800T(value), /800T/);
});
test('800T experimental color tables fit one existing film slot and retain all other choices', () => {
  const film=create800TFilm();const copy=create800TFilm();
  assert.equal(film.name,'800T');assert.equal(film.provenance.calibration,'experimental_unpaired_reference');
  const plan=createFilmPlan(['ektar100','gold200','pro400h','portra400',film.id],[film]);
  assert.equal(plan.custom.length,1);assert.equal(plan.custom[0].mode,'bleach');
  for (const curve of film.curves) assert.ok(curve.every((v,i)=>Number.isInteger(v)&&v>=0&&v<=16383&&(!i||v>=curve[i-1])));
  film.curves[0][40]=0;assert.notEqual(copy.curves[0][40],0);
});
test('800T cyan shadows separate from near-white lights and increase warm/cool saturation',()=>{
 const look=create800TFilm();
 const pixel=(rgb,film=look)=>[...previewFilmPixels(new Uint8ClampedArray([...rgb,255]),{...film,curves:undefined})].slice(0,3);
 for(const n of [32,64,96]) {const p=pixel([n,n,n]);assert.ok(p[1]-p[0]>=9,`cyan green at ${n}: ${p}`);assert.ok(Math.abs(p[2]-p[1])<=18,`cyan rather than blue at ${n}: ${p}`);}
 const white=pixel([255,255,255]);assert.ok(Math.max(...white)-Math.min(...white)<=12);
 const base=JSON.parse(readFileSync(new URL('../web/gr3/film-catalog.json',import.meta.url))).looks.find(x=>x.id==='v3-500t');
 for(const rgb of [[160,100,50],[70,140,170]]) {const a=pixel(rgb,base),b=pixel(rgb);assert.ok(Math.max(...b)-Math.min(...b)>=(Math.max(...a)-Math.min(...a))*1.15,`${rgb}: ${a} -> ${b}`);}
});
test('800T shadows lean blue-cyan without excess green amplification',()=>{
 const film=create800TFilm();
 for(const n of [32,64,96]) {
  const p=previewFilmPixels(new Uint8ClampedArray([n,n,n,255]),{...film,curves:undefined});
  assert.ok(p[2]-p[1]>=8,`blue-cyan separation at ${n}: ${p}`);
  assert.ok(p[2]-p[1]<=18,`avoid deep blue at ${n}: ${p}`);
 }
});
