import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {decodeFrameMap,sum32} from './gr3-frames.mjs';

// This catches omitted component checks, unreviewed byte changes, and loss of
// composed native payloads; expected version values are literal test inputs.
const load=()=>import('./gr3-version-unlock.mjs');
const official=readFileSync(new URL('../bin/fwdc239b-gr3-official.bin',import.meta.url));
const source=decodeFrameMap(official).decoded;
const sizes=[72,556,516,44640,21816,17520064,3062784,13899776,49152,131072,37440,18354964,36,6595272];
const start=n=>sizes.slice(0,n).reduce((a,s)=>a+s+16,0)+16;
function repair(b){b.writeUInt32LE(0,b.length-4);b.writeUInt32LE(-sum32(b)>>>0,b.length-4);return b;}
// Independent literal encoder. No production version builder computes fixtures.
function pack(decoded,header=official.subarray(0,128)){
 const chunks=[];for(let at=0;at<decoded.length;at+=0x6000){const part=decoded.subarray(at,at+0x6000),p=Buffer.alloc(2);p.writeUInt16BE(0x8000|part.length);chunks.push(p,part);}
 chunks.push(Buffer.alloc(2));const payload=Buffer.concat(chunks),footer=Buffer.from(official.subarray(-24));
 footer.writeUInt32LE(payload.length,12);footer.writeUInt32LE(decoded.length,16);footer.writeUInt32LE(0,20);
 return repair(Buffer.concat([header,payload,Buffer.alloc(-(128+payload.length)&3),footer]));
}
function fixture(){
 const end=start(5)+sizes[5],decoded=Buffer.concat([source.subarray(0,end),Buffer.from('M10V native composed payload!!!!'),source.subarray(end)]);
 const growth=decoded.length-source.length;assert.equal(growth%4,0);
 decoded.writeUInt32LE(sizes[5]+growth,start(5)-4);
 // Preserve independent native/ICONBIN edits as part of the already-audited input.
 decoded[start(5)+0x10000]^=1;decoded[start(11)+growth+0x100]^=1;
 return {candidate:pack(repair(decoded)),growth};
}

test('DSP package mode needs no guessed camera versions and keeps the complete CPU payload unchanged',async()=>{
 const m=await load(),input={enabled:true,mode:'dsp-package-only'};
 assert.deepEqual(m.normalizeVersionUnlock(input),input);
 for(const option of [{...input,dsp:'2.10.21.40'},{...input,cpu:'2.10.21.27'},{enabled:true,mode:'highest'}])
  assert.throws(()=>m.normalizeVersionUnlock(option));
 const {candidate:before,growth}=fixture(),original=Buffer.from(before);
 const {candidate:after,receipt}=m.applyVersionUnlock(before,input),decoded=decodeFrameMap(after,after.readUInt32LE(after.length-8)).decoded;
 assert.deepEqual(before,original);
 assert.equal(after.readUInt32BE(0x38),0x020affff);
 assert.equal(after.readUInt32BE(0x50),0x020a151b);
 assert.equal(decoded.readUInt32BE(start(5)+0x2038),0x020affff);
 const oldDecoded=decodeFrameMap(before,before.readUInt32LE(before.length-8)).decoded,cpu=start(9)+growth;
 assert.deepEqual(decoded.subarray(cpu,cpu+131072),oldDecoded.subarray(cpu,cpu+131072));
 assert.equal(receipt.mode,'dsp-package-only');assert.equal(receipt.current_versions,null);
 assert.deepEqual(receipt.target_versions,{dsp:'2.10.255.255',cpu:'2.10.21.27'});
 assert.equal(receipt.checks.cpu_payload_unchanged,true);
 assert.equal(receipt.camera_verified,false);assert.deepEqual(m.verifyVersionUnlock(before,after,input),receipt);
 // Independently enumerate every allowed logical byte: two DSP words and the
 // decoded checksum only; encoded length / outer checksum are separate framing.
 const allowed=new Set([...[0,1,2,3].map(n=>start(5)+0x2038+n),...[0,1,2,3].map(n=>decoded.length-4+n)]);
 for(let at=0;at<decoded.length;at++)if(!allowed.has(at))assert.equal(decoded[at],oldDecoded[at],`decoded ${at}`);
});

