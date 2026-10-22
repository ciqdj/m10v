// Shared construction and independent readback ceiling. The existing 960 KiB
// includes immutable film/icon data. Reserve a further bounded 16 KiB for the
// two-slot focal runtime, captions, controller and aspect adapters; compiler
// versions produce different ARM sizes. Keep preimage, section, tail and final
// decode verification over the entire expanded extent.
export const MAX_NATIVE_RTOS_GROWTH=976*1024;
