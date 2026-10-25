import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {normalizeGr4Request,validateGr4Source,GR4_OFFICIAL_SHA256} from './gr4-m10v-native-build.mjs';
import {defaultConfiguration} from '../web/gr3/native-library-state.mjs';
test('GR IV shares full five-slot semantics but rejects invalid source and unsupported version adaptation',async()=>{
 const configuration=defaultConfiguration();configuration.slots[4].effects.leakGain=8;configuration.stamp=2;
 assert.deepEqual(normalizeGr4Request({configuration}).configuration,{...configuration,slots:configuration.slots.map(s=>({...s,effects:{...s.effects,leakGain:0}}))});
 assert.throws(()=>normalizeGr4Request({configuration,debug_mode:'true'}));
 assert.throws(()=>normalizeGr4Request({configuration,version_unlock:{enabled:true}}));
 assert.throws(()=>validateGr4Source(Buffer.alloc(256)));
 const official=await readFile(new URL('../bin/fwdc248b-gr4-officical.bin',import.meta.url));assert.doesNotThrow(()=>validateGr4Source(official));
 assert.equal(GR4_OFFICIAL_SHA256,'a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f');
});

test('GR IV download receipt fits HTTP headers while retaining configuration and binary proof',async()=>{
 const {gr4DownloadReceipt}=await import('./gr4-m10v-native-build.mjs');
 const report={source_sha256:GR4_OFFICIAL_SHA256,runtime_source_sha256:'a'.repeat(64),candidate_sha256:'b'.repeat(64),candidate_bytes:40000000,filename:'fwdc248b.bin',camera_tested:false,configuration:defaultConfiguration(),runtime:{code_sha256:'c'.repeat(64),code_bytes:123,sources:{large:'x'.repeat(40000)}},patches:[{address:1}],resources:{texts:Array(184).fill('label'),icon_first:1024,icon_last:1091},validation:{offline:'passed',hardware:'not_tested'}};
 const receipt=gr4DownloadReceipt(report);
 assert.ok(Buffer.byteLength(Buffer.from(JSON.stringify(receipt)).toString('base64'))<8000);
 assert.deepEqual(receipt.configuration,report.configuration);assert.equal(receipt.candidate_sha256,report.candidate_sha256);assert.equal(receipt.icon_count,68);assert.equal(receipt.verified_hooks,1);
});
