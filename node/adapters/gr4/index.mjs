import { NO_MATCH } from '../../platform/adapter-registry.mjs';
import { createGr4Client } from './client.mjs';

function headerInspection(bytes) {
  if (!Buffer.isBuffer(bytes) || bytes.length < 152 || bytes.length % 4) throw NO_MATCH;
  const footer = bytes.length - 24;
  const encoded = bytes.readUInt32LE(footer + 12);
  const metadataStart = (128 + encoded + 3) & ~3;
  if (bytes.readUInt32LE(48) !== 636 || bytes.readUInt32LE(120) !== 0x027c027c ||
      bytes.readUInt32LE(124) !== 0xa55a5aa5 || bytes.readUInt32LE(footer) !== 0x027c027c ||
      bytes.readUInt32LE(footer + 4) !== 0xa55a5aa5 || bytes.readUInt32LE(footer + 8) !== 2 ||
      bytes.readUInt32LE(60) !== 3 || bytes.length - 24 - metadataStart !== 384) throw NO_MATCH;
  let sum = 0;
  for (let offset = 0; offset < bytes.length; offset += 4)
    sum = (sum + bytes.readUInt32LE(offset)) >>> 0;
  if (sum !== 0) throw new Error('GR IV container checksum differs');
  return { model: 'GR IV', public_version: '1.11', container: 'verified',
    evidence: 'container_detected_requires_python_inspection' };
}

export function createGr4Adapter(options = {}) {
  const client = options.client || createGr4Client(options);
  return {
    schema_version: 1,
    id: 'gr4',
    model: 'GR IV',
    supported: true,
    evidence: 'reference_verified',
    detect: headerInspection,
    inspect: (context) => client.request('inspect', { input_path: context.inputPath }, context.workspace),
    capabilities: () => ({
      crop: { status: 'reference_verified', can_edit: true, can_preview: true },
      shutdown: { status: 'reference_verified', can_edit: true, fits: ['contain', 'cover'], max_items: 16 },
      build: { status: 'reference_verified', can_build: true, output: 'fwdc248b.bin',
        requires: ['recognized_GR_IV_container', 'LLVM_toolchain'], hardware: 'not_tested' },
      backup: { project_export: true, original_object_immutable: true },
      history: { load: true, rollback: true },
      version: { family: '1.11.10.*', first_generated: '1.11.10.10', allow_older_gate: true },
    }),
    createDraft: () => ({ schema_version: 1, crops: [],
      shutdown: { schema_version: 1, items: [], assets: [] },
      build_options: { allow_older: true } }),
    validateDraft(value) {
      if (!value || value.schema_version !== 1 || !Array.isArray(value.crops) ||
          !value.shutdown || value.shutdown.schema_version !== 1 ||
          !Array.isArray(value.shutdown.items) || !Array.isArray(value.shutdown.assets) ||
          value.shutdown.items.length > 16 ||
          !value.build_options || typeof value.build_options.allow_older !== 'boolean')
        throw new Error('invalid GR IV draft');
      for (const item of value.shutdown.items)
        if (!['contain', 'cover'].includes(item.fit)) throw new Error('invalid shutdown fit');
      return value;
    },
    previewCrop: (context) => client.request('crop_preview', {
      project_id: context.projectId, ratio: context.ratio }, context.workspace),
    prepareShutdownAsset: (context) => client.request('shutdown_import', {
      project_id: context.projectId, image_path: context.imagePath, target_id: context.targetId,
      filename: context.filename, fit: context.fit, item_id: context.itemId,
      item_name: context.itemName }, context.workspace),
    build: (context) => client.request('build', { project_id: context.projectId,
      version: context.version, allow_older: context.allowOlder }, context.workspace),
    verify: (context) => client.request('project', { project_id: context.projectId }, context.workspace),
    rollback: (context) => client.request('rollback', { project_id: context.projectId,
      sha256: context.sha256, version: context.version, allow_older: context.allowOlder }, context.workspace),
    outputFilename: () => 'fwdc248b.bin',
    allocateVersion: (source, ledger = [], requested) =>
      client.request('allocate_version', { source, ledger, requested }),
    client,
  };
}

export { headerInspection as inspectGr4Header };