test('DSP package independent audit rejects every CPU byte change even with repaired checksums',async()=>{
 const m=await load(),input={enabled:true,mode:'dsp-package-only'},good=m.applyVersionUnlock(official,input).candidate;
 const d=decodeFrameMap(good).decoded;
 for(const at of [start(9)+0x90,start(9)+0x100]){
  const changed=Buffer.from(d);changed[at]^=1;changed.writeUInt32BE(0,start(9)+0x7c);
  let total=0;for(let p=start(9);p<start(9)+131072;p+=4)total=(total+changed.readUInt32BE(p))>>>0;
  changed.writeUInt32BE(-total>>>0,start(9)+0x7c);
  assert.throws(()=>m.verifyVersionUnlock(official,pack(repair(changed),good.subarray(0,128)),input));
 }
 const outerCpu=Buffer.from(good);outerCpu[0x53]^=1;repair(outerCpu);
 assert.throws(()=>m.verifyVersionUnlock(official,outerCpu,input));
});

test('version unlock module exposes a disabled-by-default opt-in contract',async()=>{
 const m=await load();assert.deepEqual(m.normalizeVersionUnlock(),{enabled:false});
 assert.deepEqual(m.normalizeVersionUnlock({enabled:false}),{enabled:false});
 assert.deepEqual(m.normalizeVersionUnlock({enabled:true,dsp:'02.10.21.40',cpu:'2.10.21.27'}),{enabled:true,dsp:'2.10.21.40',cpu:'2.10.21.27'});
 assert.deepEqual(m.normalizeVersionUnlock({enabled:true,mode:'observed-versions',dsp:'02.10.21.40',cpu:'2.10.21.27'}),{enabled:true,mode:'observed-versions',dsp:'2.10.21.40',cpu:'2.10.21.27'});
 for(const input of [true,[],{enabled:'true'},{enabled:true},{enabled:true,dsp:'2.10',cpu:'2.10.21.27'},{enabled:true,dsp:'2.10.21.256',cpu:'2.10.21.27'},{enabled:true,dsp:'2.10.21.40',cpu:0},{enabled:true,dsp:'1.60.21.40',cpu:'2.10.21.27'},{enabled:true,dsp:'2.10.21.40',cpu:'2.11.21.27'},{enabled:true,dsp:'2.10.21.40',cpu:'2.10.21.27',force:true}])assert.throws(()=>m.normalizeVersionUnlock(input));
 const {candidate,receipt}=m.applyVersionUnlock(official);
 assert.deepEqual(candidate,official);assert.equal(receipt.enabled,false);assert.equal(receipt.camera_verified,false);
 assert.equal(m.verifyVersionUnlock(official,candidate).enabled,false);
 const bad=Buffer.from(candidate);bad[0]^=1;assert.throws(()=>m.verifyVersionUnlock(official,bad));
});

test('unlock matches independently observed component versions and preserves composed content',async()=>{
 const m=await load(),{candidate:before,growth}=fixture(),input={enabled:true,dsp:'2.10.21.40',cpu:'2.10.21.26'};
 const original=Buffer.from(before),{candidate:after,receipt}=m.applyVersionUnlock(before,input);
 assert.deepEqual(before,original,'caller buffer must not mutate');
 assert.equal(after.readUInt32BE(0x38),0x020a1528);assert.equal(after.readUInt32BE(0x50),0x020a151b);
 const decoded=decodeFrameMap(after,after.readUInt32LE(after.length-8)).decoded;
 assert.equal(decoded.readUInt32BE(start(5)+0x2038),0x020a1528);
 assert.equal(decoded.readUInt32BE(start(9)+growth+0x90),0x020a151b);
 assert.equal(decoded[start(5)+0x10000],source[start(5)+0x10000]^1);
 assert.equal(decoded[start(11)+growth+0x100],source[start(11)+0x100]^1);
 assert.equal(decoded.toString('ascii',start(5)+sizes[5],start(5)+sizes[5]+4),'M10V');
 assert.deepEqual(receipt.current_versions,{dsp:'2.10.21.40',cpu:'2.10.21.26'});
 assert.deepEqual(receipt.target_versions,{dsp:'2.10.21.40',cpu:'2.10.21.27'});
 assert.equal(receipt.camera_verified,false);assert.equal(receipt.checks.non_target_unchanged,true);
 assert.deepEqual(m.verifyVersionUnlock(before,after,input),receipt);
});

