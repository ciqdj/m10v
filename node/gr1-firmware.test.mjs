import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
const moduleURL=new URL('./gr1-firmware.mjs',import.meta.url),sample=new URL('../bin/rg1_v051.frm',import.meta.url);
async function implementation(){assert.ok(existsSync(moduleURL),'GR 5.01 inspector is missing');return import(moduleURL);}
test('GR exact official image reads 119 resources with volume header adjustment',{skip:!existsSync(sample)},async()=>{
  const {inspectGr1,readGr1Component}=await implementation(),source=readFileSync(sample),report=inspectGr1(source);
  assert.equal(report.model,'GR');assert.equal(report.public_version,'5.01');assert.equal(report.size,12471808);
  assert.equal(report.resources.length,119);assert.equal(report.resources[0].table_offset,0x654000);
  const image=report.resources.find(r=>r.name==='A:/img/dvf_TDSt.brp');
  assert.equal(image.declared_offset,0xa7400);assert.equal(image.payload_offset,0xa7600);assert.equal(image.size,614400);
  const code=readGr1Component(source,'b01firm8');assert.equal(code.length,5824084);
  assert.equal(code.readUInt16BE(18),0x0501);assert.equal(report.proof.byte_exact_roundtrip,true);
  assert.equal(report.proof.modified_update_checksum,true);assert.equal(report.capabilities.native_film_library.can_build,false);
  assert.throws(()=>readGr1Component(source,'RTOS'),/unknown component/);
});
test('GR identity gate rejects changed and truncated official input',{skip:!existsSync(sample)},async()=>{
  const {inspectGr1}=await implementation(),source=readFileSync(sample),changed=Buffer.from(source);changed[0x900]^=1;
  assert.throws(()=>inspectGr1(changed),/identity/);
  assert.throws(()=>inspectGr1(source.subarray(0,-1)),/size/);
});
