import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {prepareCustomization,buildCustomization} from './gr3-customization.mjs';
import {stockPresetCapabilities} from './gr3-stock-presets.mjs';
import {decodeFrameMap} from './gr3-frames.mjs';
import {auditGr3Candidate} from './gr3-candidate-audit.mjs';
const x=readFileSync(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url));
const g=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
const sha=b=>createHash('sha256').update(b).digest('hex');
const selection={variant:'street',features:['negativeGrain','presets','rawNr'],negativeGrainMenu:true,stockPresets:[{slot:2,name:'Summer'}],rawNr:{mode:'threshold',iso:6400}};
test('GR IIIx exposes the same verified stock preset capabilities',()=>{
 assert.deepEqual(stockPresetCapabilities(x),stockPresetCapabilities(g));
});
test('GR IIIx legacy customization binds its source and keeps independent G and port audits',async()=>{
 const p=await prepareCustomization(x,selection),gp=await prepareCustomization(g,selection);
 assert.equal(p.ready,true);assert.equal(p.source_sha256,sha(x));assert.equal(p.filename,'fwdc243b.bin');assert.notEqual(p.configuration_sha256,gp.configuration_sha256);
 await assert.rejects(()=>buildCustomization(x,selection,gp.configuration_sha256),/变化|预检/);
 const r=await buildCustomization(x,selection,p.configuration_sha256);
 const gr=await buildCustomization(g,selection,gp.configuration_sha256);
 assert.throws(()=>auditGr3Candidate(g,gr.candidate),/growth/);
 assert.equal(auditGr3Candidate(g,gr.candidate,{minRtosGrowth:0}).rtosGrowth,0);
 assert.throws(()=>auditGr3Candidate(g,gr.candidate,{minRtosGrowth:-1}),/growth/);
 assert.equal(r.receipt.audit.candidateBytes,r.candidate.length);assert.equal(r.receipt.audit.reference_audit,'gr3_audit');
 assert.equal(r.receipt.configuration_sha256,p.configuration_sha256);assert.equal(r.receipt.source_sha256,sha(x));assert.equal(r.receipt.candidate_sha256,sha(r.candidate));
 assert.equal(r.receipt.gr3x_port.verified,true);assert.equal(r.receipt.gr3x_port.checks.cpu_payload_unchanged,true);assert.equal(r.receipt.camera_tested,false);
 assert.deepEqual(r.candidate.subarray(0,128),x.subarray(0,128));
 const d=decodeFrameMap(r.candidate).decoded,old=decodeFrameMap(x).decoded,report=(await import('./firmware.mjs')).inspectOfficial(x);
 let at=0;for(const s of report.sections){if(s.name==='CPU')assert.deepEqual(d.subarray(at,at+s.size),old.subarray(at,at+s.size));at+=s.size;}
 await assert.rejects(()=>buildCustomization(x,{...selection,negativeGrainMenu:false},p.configuration_sha256),/变化|预检/);
});

test('GR IIIx ports audited legacy recipe, timestamp, aspect and level composition with stock edits',async()=>{
 const parameters=Object.fromEntries(['saturation','hue','high_low_key','contrast','highlight_contrast','shadow_contrast','sharpness','shading','clarity'].map(k=>[k,0]));
 const input={...selection,features:['recipes','timestamp','aspect','level',...selection.features],recipes:[{slotId:'custom1',cameraName:'Leica',baseEffect:'Standard',iconMode:'original',source:'community_reference',id:'cookbook_photo-stuff-leica-look',parameters}]};
 const p=await prepareCustomization(x,input);assert.equal(p.ready,true);
 const r=await buildCustomization(x,input,p.configuration_sha256);
 assert.equal(r.receipt.gr3x_port.verified,true);assert.ok(r.receipt.gr3_audit.rtosGrowth>0);
 assert.deepEqual(r.receipt.features,['recipes','timestamp','aspect','level','presets','negativeGrain','rawNr']);
 assert.equal(r.receipt.gr3x_port.model_words.length,19);assert.equal(r.receipt.gr3x_port.checks.cpu_payload_unchanged,true);
});
