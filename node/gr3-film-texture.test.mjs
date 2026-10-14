import test from 'node:test';
import assert from 'node:assert/strict';
import { createFilmPlan } from './gr3-film-plan.mjs';
import * as films from './gr3-film-plan.mjs';
const ids=['ektar100','gold200','pro400h','portra400','vision3-250d'];
test('texture follows film ID through actual slot assignment',()=>{
  const plan=createFilmPlan(ids,[],{'gold200':{grain:1,hdf:0},'portra400':{grain:3,hdf:2}});
  assert.deepEqual(plan.texture,{retro:{grain:1,hdf:0},cross:{grain:3,hdf:2}});
  assert.deepEqual(films.assignFilmSlots(ids).map(x=>[x.id,x.mode]),[
    ['ektar100','vivid'],['gold200','retro'],['pro400h','hdr'],['portra400','cross'],['vision3-250d','bleach']]);
});
test('texture rejects stale film IDs, unknown fields and invalid intensity',()=>{
  for(const texture of [{removed:{grain:1}}, {gold200:{grain:4}}, {gold200:{grain:true}}, {gold200:{soft:1}}, []])
    assert.throws(()=>createFilmPlan(ids,[],texture),/texture/);
});
test('disabled texture preserves the existing upstream bundle',()=>{
  assert.deepEqual(createFilmPlan(ids,[],{gold200:{grain:0,hdf:0}}),{bundle:'films-v10'});
});

import { readFileSync } from 'node:fs';
import { createStorePlan } from './gr3-store-plan.mjs';
import { runGr3Runtime } from './gr3-runtime.mjs';
import { decodeFrameMap } from './gr3-frames.mjs';
import { auditGr3Candidate } from './gr3-candidate-audit.mjs';
test('real GR III build stores correct grain strengths and preserves Positive shared branch',async()=>{
  const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
  const texture=Object.fromEntries(ids.map((id,i)=>[id,{grain:[1,2,3,1,3][i],hdf:0}]));
  const plan=createStorePlan({variant:'street',features:['film'],filmIds:ids,filmTexture:texture});
  const {candidate}=await runGr3Runtime(source,plan,'build');
  auditGr3Candidate(source,candidate);
  const {decoded}=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8));
  const word=a=>decoded.readUInt32LE(0x10870+a-0x53000000);
  assert.equal(word(0x536dbdac),0xe3a06001); // bleach strong
  assert.equal(word(0x536dbe88),0xe3a06002); // retro medium
  assert.equal(word(0x536dbf3c),0xe3a06001); // hdr strong
  assert.equal(word(0x536dc000),0xe3a06003); // cross weak
  const at=0x536db9a8,instruction=word(at);
  assert.equal(instruction>>>24,0xea);
  const signed=(instruction<<8)>>8,target=at+8+signed*4;
  assert.equal(word(target),0xe5d3677c);
  assert.equal(word(target+4),0xe356000c);
  assert.equal(word(target+8),0x03a06003);
  assert.equal(word(target+12),0x13a06000); // non-Vivid retains off
});
import * as textureAudit from './gr3-film-texture.mjs';
test('diffusion hook, frozen code and per-tone levels are read back independently of receipt',async()=>{
 const source=readFileSync(new URL('../fwdc239b.bin',import.meta.url));
 const plan=createStorePlan({variant:'street',features:['film','timestamp'],filmIds:ids,
  filmTexture:{gold200:{grain:1,hdf:2}}});
 const {candidate}=await runGr3Runtime(source,plan,'build');
 const film=plan.features.find(f=>f.id==='film').configuration;
 const audit=textureAudit.auditFilmTexture(source,candidate,film,true);assert.equal(audit.diffusionLevel.retro,2);
 assert.throws(()=>textureAudit.auditFilmTexture(source,candidate,{...film,texture:{retro:{grain:1,hdf:3}}},true),/柔光/);
});
