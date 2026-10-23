#ifndef M10V_ISP_NATIVE_EFFECTS_H
#define M10V_ISP_NATIVE_EFFECTS_H
#include <stdint.h>
/* GR III 2.10 SHA256 8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67.
 * Borrow RAM already owned by the stock spatial-stage task. This module does
 * not allocate, create controls, submit, wait, release, reset, or access MMIO.
 * No capture hook is installed. No hardware visual calibration is claimed.
 * The stock graph addressed below affects Y only. Chroma, colored halation,
 * and remaining spatial effects retain their existing
 * implementation until a separately validated native route executes them. */
#define M10V_ISP_NATIVE_SHADING 1u
#define M10V_ISP_NATIVE_CLARITY 2u
#define M10V_ISP_NATIVE_GRAIN 4u
#define M10V_ISP_NATIVE_HDR 8u
struct m10v_isp_native_effects_config {
    uint32_t mask;
    /* Actual native processing values, NOT SI menu values: shading/clarity
     * -4..4; grain/HdrTone 0..3. No implicit soft/halo to clarity mapping. */
    int16_t value[4];
};
/* Copy the original 12-byte settings and replace only selected fields. Scale
 * (+8 float) stays byte-identical. dst==original allowed; any other overlapping
 * objects rejected. All validation precedes writes. Returns 0/-1.
 * Apply BEFORE the ORIGINAL plan's workspace sizing AND execution settings
 * producers (5350304c). Changing only execution can require unavailable 24MB
 * workspace. This API cannot force the scheduler to include the spatial stage. */
int m10v_isp_native_effects_settings(void *dst12,const void *original12,
    const struct m10v_isp_native_effects_config *config);
/* Replace existing Granulation's three LUT allocations IN PLACE immediately
 * before its original submit BL5367b404. Caller verifies the actual callsite
 * and original owner/task. graph is ORIGINAL r5 (0x120 bytes); A/B are original
 * heap buffers, C the original Granulation stack buffer. They stay alive through
 * ORIGINAL wait5367b410/cache5367b424/cleanup5367b418..4ec. No pointer retained.
 * Native graph+5c/+64=A; +6c/+70=B; +60/+68=C; +74..88 lengths256.
 * A/B/C are explicit CALIBRATED endpoint curves (256 signed16 values0..255),
 * not auto-generated approximations. This only changes existing LUT uploads;
 * stock graph topology, descriptors, original event and failure handling stay.
 * Must run before submit has begun reading/uploading tables. Returns0/-1;
 * host returns-3. All input arrays disjoint from graph and stock destinations.
 * The native mask/control arithmetic is not proved by CPU tests. Camera visual
 * calibration must establish effect appearance before enabling this rewrite. */
int m10v_isp_native_effects_grain_tables_owned(void *graph,
    const int16_t a[256],const int16_t b[256],const int16_t c[256]);
#endif