test('CPU version changes repair its BE checksum and lower observations never downgrade the baseline',async()=>{
 const m=await load(),input={enabled:true,dsp:'2.10.21.26',cpu:'2.10.22.1'},r=m.applyVersionUnlock(official,input);
 assert.equal(r.candidate.readUInt32BE(0x38),0x020a151b);assert.equal(r.candidate.readUInt32BE(0x50),0x020a1601);
 const d=decodeFrameMap(r.candidate).decoded;let cpuSum=0;
 for(let at=start(9);at<start(9)+131072;at+=4)cpuSum=(cpuSum+d.readUInt32BE(at))>>>0;
 assert.equal(cpuSum,0);assert.notEqual(d.readUInt32BE(start(9)+0x7c),source.readUInt32BE(start(9)+0x7c));
 const unchanged=m.applyVersionUnlock(official,{enabled:true,dsp:'2.10.21.1',cpu:'2.10.21.1'});
 assert.deepEqual(unchanged.candidate,official);assert.equal(unchanged.receipt.checks.non_target_unchanged,true);
});

test('independent verification rejects wrong versions, extra executable bytes, model/header/section changes and broken checksums',async()=>{
 const m=await load(),input={enabled:true,dsp:'2.10.21.40',cpu:'2.10.21.41'},good=m.applyVersionUnlock(official,input).candidate;
 const d=decodeFrameMap(good).decoded;
 // Even with every additive checksum repaired, an unlisted payload edit fails.
 for(const at of [start(5)+0x2038,start(5)+0x10000,start(9)+0x90,start(11)+0x100,start(5)-8]){
  const modified=Buffer.from(d);modified[at]^=1;
  modified.writeUInt32BE(0,start(9)+0x7c);let sum=0;for(let p=start(9);p<start(9)+131072;p+=4)sum=(sum+modified.readUInt32BE(p))>>>0;
  modified.writeUInt32BE(-sum>>>0,start(9)+0x7c);
  assert.throws(()=>m.verifyVersionUnlock(official,pack(repair(modified),good.subarray(0,128)),input));
 }
 for(const at of [0,0x30,0x38,0x50,0x78,good.length-24]){
  const modified=Buffer.from(good);modified[at]^=1;repair(modified);
  assert.throws(()=>m.verifyVersionUnlock(official,modified,input));
 }
 const badSum=Buffer.from(good);badSum[badSum.length-1]^=1;assert.throws(()=>m.verifyVersionUnlock(official,badSum,input));
 const badCpu=Buffer.from(source);badCpu[start(9)+0x90]^=1;assert.throws(()=>m.applyVersionUnlock(pack(repair(badCpu)),input));
 const x=Buffer.from(official);x.writeUInt32LE(609,0x30);repair(x);assert.throws(()=>m.applyVersionUnlock(x,input));
});

