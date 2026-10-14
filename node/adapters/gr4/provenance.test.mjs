import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyGr4Provenance } from './provenance.mjs';

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
