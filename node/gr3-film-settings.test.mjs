import test from 'node:test';
import assert from 'node:assert/strict';
import {filmToneMap} from './gr3-appended-films.mjs';
import {encodeFilmSettings,decodeFilmSettings} from './gr3-film-settings.mjs';

const bank=(value)=>Array.from({length:3},()=>Array(9).fill(value));
const map=filmToneMap([{id:'portra'},{id:'ektar'},{id:'gold'}]);

test('settings round-trip by stable film ID and follow reorder or removal',()=>{
  const bytes=encodeFilmSettings([{id:'portra',banks:bank(2),grain:3},
    {id:'gold',banks:bank(-4),grain:1}],map);
  assert.equal(bytes.length,20+2*64);
  const original=decodeFilmSettings(bytes,map);
  assert.equal(original.recovered,false);
  assert.equal(original.settings[0].tone,25);
  const reordered=decodeFilmSettings(bytes,filmToneMap([{id:'gold'},{id:'portra'}]));
  assert.equal(reordered.settings[0].tone,26);
  assert.equal(reordered.settings[1].tone,25);
  const removed=decodeFilmSettings(bytes,filmToneMap([{id:'portra'}]));
  assert.equal(removed.recovered,true);
  assert.equal(removed.reason,'removed_film');
  assert.equal(removed.settings.length,1);
  assert.equal(decodeFilmSettings(bytes,[]).reason,'removed_film');
});

test('truncated, unknown schema and damaged parameters recover without private IDs',()=>{
  const bytes=encodeFilmSettings([{id:'portra',banks:bank(0),grain:0}],map);
  assert.deepEqual(decodeFilmSettings(bytes.subarray(0,-1),map).settings,[]);
  const badCrc=Buffer.from(bytes);badCrc[50]^=1;
  assert.equal(decodeFilmSettings(badCrc,map).reason,'crc');
  const badSchema=Buffer.from(bytes);badSchema.writeUInt16LE(2,8);
  assert.equal(decodeFilmSettings(badSchema,map).reason,'schema');
  const badLength=Buffer.from(bytes);badLength.writeUInt32LE(4,12);
  assert.equal(decodeFilmSettings(badLength,map).reason,'length');
});

test('encode rejects out-of-range sliders and unknown film ownership',()=>{
  assert.throws(()=>encodeFilmSettings([{id:'other',banks:bank(0),grain:0}],map),/ID无效/);
  assert.throws(()=>encodeFilmSettings([{id:'portra',banks:bank(5),grain:0}],map),/三组/);
  assert.throws(()=>encodeFilmSettings([{id:'portra',banks:bank(0),grain:4}],map),/颗粒/);
});
