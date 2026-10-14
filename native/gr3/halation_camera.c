/* Exact GR III 2.10 still-recipe bridge. The existing capture trampoline
 * preserves caller state and passes context r4. Hardware execution remains
 * untested; this bridge is for offline-verified experimental candidates.
 */
#include "halation_core.h"
#include "halation_controls.h"
#ifndef M10V_CAMERA_ORDER
#error M10V_CAMERA_ORDER must be supplied explicitly
#endif
#ifndef M10V_CAMERA_TONE
#error M10V_CAMERA_TONE must be supplied explicitly
#endif
#ifndef M10V_CAMERA_STRENGTH
#error M10V_CAMERA_STRENGTH must be supplied explicitly
#endif
#if M10V_CAMERA_ORDER != 1 && M10V_CAMERA_ORDER != 2
#error unsupported software chroma order
#endif
#if M10V_CAMERA_STRENGTH != 1 && M10V_CAMERA_STRENGTH != 2
#error unsupported halation strength
#endif
static inline __attribute__((always_inline)) int ram(uint32_t pointer, uint32_t size) {
    return !(pointer & 3) && pointer >= 0x55000000u && pointer < 0x80000000u &&
           size <= 0x80000000u - pointer;
}
static inline __attribute__((always_inline)) int raw_ram(uint32_t pointer, uint32_t size) {
    /* The stock startup table also maps A0000000..DFFFFFFF as normal
     * read/write identity memory. Real RAW+JPEG capture uses this bank.
     * CFA is only checked as a protected interval, never dereferenced. */
    return ram(pointer,size) || (!(pointer & 3) && pointer >= 0xa0000000u &&
           pointer < 0xe0000000u && size <= 0xe0000000u-pointer);
}
static inline int overlaps(uint32_t a, uint32_t an, uint32_t b, uint32_t bn) {
    return a < b + bn && b < a + an;
}
void m10v_capture_800t(uint32_t context) {
    typedef void *(*allocate_fn)(uint32_t);
    typedef void (*free_fn)(void *);
    typedef void (*cache_fn)(void *, uint32_t);
    typedef int (*core_fn)(const m10v_halo_image *, uint32_t, uint8_t *, uint32_t);
    if (!ram(context, 0x5c) || context < 0x550009b8u) return;
    const uint32_t *ctx = (const uint32_t *)context;
    uint32_t recipe = context - 0x9b8u;
    if (!ram(recipe, 0x44cc)) return;
    uint32_t sequence_mode = *(const uint32_t *)(recipe + 0x18u);
    if (sequence_mode != 0 && sequence_mode != 1 && sequence_mode != 5 && sequence_mode != 6 &&
        sequence_mode != 7 && sequence_mode != 8 && sequence_mode != 12) return;
    if (ctx[0] != 0x53d0fbe0u ||
        ctx[0x30 / 4] != recipe + 0x1a8u || ctx[0x3c / 4] != recipe + 0xb0u ||
        ctx[0x48 / 4] != recipe + 0x110u || ctx[0x4c / 4] != recipe + 0x130u ||
        ctx[0x34 / 4] != *(const uint32_t *)(recipe + 0x44c8u) ||
        ctx[0x38 / 4] != *(const uint32_t *)(recipe + 0x5cu)) return;
    uint32_t request = ctx[0x38 / 4], shooting = ctx[0x34 / 4];
    uint32_t descriptor = ctx[0x3c / 4], jpeg = ctx[0x4c / 4];
    if (!ram(request, 14) || !ram(shooting, 0x785) ||
        !ram(descriptor, 32) || !ram(jpeg, 17) ||
        *(const uint32_t *)request != 0x53d0fe60u) return;
    const uint8_t *req = (const uint8_t *)request;
    if (req[12] != 1 || req[13] > 1 ||
        ((const uint8_t *)shooting)[0x77c] != M10V_CAMERA_TONE ||
        ((const uint8_t *)jpeg)[16] != 1 ||
        ((const uint8_t *)descriptor)[0] != 1) return;
    const uint32_t *desc = (const uint32_t *)descriptor;
    const uint16_t *dims = (const uint16_t *)(descriptor + 16);
    uint32_t width = dims[0], height = dims[1], stride = dims[2], allocated = dims[3];
    if (width < 2 || width > 6144 || (width & 1) || height < 1 || height > 4096 ||
        stride < width || stride > 16384 || (stride & 1) || allocated < height ||
        allocated > 4096 || desc[3] != 0 || dims[4] || dims[5] ||
        ((const uint8_t *)desc)[0x1c] != 2) return;
    uint32_t bytes = stride * allocated;
    if (!ram(desc[1], bytes) || !ram(desc[2], bytes) ||
        overlaps(desc[1], bytes, desc[2], bytes)) return;
    /* Check the declared RAW encoder source even when its record flag is off. */
    uint32_t raw_source = *(const uint32_t *)(recipe + 0x60u);
    uint32_t raw_dims = *(const uint32_t *)(recipe + 0x230u);
    /* Module7's +4/+30 are still zero here: its SetupModuleConfig is after
     * JPEG(module6). Read the established recipe/status CFA source instead of
     * requiring the future RAW encoder config to have already been populated. */
    if (!ram(raw_dims, 4)) return;
    uint32_t raw_width = ((const uint16_t *)raw_dims)[0];
    uint32_t raw_height = ((const uint16_t *)raw_dims)[1];
    if (!raw_width || raw_width > 8192 || !raw_height || raw_height > 8192) return;
    uint32_t raw_bytes = 2 * raw_width * raw_height;
    if (!raw_ram(raw_source, raw_bytes)) return;
    uint32_t control_record=0;
#if M10V_CAMERA_TONE == 18
    control_record=m10v_control_record();
#endif
    uint32_t planes[2] = {desc[1], desc[2]};
#pragma clang loop unroll(disable)
    for (uint32_t plane = 0; plane < 2; ++plane) {
        uint32_t address = planes[plane];
        if (overlaps(address, bytes, raw_source, raw_bytes) ||
            overlaps(address, bytes, recipe, 0x44cc) ||
            overlaps(address, bytes, request, 0x3c) ||
            overlaps(address, bytes, shooting, 0x785) ||
            overlaps(address, bytes, raw_dims, 4) ||
            (control_record && overlaps(address,bytes,control_record,0xb48))) return;
    }
    /* The additional JPEG/DNG preview may share the main pixels. Its appearance
     * can change with this effect; the CFA interval above must remain disjoint. */
    const uint32_t *preview = (const uint32_t *)(recipe + 0x110u);
    const uint16_t *pd = (const uint16_t *)(recipe + 0x120u);
    uint32_t pf = *(const uint8_t *)preview;
    if ((pf != 1 && pf != 2) || !pd[2] || pd[2] > 16384 ||
        !pd[3] || pd[3] > 4096 || preview[3] ||
        ((const uint8_t *)preview)[0x1c] != 2) return;
    uint32_t preview_bytes = (uint32_t)pd[2] * pd[3];
    uint32_t preview_chroma_bytes = pf == 1 ? preview_bytes : preview_bytes >> 1;
    if (!ram(preview[1], preview_bytes) || !ram(preview[2], preview_chroma_bytes)) return;
    m10v_halo_image image = {(uint8_t *)desc[1], (uint8_t *)desc[2], bytes, bytes,
                             width, height, stride, stride, M10V_CAMERA_ORDER};
    uint32_t step = 1, shift = 0;
    while (((width + step - 1) >> shift) > 384 || ((height + step - 1) >> shift) > 256) {
        step <<= 1;
        shift++;
    }
    uint32_t scratch_bytes = (6 * ((width + step - 1) >> shift) * ((height + step - 1) >> shift)+3)&~3u;
    uint8_t *scratch = ((allocate_fn)0x536af2a8u)(scratch_bytes);
    if (!ram((uint32_t)scratch, scratch_bytes)) return;
    uint32_t scratch_start = (uint32_t)scratch;
    if (overlaps(scratch_start, scratch_bytes, planes[0], bytes) ||
        overlaps(scratch_start, scratch_bytes, planes[1], bytes) ||
        overlaps(scratch_start, scratch_bytes, raw_source, raw_bytes) ||
        overlaps(scratch_start, scratch_bytes, recipe, 0x44cc) ||
        overlaps(scratch_start, scratch_bytes, request, 0x3c) ||
        overlaps(scratch_start, scratch_bytes, shooting, 0x785) ||
        overlaps(scratch_start, scratch_bytes, raw_dims, 4) ||
        (control_record && overlaps(scratch_start,scratch_bytes,control_record,0xb48)) ||
        overlaps(scratch_start, scratch_bytes, preview[1], preview_bytes) ||
        overlaps(scratch_start, scratch_bytes, preview[2], preview_chroma_bytes)) {
        ((free_fn)0x536af2e4u)(scratch);
        return;
    }
    uint32_t touched = (height - 1) * stride + width;
    ((cache_fn)0x5383c8a8u)(image.y, touched);
    ((cache_fn)0x5383c8a8u)(image.chroma, touched);
    uint32_t control=M10V_CAMERA_STRENGTH;
#if M10V_CAMERA_TONE == 18
    control=m10v_camera_controls((const uint8_t *)shooting,M10V_CAMERA_STRENGTH);
#endif
    int result = ((core_fn)0x540bb800u)(&image, control, scratch, scratch_bytes);
    if (result == M10V_HALO_OK) {
        ((cache_fn)0x5383c8a8u)(image.y, touched);
        ((cache_fn)0x5383c8a8u)(image.chroma, touched);
    }
    ((free_fn)0x536af2e4u)(scratch);
}
