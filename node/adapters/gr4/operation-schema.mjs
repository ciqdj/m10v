const names = ['handshake', 'allocate_version', 'status', 'settings', 'import', 'project',
  'project_save', 'project_import', 'project_export', 'filter_add', 'filter_remove',
  'xmp_import', 'icon_import', 'calibration_state', 'calibration_register',
  'calibration_run', 'calibration_output', 'crop_preview', 'shutdown_item',
  'shutdown_image', 'shutdown_export', 'toolchain_save', 'build', 'build_download',
  'history', 'history_open', 'history_rollback', 'history_download'];

names.push('inspect', 'save', 'shutdown_import', 'shutdown_add', 'rollback');
export const GR4_OPERATIONS = new Set(names);
const ID = /^[a-zA-Z0-9_-]{1,90}$/;
const SHA = /^[0-9a-f]{64}$/;

export function validateGr4Operation(operation, payload = {}) {
  if (!GR4_OPERATIONS.has(operation)) throw new Error(`unknown GR IV operation: ${operation}`);
  if (!payload || typeof payload !== 'object' || Array.isArray(payload))
    throw new Error('invalid GR IV payload');
  for (const [key, value] of Object.entries(payload)) {
    if ((key === 'project_id' || key === 'filter_id' || key === 'build_id' || key === 'job_id') &&
        value != null && !ID.test(value)) throw new Error(`invalid GR IV identifier: ${key}`);
    if (key === 'sha256' && value != null && !SHA.test(value)) throw new Error('invalid GR IV SHA-256');
  }
  return payload;
}
