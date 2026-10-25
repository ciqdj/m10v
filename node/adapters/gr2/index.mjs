export const gr2Descriptor = Object.freeze({
  schema_version: 1,
  id: 'gr2',
  model: 'GR II',
  supported: false,
  evidence: 'container_and_checksum_verified_offline',
  reason: 'GR II 3.00 inventory and update checksum verified; native ABI and final loader handoff are under research',
  capabilities: () => ({
    inspect: {status:'verified_offline',can_read:true},
    experimental_firmware: {status:'experimental_offline',can_build:true,hardware_verified:false,release_ready:false,workspace_url:'/gr2/'},
    update_checksum: {status:'verified_offline',can_read:true,can_recompute:true,
      evidence:'docs/research/gr2-checksum-loader-2026-10-20.md'},
    native_film_library: {status:'researching',can_build:false,
      reason:'Native menu, capture ABI and final loader handoff require further reverse analysis'},
  }),
});
