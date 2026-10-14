import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyGr4Provenance } from './provenance.mjs';
import {createHash} from 'node:crypto';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import os from 'node:os';

test('local compatibility patches retain upstream identity and verify authored files',async()=>{
  const root=await mkdtemp(path.join(os.tmpdir(),'m10v-provenance-'));
  const hash=text=>createHash('sha256').update(text).digest('hex');
  const manifest={schema_version:1,license:'GPL-2.0-only',source_commit:'a'.repeat(40),
    included_files:{'core.py':hash('upstream')},excluded_roots:[],
    local_modifications:{'core.py':{upstream_sha256:hash('upstream'),local_sha256:hash('patched')}},
    local_authored_files:{'compat.py':hash('authored')}};
  const save=()=>writeFile(path.join(root,'PROVENANCE.json'),JSON.stringify(manifest));
  try{
    await writeFile(path.join(root,'core.py'),'patched');await writeFile(path.join(root,'compat.py'),'authored');await save();
    const result=await verifyGr4Provenance(root);assert.equal(result.included_files['core.py'],hash('upstream'));
    await writeFile(path.join(root,'compat.py'),'tampered');await assert.rejects(verifyGr4Provenance(root),/differs/);
    await writeFile(path.join(root,'compat.py'),'authored');
    manifest.local_modifications['core.py'].upstream_sha256=hash('different upstream');await save();
    await assert.rejects(verifyGr4Provenance(root),/upstream/);
    manifest.local_modifications['core.py'].upstream_sha256=hash('upstream');
    manifest.local_authored_files['../outside.py']=hash('outside');await save();
    await assert.rejects(verifyGr4Provenance(root),/unsafe/);
  }finally{await rm(root,{recursive:true,force:true});}
});

test('vendored GR IV distribution is pinned, fully hashed and excludes runtime server/data', async () => {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../vendor/gr4');
  const manifest = await verifyGr4Provenance(root);
  assert.equal(manifest.source_repository, 'gr-custom-tool');
  assert.ok(Object.keys(manifest.included_files).length > 40);
  assert.ok(manifest.included_files['gr4_editor/firmware.py']);
  assert.ok(manifest.included_files['gr4_editor/service.py']);
  assert.ok(manifest.included_files['web/index.html']);
  assert.ok(manifest.included_files['web/app.js']);
  assert.ok(manifest.included_files['web/calibration-ui.js']);
  assert.ok(manifest.included_files['gr4_editor/assets/lightroom/GR4FirmwareBridge.lrplugin/Bridge.lua']);
  for (const name of ['R0000289.DNG', 'R0000351.DNG', 'R0000398.DNG']) {
    const relative = `gr4_editor/assets/calibration/samples/${name}`;
    assert.match(manifest.included_files[relative], /^[0-9a-f]{64}$/);
    assert.ok(manifest.included_sizes[relative] > 30_000_000);
  }
  assert.deepEqual(manifest.excluded_roots, ['data', 'gr4_editor/server.py']);
});
