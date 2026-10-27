#ifndef M10V_TEXTURE_ACCEL_H
#define M10V_TEXTURE_ACCEL_H
#include <stdint.h>
/* Exactly eight full-color YUV422 pixels. LUT is3375 interleaved RGB triples.
 * Legacy texture fields are ignored. Disjoint buffers, LUT and params required.
 * ARM caller establishes task NEON ownership. No ISP operation or allocation.
 * Invalid scalar params return-1 before writes. LUT/planes must be valid RAM. */
typedef struct {
 uint8_t light[8];
 uint32_t grain_q8;
 uint32_t hashes[8];
 int32_t noise[8];
} m10v_texture_block_params;
int m10v_texture_block8(uint8_t *y,uint8_t *uv,const uint8_t *lut,const m10v_texture_block_params *p);
/* Optional caller-owned 64KiB cache, aligned4, reset when capture or LUT changes.
 * Full RGB24 keys identify the exact LUT color output.
 * No shared state. Returns observed hits0..8 or-1. Null cache is uncached SIMD.
 * All-four-lane hits skip interpolation; partial hits recompute the four lanes.
 * Cache/planes/params/LUT must be disjoint with lifetimes spanning the call. */
int m10v_texture_block8_cached(uint8_t *y,uint8_t *uv,const uint8_t *lut,const m10v_texture_block_params *p,void *cache);
/* Same contract as cached RGB above; LUT contains 3375 neutral single-byte nodes. */
int m10v_texture_mono_block8_cached(uint8_t *y,uint8_t *uv,const uint8_t *lut,const m10v_texture_block_params *p,void *cache);
/* Retired ABI entry point: validates pointers and otherwise leaves planes unchanged. */
int m10v_texture_effects_block8(uint8_t *y,uint8_t *uv,const m10v_texture_block_params *p,uint32_t chroma_enabled);
#endif
