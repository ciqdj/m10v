import { inspectOfficial } from '../../firmware.mjs';
import { NO_MATCH } from '../../platform/adapter-registry.mjs';

const unsupported = (feature) => ({ status: 'unsupported', can_edit: false,
  can_build: false, blockers: [`gr3_${feature}_adapter_not_implemented`] });

export function createGr3Adapter() {
  return {
    schema_version: 1,
    id: 'gr3',
    model: 'GR III',
    supported: true,
    evidence: 'exact_sample',
    detect(bytes) {
      try { return inspectOfficial(bytes); } catch { throw NO_MATCH; }
    },
    inspect: inspectOfficial,
    capabilities: () => ({ crop: unsupported('crop'), shutdown: unsupported('shutdown'),
      build: { status: 'blocked', can_build: false,
        blockers: ['gr3_editable_adapter_not_implemented'] } }),
    createDraft: () => ({ schema_version: 1, crops: [], shutdown: { items: [], assets: [] } }),
    validateDraft(value) {
      if (!value || value.schema_version !== 1 || !Array.isArray(value.crops) ||
        !value.shutdown || !Array.isArray(value.shutdown.items) ||
        !Array.isArray(value.shutdown.assets)) throw new Error('invalid GR III draft');
      return value;
    },
    previewCrop: () => { throw new Error('GR III crop preview is not implemented'); },
    prepareShutdownAsset: () => { throw new Error('GR III shutdown assets are not implemented'); },
    build: async () => { throw new Error('GR III build is not implemented'); },
    verify: async () => { throw new Error('GR III candidate verification is not implemented'); },
    rollback: async () => { throw new Error('GR III rollback is not implemented'); },
    outputFilename: () => 'fwdc239b.bin',
  };
}
