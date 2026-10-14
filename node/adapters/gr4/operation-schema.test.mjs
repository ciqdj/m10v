import test from 'node:test';
import assert from 'node:assert/strict';
import { GR4_OPERATIONS, validateGr4Operation } from './operation-schema.mjs';

test('GR IV operation inventory covers every latest reference workflow', () => {
  for (const name of ['status', 'settings', 'import', 'project', 'project_save',
    'project_import', 'project_export', 'filter_add', 'filter_remove', 'xmp_import',
    'icon_import', 'calibration_state', 'calibration_register', 'calibration_run',
    'calibration_output', 'crop_preview', 'shutdown_item', 'shutdown_image',
    'shutdown_export', 'toolchain_save', 'build', 'build_download', 'history',
    'history_open', 'history_rollback', 'history_download']) assert.ok(GR4_OPERATIONS.has(name), name);
});

test('GR IV operation validator rejects unknown operations and unsafe identifiers', () => {
  assert.throws(() => validateGr4Operation('unknown', {}), /unknown GR IV operation/);
  assert.throws(() => validateGr4Operation('project', { project_id: '../escape' }), /identifier/);
  assert.deepEqual(validateGr4Operation('project', { project_id: 'project-abc123' }),
    { project_id: 'project-abc123' });
});
