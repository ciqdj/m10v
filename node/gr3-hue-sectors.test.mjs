import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeHueSectors,quantizeHueSectors,inspectPackedHueSectors} from './gr3-hue-sectors.mjs';

const identity = () => Array.from({length:12},()=>
  Array.from({length:3},(_,r)=>Array.from({length:3},(_,c)=>r===c?1:0)));

test('identity sectors encode as zeros and read back as exact Q10 identity',()=>{
  const source=identity(),{q10,packed}=quantizeHueSectors(source);
  assert.equal(packed.length,108);
  assert.ok(packed.every(byte=>byte===0));
  assert.deepEqual(inspectPackedHueSectors(packed),q10);
  assert.equal(q10[11][2][2],1024);
  source[0][0][0]=2;
  assert.equal(normalizeHueSectors(identity())[0][0][0],1);
});

test('only the requested sector changes, with a zero-sum signed byte row',()=>{
  const source=identity();source[11][0]=[0.75,0.25,0];
  const {q10,packed}=quantizeHueSectors(source);
  assert.deepEqual(q10[11][0],[768,256,0]);
  assert.deepEqual([...packed.subarray(99,102)],[192,64,0]);
  assert.deepEqual(q10[0][0],[1024,0,0]);
  assert.deepEqual(inspectPackedHueSectors(packed),q10);
});

test('invalid shape, conservation, overflow and malformed packed rows are rejected',()=>{
  assert.throws(()=>normalizeHueSectors([]),/12个分区/);
  const bad=identity();bad[4][2]=[0,0,2];
  assert.throws(()=>quantizeHueSectors(bad),/行和/);
  const overflow=identity();overflow[0][0]=[0,0.51,0.49];
  assert.throws(()=>quantizeHueSectors(overflow),/超出固件有符号范围/);
  const bytes=Buffer.alloc(108);bytes[0]=1;
  assert.throws(()=>inspectPackedHueSectors(bytes),/不守恒/);
});
