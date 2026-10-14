import { publicDescriptor, validateAdapter, validateDescriptor } from './adapter-contract.mjs';

export const NO_MATCH = Symbol('NO_MATCH');

export function createRegistry(values) {
  if (!Array.isArray(values) || values.length === 0) throw new Error('adapter list is empty');
  const entries = values.map((value) => value?.supported === false ?
    validateDescriptor(value) : validateAdapter(value));
  const ids = new Set();
  for (const entry of entries) {
    if (ids.has(entry.id)) throw new Error(`duplicate adapter id: ${entry.id}`);
    ids.add(entry.id);
  }
  const active = entries.filter((entry) => entry.supported !== false);
  return Object.freeze({
    list: () => entries.map(publicDescriptor),
    get(id) {
      const entry = entries.find((candidate) => candidate.id === id);
      if (!entry) throw new Error(`unknown adapter: ${id}`);
      return entry;
    },
    detect(bytes) {
      const matches = [];
      const errors = [];
      for (const entry of active) {
        try { matches.push({ adapter: entry, inspection: entry.detect(bytes) }); }
        catch (error) {
          if (error !== NO_MATCH) errors.push(`${entry.id}: ${error?.message || String(error)}`);
        }
      }
      if (errors.length) throw new Error(`firmware detection failed: ${errors.join('; ')}`);
      if (matches.length > 1) throw new Error('ambiguous firmware: multiple adapters matched');
      if (matches.length === 0) throw new Error('unsupported firmware');
      return matches[0];
    },
  });
}
