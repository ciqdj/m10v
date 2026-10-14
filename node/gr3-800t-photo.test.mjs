import test from 'node:test';
import assert from 'node:assert/strict';
import { createLatestPhotoLoader } from '../web/gr3/photo-load.mjs';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return{promise,resolve,reject};};
test('a late initial sample fetch cannot replace the chosen local photo',async()=>{
 const initial=deferred(),applied=[],errors=[];let decodes=0;
 const load=createLatestPhotoLoader({decode:async(v)=>{decodes++;return {value:v,close(){}}},apply:(b,n)=>applied.push(n),onError:e=>errors.push(e)});
 const old=load(initial.promise,'sample');await load('new','chosen');initial.resolve('old');await old;
 assert.deepEqual(applied,['chosen']);assert.equal(decodes,1);assert.equal(errors.length,0);
});
test('stale decoded bitmaps are closed and stale errors do not replace current status',async()=>{
 const slow=deferred(),applied=[],errors=[];let closed=0;
 const load=createLatestPhotoLoader({decode:v=>v==='slow'?slow.promise:Promise.resolve({value:v,close(){}}),apply:(b,n)=>applied.push(n),onError:e=>errors.push(e)});
 const old=load('slow','old');await Promise.resolve();await load('new','latest');slow.resolve({close(){closed++}});await old;
 assert.deepEqual(applied,['latest']);assert.equal(closed,1);
 const rejected=deferred();const failed=load(rejected.promise,'bad');await load('newer','newer');rejected.reject(new Error('stale'));await failed;assert.equal(errors.length,0);
});
