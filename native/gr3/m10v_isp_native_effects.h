#ifndef M10V_ISP_NATIVE_EFFECTS_H
#define M10V_ISP_NATIVE_EFFECTS_H
#include <stdint.h>
/* GR III 2.10 SHA256 8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67.
 * Borrow RAM already owned by the stock spatial-stage task. This module does
 * not allocate, create controls, submit, wait, release, reset, or access MMIO.
 * No capture hook is installed. No hardware visual calibration is claimed.
 * The stock graph addressed below affects Y only. Chroma, colored halation,
 * leak tint, and the remaining custom effects MUST retain their existing
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
/* Expand a caller-calibrated small luma field into the ORIGINAL grain workspace,
 * blending existing ORIGINAL RNG bytes: noise_mix255 leaves original noise;
 * noise_mix0 selects the spatial field. Padded bytes remain original noise.
 * field occupies field_stride*field_height bytes, disjoint from entire output.
 * Input/output are raw8 fields; they are NOT RGB or a claim of IIP blend math.
 * Full original image width/height admitted (<=6144x4096); no photo downsample.
 * Call ONLY after original RNG BL5367ae14 returns, BEFORE original cache clean
 * BL5367ae24. At this boundary r0/r1 of displaced RNG are workspace/byte count;
 * original Granulation fp-64c/-644 store width/height, fp-650 aligned stride.
 * The owner provides immutable field storage for this call. No global binding.
 * Returns 0/-1; failed preflight leaves entire original workspace unchanged. */
int m10v_isp_native_effects_field(uint8_t *noise,uint32_t noise_bytes,
    uint32_t width,uint32_t height,uint32_t stride,const uint8_t *field,
    uint32_t field_width,uint32_t field_height,uint32_t field_stride,
    uint32_t noise_mix);
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
/* Grain SIZE adapter, distinct from the native amplitude setting. Size0 is
 * byte-identical original RNG. Size1/2 correlate the ORIGINAL full-size random
 * plane with causal separable2/3-tap box FIRs and an explicit mid-CDF LUT that
 * restores its uniform8 marginal/variance in the interior. Replicated leading
 * edges have a different marginal for first1/2 pixels/rows. No photo pixels or
 * image dimensions change. Padding is untouched. Scalar reference uses128B fixed history. Define
 * M10V_NATIVE_NOISE_ONLY to export only this API; M10V_NOISE_NEON selects
 * the exact reverse-traversal16-wide implementation with16B lane scratch.
 * Compile the latter alone with -mfpu=neon -mfloat-abi=softfp -O2; caller
 * integer ABI stays identical and d8-d15 are preserved. No allocator, shared
 * state or IIP call.
 * Original RNG must finish first; call before its original cache clean at
 * 5367ae24. Size is the per-recipe grain_size0/1/2, NEVER strength-1.
 * Returns0/-1; validates entire geometry before writing. These are calibrated
 * native creative sizes, not the old CPU grain hash. Camera output validation
 * is required because actual IIP LUT/Blend amplitude is a separate contract. */
int m10v_isp_native_effects_noise_shape(uint8_t *noise,uint32_t noise_bytes,
    uint32_t width,uint32_t height,uint32_t stride,uint32_t size);
#endif
