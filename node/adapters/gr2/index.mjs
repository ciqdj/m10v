export const gr2Descriptor = Object.freeze({
  schema_version: 1,
  id: 'gr2',
  model: 'GR II',
  supported: false,
  evidence: 'container_verified_offline',
  reason: 'GR II 3.00 inspection verified; modified checksum and native runtime are not yet proved',
  capabilities: () => ({
    inspect: {status:'verified_offline',can_read:true},
    native_film_library: {status:'not_ported',can_build:false},
  }),
});
