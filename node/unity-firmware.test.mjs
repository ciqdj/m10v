import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
const moduleURL=new URL('./unity-firmware.mjs',import.meta.url);
async function implementation(){assert.ok(existsSync(moduleURL),'shared UNITY inspector is missing');return import(moduleURL);}
function container(){
  const b=Buffer.alloc(3072,0xff);b.write('UNITY FILE V1.10 / RICOH COMPANY');
  b.writeUInt32BE(b.length,32);b.writeUInt32BE(1,36);b.writeUInt32BE(4,64);b.writeUInt32BE(512,68);
  b.fill(0,72,84);b.write('component',72);b[94]=1;b[95]=1;return b;
}
test('UNITY shared parser preserves padding and rejects duplicate, overlapping and malformed records',async()=>{
  const {decodeUnity}=await implementation(),b=container();
  assert.deepEqual(decodeUnity(b).reencoded,b);
  const duplicate=Buffer.from(b);duplicate.writeUInt32BE(2,36);duplicate.copy(duplicate,128,64,128);
  duplicate.writeUInt32BE(5,128);assert.throws(()=>decodeUnity(duplicate),/duplicated/);
  const overlap=Buffer.from(duplicate);overlap.fill(0,136,148);overlap.write('other',136);overlap.writeUInt32BE(4,128);
  assert.throws(()=>decodeUnity(overlap),/overlap/);
  const encoding=Buffer.from(b);encoding[95]=2;assert.throws(()=>decodeUnity(encoding),/encoding/);
  assert.throws(()=>decodeUnity(b,3),/nesting/);
  assert.throws(()=>decodeUnity(b.subarray(0,-1)),/size/);
});
test('UNITY model APIs never confuse identically named components across models',async()=>{
  const {inspectUnityModel,readUnityModelComponent,decodeUnity}=await implementation();
  for(const [model,file,other] of [['gr2','rg2_v003.frm','gr1'],['gr1','rg1_v051.frm','gr2']]){
    const url=new URL('../bin/'+file,import.meta.url);if(!existsSync(url))continue;
    const source=readFileSync(url);
    assert.throws(()=>inspectUnityModel(source,other),/size|identity/);
    assert.throws(()=>readUnityModelComponent(source,other,'b01firm8'),/size|identity/);
    assert.equal(inspectUnityModel(source,model).components.length,3);
    assert.deepEqual(decodeUnity(source).reencoded,source);
  }
  assert.throws(()=>inspectUnityModel(Buffer.alloc(2048),'gr4'),/unsupported model/);
});
