import test from 'node:test';
import assert from 'node:assert/strict';
import {parseCustomCube} from './gr3-custom-lut.mjs';

const identity=`LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n`;
test('identity cube samples to 13 cubed RGB bytes',()=>{
 const result=parseCustomCube(Buffer.from(identity),'identity.cube','My Film');
 assert.equal(result.rgb.length,6591);
 assert.deepEqual([...result.rgb.subarray(0,3)],[0,0,0]);
 assert.deepEqual([...result.rgb.subarray(-3)],[255,255,255]);
 assert.equal(result.rgb[3],21);
});
test('malformed and unsupported cubes are rejected',()=>{
 for(const input of ['', 'LUT_1D_SIZE 2\n0\n1',identity.replace('1 1 1','NaN 1 1'),identity.slice(0,-6)])
  assert.throws(()=>parseCustomCube(Buffer.from(input),'bad.cube','My Film'));
 assert.throws(()=>parseCustomCube(Buffer.from(identity),'bad.cube','胶卷'));
});
