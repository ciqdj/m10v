import test from 'node:test';
import assert from 'node:assert/strict';
import {filmToneMap,stockSafeTone,privateFilmToneFromRawEnum} from './gr3-appended-films.mjs';

test('six added films fit the documented menu, RAW, EXIF, icon and record capacities',()=>{
  const map=filmToneMap(['a','b','c','d','e','f'].map(id=>({id})));
  assert.deepEqual(map.map(x=>x.tone),[25,26,27,28,29,30]);
  assert.deepEqual(map.map(x=>x.rawEnum),[13,14,15,16,17,18]);
  assert.deepEqual(map.map(x=>x.imageTone),[0x10c,0x10d,0x10e,0x10f,0x110,0x111]);
  assert.deepEqual(map.map(x=>x.recordSlot),[1,2,3,4,5,7]);
  assert.deepEqual(map.map(x=>x.iconId),[5,6,7,0x1d,0x2d,0x2e]);
  assert.deepEqual(map.map(x=>x.menuIndex),[12,13,14,15,16,17]);
  assert.equal(privateFilmToneFromRawEnum(18,map),30);
  assert.equal(privateFilmToneFromRawEnum(9,map),null);
  assert.equal(stockSafeTone(30,map),30);
  assert.equal(stockSafeTone(22,map),22);
  assert.equal(stockSafeTone(31,map),11);
});

test('invalid count, duplicate IDs and malformed IDs cannot enter a firmware map',()=>{
  assert.throws(()=>filmToneMap([]),/1至6/);
  assert.throws(()=>filmToneMap(Array.from({length:7},(_,i)=>({id:`f${i}`}))),/1至6/);
  assert.throws(()=>filmToneMap([{id:'a'},{id:'a'}]),/重复/);
  assert.throws(()=>filmToneMap([{id:'../foo'}]),/无效/);
});
