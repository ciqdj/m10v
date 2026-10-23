import {test} from 'node:test';
import assert from 'node:assert/strict';
import {compareLoaded,compareReference} from '../scripts/compare_gr2_reference.mjs';
function image(sourceShift=0){
 const b=Buffer.alloc(4096);b[16]=1;b.writeUInt32BE(b.length,0x168);b.writeUInt32BE(0xa0020200,0x160);
 for(let i=0;i<16;i++)b.writeUInt32BE(0,32+20*i);
 b.writeUInt32BE(512+sourceShift,32);b.writeUInt32BE(0xa0020200,36);b.writeUInt32BE(16,40);
 Buffer.from(Array.from({length:16},(_,i)=>i+1)).copy(b,1024+sourceShift);return b;
}
test('GR II reference diff aligns loaded addresses despite moved source offsets',()=>{
 const a=image(),b=image(512);assert.deepEqual(compareLoaded(a,b).changes,[]);
 b[1539]^=1;b[1540]^=1;const r=compareLoaded(a,b);
 assert.equal(r.changedBytes,2);assert.equal(r.changes.length,1);assert.equal(r.changes[0].address,0xa0020203);
 b.writeUInt32BE(32,40);assert.deepEqual(compareLoaded(a,b).added,[{address:0xa0020210,length:16,newRecord:0}]);
});
test('GR II reference diff rejects partial/unrecognized artifacts and invalid load bounds',()=>{
 assert.throws(()=>compareReference(Buffer.alloc(2048),Buffer.alloc(2048)),/incomplete|pinned/);
 const a=image(),b=image();b.writeUInt32BE(100000,40);assert.throws(()=>compareLoaded(a,b),/load range/);
});
test('GR II staged loader extensions are reported without conflating another logical record',()=>{
 const a=image(),b=image();
 for(const x of [a,b]){x.writeUInt32BE(1536,52);x.writeUInt32BE(0xa0020240,56);x.writeUInt32BE(16,60);x.fill(0x55,2048,2064);}
 b.writeUInt32BE(80,40);b.fill(0xaa,1040,1104);
 const r=compareLoaded(a,b);
 assert.deepEqual(r.changes,[]);
 assert.equal(r.loadOverlaps.length,1);assert.equal(r.loadOverlaps[0].length,16);
 assert.deepEqual(r.recordExtensions,[{oldRecord:0,newRecord:0,address:0xa0020210,length:64}]);
});
test('GR II scatter decoding preserves literal words and explicit zero runs and rejects malformed counts',async()=>{
 const {decodeScatter}=await import('../scripts/compare_gr2_reference.mjs');
 assert.equal(typeof decodeScatter,'function');
 const packed=Buffer.from('0000000801020304050607088000000800000004090a0b0c','hex');
 assert.deepEqual(decodeScatter(packed,20,true),{bytes:Buffer.from('01020304050607080000000000000000090a0b0c','hex'),consumed:24});
 for(const bad of ['00000000','00000003','80000018','00000008'])assert.throws(()=>decodeScatter(Buffer.from(bad,'hex'),8,true));
});
