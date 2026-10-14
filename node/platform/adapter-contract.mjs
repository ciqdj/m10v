const ID = /^[a-z][a-z0-9-]{1,31}$/;
const METHODS = ['detect', 'inspect', 'capabilities', 'createDraft', 'validateDraft',
  'previewCrop', 'prepareShutdownAsset', 'build', 'verify', 'rollback', 'outputFilename'];

function check(condition, message) {
  if (!condition) throw new Error(message);
}

export function validateAdapter(value) {
  check(value && typeof value === 'object', 'adapter must be an object');
  check(value.schema_version === 1, 'adapter schema must be 1');
  check(typeof value.id === 'string' && ID.test(value.id), 'invalid adapter id');
  check(typeof value.model === 'string' && value.model.length > 0, 'invalid adapter model');
  check(typeof value.evidence === 'string' && value.evidence.length > 0,
    'invalid adapter evidence');
  check(value.supported !== false, 'unsupported descriptors are not executable adapters');
  for (const method of METHODS) check(typeof value[method] === 'function',
    `adapter method missing: ${method}`);
  return Object.freeze(value);
}

export function validateDescriptor(value) {
  check(value && typeof value === 'object', 'adapter descriptor must be an object');
  check(value.schema_version === 1, 'adapter schema must be 1');
  check(typeof value.id === 'string' && ID.test(value.id), 'invalid adapter id');
  check(typeof value.model === 'string' && value.model.length > 0, 'invalid adapter model');
  check(value.supported === false, 'adapter descriptor must be unsupported');
  check(typeof value.reason === 'string' && value.reason.length > 0,
    'unsupported adapter reason missing');
  return Object.freeze(value);
}

export function publicDescriptor(value) {
  return Object.freeze({ schema_version: value.schema_version, id: value.id,
    model: value.model, supported: value.supported !== false,
    evidence: value.evidence || 'none', ...(value.reason ? { reason: value.reason } : {}) });
}
