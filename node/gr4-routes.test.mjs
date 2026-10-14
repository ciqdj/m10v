import test from 'node:test';
import assert from 'node:assert/strict';
import { GR4_ROUTE_INVENTORY } from './gr4-routes.mjs';

test('GR IV HTTP inventory covers every latest editor endpoint', () => {
  for (const route of ['status', 'settings', 'import', 'project', 'project-import',
    'export', 'original', 'add-filter', 'remove-filter', 'xmp', 'icon', 'calibration-state',
    'calibration-output', 'calibration/register', 'calibration/run', 'crop-preview',
    'shutdown-item', 'shutdown-image', 'shutdown-export', 'toolchain', 'build',
    'download', 'history', 'history/open', 'history/rollback', 'history/download'])
    assert.ok(GR4_ROUTE_INVENTORY.has(route), route);
});
