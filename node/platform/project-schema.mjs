import { checkProjectId, checkSha256 } from './ids.mjs';

const keys = ['adapter_id', 'created_at', 'draft', 'id', 'input_sha256', 'revision',
  'schema_version', 'title', 'updated_at'];

export function validateProjectShape(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
    Object.keys(value).sort().join(',') !== keys.join(','))
    throw new Error('invalid project record');
  checkProjectId(value.id);
  checkSha256(value.input_sha256);
  if (value.schema_version !== 1 || typeof value.adapter_id !== 'string' ||
    !/^[a-z][a-z0-9-]{1,31}$/.test(value.adapter_id) ||
    typeof value.title !== 'string' || value.title.length < 1 || value.title.length > 120 ||
    !Number.isSafeInteger(value.revision) || value.revision < 0 ||
    typeof value.created_at !== 'string' || typeof value.updated_at !== 'string' ||
    !value.draft || typeof value.draft !== 'object' || Array.isArray(value.draft))
    throw new Error('invalid project record');
  return value;
}
