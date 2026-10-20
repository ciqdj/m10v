// Six stock LUTs (60,750 bytes), six icons (38,400 bytes), Phoenix EI120
// (10,125 bytes) and its native controls extend the previous 744 KiB budget.
// Measured worst configuration: 875,320 bytes growth, base 0x540ba000,
// debug/live color/HDF/SD/native grain/NEON/all capture extensions enabled.
// Its end is 0x5418b0f8; the ceiling leaves 42,184 bytes of headroom.
// Construction and independent audits share this bounded 896 KiB ceiling;
// every mapped section and non-target byte is still checked on fresh decode.
export const MAX_NATIVE_RTOS_GROWTH=896*1024;
