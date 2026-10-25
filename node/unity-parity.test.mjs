import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
const moduleURL=new URL('../scripts/check_unity_parity.mjs',import.meta.url);
async function checker(){
  assert.ok(existsSync(moduleURL),'parity completion checker is missing');
  return import(moduleURL);
}
const manifest=()=>JSON.parse(readFileSync(new URL('../docs/testing/gr1-gr2-parity.json',import.meta.url)));
test('parity gate permits honest research but refuses completion',async()=>{
  const {checkParity}=await checker(),ledger=manifest();
  assert.ok(checkParity(ledger).researching>0);
  assert.throws(()=>checkParity(ledger,{complete:true}),/incomplete/);
});
test('parity gate rejects omitted baseline features and unsupported exemptions',async()=>{
  const {checkParity}=await checker(),ledger=manifest();
  const removed=structuredClone(ledger);removed.features.pop();
  assert.throws(()=>checkParity(removed),/missing baseline/);
  const unsupported=structuredClone(ledger);
  unsupported.features[0].models.gr2.status='proven_unavailable';
  assert.throws(()=>checkParity(unsupported),/limitation|evidence/);
});
test('parity gate requires real implementation evidence and hardware acceptance',async()=>{
  const {checkParity}=await checker(),ledger=manifest();
  const row=ledger.features.find(f=>f.models.gr2.status==='researching').models.gr2;
  row.status='verified_offline';
  assert.throws(()=>checkParity(ledger),/implementation|automated/);
  row.implementation_files=['node/gr2-firmware.mjs'];row.automated_checks=['node --test node/gr2-firmware.test.mjs'];
  row.evidence_files=['docs/research/gr1-gr2-official-evidence-2026-10-20.md'];
  assert.doesNotThrow(()=>checkParity(ledger));
  row.status='hardware_verified';
  assert.throws(()=>checkParity(ledger),/hardware/);
});
test('full parity includes global HDF separately from legacy per-slot soft',()=>{
  const ledger=manifest();
  assert.ok(ledger.baseline.required_ids.includes('camera.hdf'),'independent HDF baseline is omitted');
  const hdf=ledger.features.find(f=>f.id==='camera.hdf');
  assert.ok(hdf?.baseline_files.includes('native/gr3/m10v_digital_hdf.c'));
  assert.ok(hdf.baseline_files.includes('native/gr3/m10v_hdf_menu.c'));
  assert.ok(ledger.features.some(f=>f.id==='film.soft'));
});