// A changed version word can be in a later frame's backward-reference history.
// Content-only frame reuse must not corrupt an unchanged following word.
test('repacking does not reuse a compressed frame whose backward history changed',async()=>{
 const m=await load();
 for(const distance of [4,4096]){
 const versionAt=start(5)+0x2038,at=versionAt+distance,decoded=Buffer.from(source);
 decoded.writeUInt32BE(0x020a151b,at);repair(decoded);
 const chunks=[];
 for(const [from,to] of [[0,at],[at+4,decoded.length]]){
  if(from)chunks.push(Buffer.from([0,6,0xc0,0,((distance>>>8)<<3)|1,distance&255,0,0]));
  for(let p=from;p<to;p+=0x6000){const part=decoded.subarray(p,Math.min(p+0x6000,to)),h=Buffer.alloc(2);h.writeUInt16BE(0x8000|part.length);chunks.push(h,part);}
 }
 chunks.push(Buffer.alloc(2));const payload=Buffer.concat(chunks),footer=Buffer.from(official.subarray(-24));
 footer.writeUInt32LE(payload.length,12);footer.writeUInt32LE(decoded.length,16);
 const before=repair(Buffer.concat([official.subarray(0,128),payload,Buffer.alloc(-(128+payload.length)&3),footer]));
 assert.deepEqual(decodeFrameMap(before).decoded,decoded);
 const {candidate}=m.applyVersionUnlock(before,{enabled:true,dsp:'2.10.21.40',cpu:'2.10.21.27'});
 const after=decodeFrameMap(candidate).decoded;
 assert.equal(after.readUInt32BE(versionAt),0x020a1528);assert.equal(after.readUInt32BE(at),0x020a151b);
 }
});


test('GR IIIx exact profile supports its 1.60 version line and preserves its CPU in DSP package mode',async()=>{
 const m=await load(),x=readFileSync(new URL('../bin/fwdc243b-gr3x-official.bin',import.meta.url));
 const input={enabled:true,mode:'dsp-package-only'};
 assert.deepEqual(m.normalizeVersionUnlock(input,'gr3x'),input);
 for(const model of ['gr4','__proto__','constructor',null])assert.throws(()=>m.normalizeVersionUnlock(input,model));
 assert.deepEqual(m.normalizeVersionUnlock({enabled:true,dsp:'1.60.11.18',cpu:'1.60.11.16'},'gr3x'),{enabled:true,dsp:'1.60.11.18',cpu:'1.60.11.16'});
 assert.throws(()=>m.normalizeVersionUnlock({enabled:true,dsp:'2.10.21.27',cpu:'2.10.21.27'},'gr3x'));
 const result=m.applyVersionUnlock(x,input),d=decodeFrameMap(result.candidate).decoded,old=decodeFrameMap(x).decoded;
 assert.equal(result.candidate.readUInt32LE(0x30),609);assert.equal(result.candidate.readUInt32LE(0x78),0x02610261);
 assert.equal(result.candidate.readUInt32BE(0x38),0x013cffff);assert.equal(result.candidate.readUInt32BE(0x50),0x013c0b11);
 assert.deepEqual(d.subarray(start(9),start(9)+131072),old.subarray(start(9),start(9)+131072));
 assert.deepEqual(result.receipt.target_versions,{dsp:'1.60.255.255',cpu:'1.60.11.17'});
 assert.deepEqual(m.verifyVersionUnlock(x,result.candidate,input),result.receipt);
 const advanced=m.applyVersionUnlock(x,{enabled:true,dsp:'1.60.11.16',cpu:'1.60.12.1'});
 assert.deepEqual(advanced.receipt.target_versions,{dsp:'1.60.11.17',cpu:'1.60.12.1'});
 assert.throws(()=>m.applyVersionUnlock(x,{enabled:true,dsp:'2.10.21.40',cpu:'2.10.21.27'}));
 const mixed=Buffer.from(x);mixed.writeUInt32LE(588,0x30);repair(mixed);assert.throws(()=>m.applyVersionUnlock(mixed,input));
 const changed=Buffer.from(d);changed[start(9)+0x100]^=1;changed.writeUInt32BE(0,start(9)+0x7c);
 let total=0;for(let at=start(9);at<start(9)+131072;at+=4)total=(total+changed.readUInt32BE(at))>>>0;
 changed.writeUInt32BE(-total>>>0,start(9)+0x7c);
 const forged=pack(repair(changed),result.candidate.subarray(0,128));forged.writeUInt32LE(0x02610261,forged.length-24);repair(forged);
 assert.throws(()=>m.verifyVersionUnlock(x,forged,input));
});
