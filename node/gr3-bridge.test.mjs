import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeFrameMap,sum32} from './gr3-frames.mjs';
const official=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
const load=()=>import('./gr3-bridge.mjs');
test('bridge has third-component increment component versions and only the evidenced updater code change',async()=>{
 const {buildGr3Bridge,verifyGr3Bridge}=await load();const {candidate,receipt}=buildGr3Bridge(official);
 const d=decodeFrameMap(candidate).decoded;
 assert.equal(candidate.readUInt32BE(0x38),0x020a211b);assert.equal(candidate.readUInt32BE(0x50),0x020a211b);
 // Offsets are independently obtained from section headers below.
 let at=0,sections={};for(let n=0;n<14;n++){const name=d.toString('ascii',at,at+8).replace(/\0/g,'');const size=name==='RES'?6595272:d.readUInt32LE(at+12);sections[name]={at:at+16,size};at+=16+size;}
 assert.equal(d.readUInt32BE(sections.RTOS.at+0x2038),0x020a211b);
 assert.equal(d.readUInt32BE(sections.CPU.at+0x90),0x020a211b);
 assert.equal(d.subarray(sections.RTOS.at+0x6285dc,sections.RTOS.at+0x6285e0).toString('hex'),'e6ffffea');
 assert.equal(sum32(candidate),0);assert.equal(sum32(d),0);
 let cpuSum=0;for(let p=sections.CPU.at;p<sections.CPU.at+131072;p+=4)cpuSum=(cpuSum+d.readUInt32BE(p))>>>0;assert.equal(cpuSum,0);
 assert.equal(receipt.camera_verified,false);assert.equal(receipt.hardware_verification.source,'photo_metadata_and_offline_tests');assert.equal(receipt.hardware_verification.candidate_sha256,'f58ae0ec9453024c607391fb42dcd168394adfdea97fdf166d7060b7115c5baf');assert.equal(receipt.candidate_sha256,receipt.hardware_verification.candidate_sha256);assert.equal(receipt.package_version,'2.10.33.27');
 assert.deepEqual(verifyGr3Bridge(official,candidate),receipt);
 assert.throws(()=>buildGr3Bridge(readFileSync(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url))),/GR III|identity/);
 const wrong=Buffer.from(official);wrong[0x38]^=1;assert.throws(()=>buildGr3Bridge(wrong));
});
test('bridge audit rejects unrelated content, absent gate patch and invalid checksums',async()=>{
 const {buildGr3Bridge,verifyGr3Bridge}=await load();const {candidate}=buildGr3Bridge(official);
 const d=decodeFrameMap(candidate).decoded;
 const rtos=16+72+16+556+16+516+16+44640+16+21816+16;
 function pack(bytes){const chunks=[];for(let p=0;p<bytes.length;p+=0x6000){const part=bytes.subarray(p,p+0x6000),h=Buffer.alloc(2);h.writeUInt16BE(0x8000|part.length);chunks.push(h,part);}chunks.push(Buffer.alloc(2));const body=Buffer.concat(chunks),tail=Buffer.from(candidate.subarray(-24));tail.writeUInt32LE(body.length,12);const b=Buffer.concat([candidate.subarray(0,128),body,Buffer.alloc(-(128+body.length)&3),tail]);b.writeUInt32LE(0,b.length-4);b.writeUInt32LE(-sum32(b)>>>0,b.length-4);return b;}
 assert.equal(verifyGr3Bridge(official,pack(d)).camera_verified,false,'different encoded bytes must not inherit the tested sample status');
 for(const off of [rtos+0x6285dc,rtos+0x10000,0]){let bad=Buffer.from(d);bad[off]^=1;bad.writeUInt32LE(0,bad.length-4);bad.writeUInt32LE(-sum32(bad)>>>0,bad.length-4);assert.throws(()=>verifyGr3Bridge(official,pack(bad)));}
 const bad=Buffer.from(candidate);bad[bad.length-1]^=1;assert.throws(()=>verifyGr3Bridge(official,bad));
});
