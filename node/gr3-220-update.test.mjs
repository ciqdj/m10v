import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {decodeFrameMap,sum32} from './gr3-frames.mjs';
import * as versions from './gr3-version-unlock.mjs';
const stock=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
const option={imported_sha256:'5c53760b3b564c87239dbf7f5c94d0f6fd91accd156ec4ba672ebfd6b861793e'};
test('2.20 update compatibility raises both components and preserves a recoverable updater',()=>{
 const original=Buffer.from(stock),result=versions.applyGr3UpdateCompatibility(stock,option),b=result.candidate;
 assert.ok(stock.equals(original));
 assert.equal(b.readUInt32BE(0x38),0x0214151c);assert.equal(b.readUInt32BE(0x50),0x0214151c);
 const {decoded:d}=decodeFrameMap(b);let at=0,sections={};
 while(at<d.length-4){const name=d.toString('ascii',at,at+8).split('\0')[0];let n=d.readUInt32LE(at+12);if(name==='RES')n=6595272;sections[name]={offset:at+16,size:n};at+=16+n;}
 assert.equal(d.readUInt32BE(sections.RTOS.offset+0x2038),0x0214151c);
 assert.equal(d.readUInt32BE(sections.CPU.offset+0x90),0x0214151c);
 assert.equal(d.subarray(sections.RTOS.offset+0x6285dc,sections.RTOS.offset+0x6285e0).toString('hex'),'e6ffffea');
 assert.equal(sum32(b),0);assert.equal(sum32(d),0);let sum=0;
 for(let p=sections.CPU.offset;p<sections.CPU.offset+sections.CPU.size;p+=4)sum=(sum+d.readUInt32BE(p))>>>0;
 assert.equal(sum,0);assert.equal(result.receipt.camera_verified,false);
 assert.deepEqual(versions.verifyGr3UpdateCompatibility(stock,b,option),result.receipt);
 const bad=Buffer.from(b);bad[0x38]^=1;assert.throws(()=>versions.verifyGr3UpdateCompatibility(stock,bad,option));
});
test('2.10 and IIIx exports remain byte identical; modified baselines are refused for 2.20',()=>{
 assert.ok(versions.applyGr3UpdateCompatibility(stock,{imported_sha256:'other'}).candidate.equals(stock));
 const x=readFileSync(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url));
 assert.ok(versions.applyGr3UpdateCompatibility(x,{}).candidate.equals(x));
 assert.throws(()=>versions.applyGr3UpdateCompatibility(x,option));
 const b=Buffer.from(stock);b[200]^=1;assert.throws(()=>versions.applyGr3UpdateCompatibility(b,option));
});

test('independent 2.20 audit rejects repaired-checksum executable tampering',()=>{
 const good=versions.applyGr3UpdateCompatibility(stock,option).candidate;
 const d=Buffer.from(decodeFrameMap(good).decoded);d[100000]^=1;
 d.writeUInt32LE(0,d.length-4);d.writeUInt32LE(-sum32(d)>>>0,d.length-4);
 const chunks=[];for(let at=0;at<d.length;at+=0x6000){const part=d.subarray(at,at+0x6000),h=Buffer.alloc(2);h.writeUInt16BE(0x8000|part.length);chunks.push(h,part);}
 chunks.push(Buffer.alloc(2));const payload=Buffer.concat(chunks),footer=Buffer.from(good.subarray(-24));footer.writeUInt32LE(payload.length,12);
 const changed=Buffer.concat([good.subarray(0,128),payload,Buffer.alloc(-(128+payload.length)&3),footer]);
 changed.writeUInt32LE(0,changed.length-4);changed.writeUInt32LE(-sum32(changed)>>>0,changed.length-4);
 assert.equal(sum32(changed),0);
 assert.throws(()=>versions.verifyGr3UpdateCompatibility(stock,changed,option),/非目标/);
});
