/* Still-JPEG bridge for the original GR III 2.10 recipe topology.
 * The original encoder call is chained separately by an ARM trampoline.
 * CFA is checked as a protected interval and is never read or written.
 */
#include "m10v_library.h"
typedef void *(*allocate_fn)(uint32_t);
typedef void (*free_fn)(void *);
typedef void (*cache_fn)(void *, uint32_t);
typedef uint32_t (*root_fn)(void);
typedef uint32_t (*get_fn)(uint32_t);
typedef int (*clock_fn)(uint32_t, void *);
static int ram(uint32_t p, uint32_t size) {
    return !(p & 3) && p >= 0x55000000u && p < 0x80000000u && size <= 0x80000000u - p;
}
static int raw_ram(uint32_t p, uint32_t size) {
    return ram(p, size) || (!(p & 3) && p >= 0xa0000000u && p < 0xe0000000u && size <= 0xe0000000u - p);
}
static int overlap(uint32_t a, uint32_t an, uint32_t b, uint32_t bn) {
    return a < b + bn && b < a + an;
}
int m10v_capture_library(uint32_t context) {
    if (!ram(context, 0x60) || context < 0x550009b8u) return -3;
    uint32_t recipe = context - 0x9b8u;
    if (!ram(recipe, 0x44cc)) return -3;
    const uint32_t *ctx = (const uint32_t *)(uintptr_t)context;
    uint32_t sequence_mode = *(const uint32_t *)(uintptr_t)(recipe + 0x18u);
    if (sequence_mode != 0 && sequence_mode != 1 && sequence_mode != 5 && sequence_mode != 6 &&
        sequence_mode != 7 && sequence_mode != 8 && sequence_mode != 12) return -4;
    if (ctx[0] != 0x53d0fbe0u || ctx[0x30 / 4] != recipe + 0x1a8u ||
        ctx[0x3c / 4] != recipe + 0xb0u || ctx[0x48 / 4] != recipe + 0x110u ||
        ctx[0x4c / 4] != recipe + 0x130u ||
        ctx[0x34 / 4] != *(const uint32_t *)(uintptr_t)(recipe + 0x44c8u) ||
        ctx[0x38 / 4] != *(const uint32_t *)(uintptr_t)(recipe + 0x5cu)) return -3;
    uint32_t request = ctx[0x38 / 4], shooting = ctx[0x34 / 4], descriptor = ctx[0x3c / 4], jpeg = ctx[0x4c / 4];
    if (!ram(request, 14) || !ram(shooting, 0x797) || !ram(descriptor, 32) || !ram(jpeg, 17) ||
        *(const uint32_t *)(uintptr_t)request != 0x53d0fe60u) return -3;
    const uint8_t *req = (const uint8_t *)(uintptr_t)request;
    if (req[12] != 1 || req[13] > 1 || ((const uint8_t *)(uintptr_t)jpeg)[16] != 1) return -4;
    uint32_t tone = ((const uint8_t *)(uintptr_t)shooting)[0x77c], slot = 5;
    static const uint8_t tones[5] = {12,18,19,20,21};
    for (uint32_t i = 0; i < 5; ++i) if (tones[i] == tone) slot = i;
    if (slot == 5) return -4;
    const uint32_t *desc = (const uint32_t *)(uintptr_t)descriptor;
    const uint16_t *dims = (const uint16_t *)(uintptr_t)(descriptor + 16);
    uint32_t width = dims[0], height = dims[1], stride = dims[2], allocated = dims[3];
    if (((const uint8_t *)desc)[0] != 1 || width < 2 || width > 6144 || (width & 1) ||
        !height || height > 4096 || stride < width || stride > 16384 || (stride & 1) ||
        allocated < height || allocated > 4096 || desc[3] || dims[4] || dims[5] ||
        ((const uint8_t *)desc)[0x1c] != 2) return -3;
    uint32_t bytes = stride * allocated;
    if (!ram(desc[1], bytes) || !ram(desc[2], bytes) || overlap(desc[1], bytes, desc[2], bytes)) return -3;
    uint32_t raw_source = *(const uint32_t *)(uintptr_t)(recipe + 0x60u);
    uint32_t raw_dims = *(const uint32_t *)(uintptr_t)(recipe + 0x230u);
    if (!ram(raw_dims, 4)) return -3;
    uint32_t raw_width = ((const uint16_t *)(uintptr_t)raw_dims)[0];
    uint32_t raw_height = ((const uint16_t *)(uintptr_t)raw_dims)[1];
    if (!raw_width || raw_width > 8192 || !raw_height || raw_height > 8192) return -3;
    uint32_t raw_bytes = 2 * raw_width * raw_height;
    if (!raw_ram(raw_source, raw_bytes)) return -3;
    uint32_t planes[2] = {desc[1], desc[2]};
    for (uint32_t i = 0; i < 2; ++i)
        if (overlap(planes[i], bytes, raw_source, raw_bytes) || overlap(planes[i], bytes, recipe, 0x44cc) ||
            overlap(planes[i], bytes, request, 0x3c) || overlap(planes[i], bytes, shooting, 0x797) ||
            overlap(planes[i], bytes, raw_dims, 4)) return -3;
    const uint32_t *preview = (const uint32_t *)(uintptr_t)(recipe + 0x110u);
    const uint16_t *pd = (const uint16_t *)(uintptr_t)(recipe + 0x120u);
    uint32_t pf = *(const uint8_t *)preview;
    if ((pf != 1 && pf != 2) || !pd[2] || pd[2] > 16384 || !pd[3] || pd[3] > 4096 ||
        preview[3] || ((const uint8_t *)preview)[0x1c] != 2) return -3;
    uint32_t preview_bytes = (uint32_t)pd[2] * pd[3];
    uint32_t preview_chroma_bytes = pf == 1 ? preview_bytes : preview_bytes >> 1;
    if (!ram(preview[1], preview_bytes) || !ram(preview[2], preview_chroma_bytes)) return -3;
    m10v_library_state state;
    if (m10v_camera_library_load(&state) < 0) return -5;
    uint32_t time[3] = {0,0,0};
    uint32_t seed = state.sequence ^ planes[0];
    if (state.stamp || state.slots[slot].grain) {
        uint32_t root = ((root_fn)0x5320ad88u)();
        uint32_t service = ((get_fn)0x5320b97cu)(root);
        if (!ram(service, 0x1a0) || !((clock_fn)0x532b36ccu)(service, time)) return -7;
        const m10v_library_date *date = (const m10v_library_date *)time;
        seed ^= ((uint32_t)date->year << 16) ^ ((uint32_t)date->month << 8) ^ date->day ^
                ((uint32_t)date->hour << 24) ^ ((uint32_t)date->minute << 16) ^
                ((uint32_t)((const uint8_t *)time)[6] << 8);
    }
    uint8_t *scratch = (uint8_t *)0; uint32_t scratch_bytes = 0;
    uint32_t use_halo=state.slots[slot].film==33&&state.slots[slot].halo_profile&&state.slots[slot].halo_gain;
    if (state.slots[slot].soft || use_halo) {
        uint32_t step = 1, shift = 0;
        while (((width + step - 1) >> shift) > 384 || ((height + step - 1) >> shift) > 256) { step <<= 1; ++shift; }
        scratch_bytes = ((use_halo ? 6 : 2) * ((width + step - 1) >> shift) * ((height + step - 1) >> shift) + 3) & ~3u;
        scratch = ((allocate_fn)0x536af2a8u)(scratch_bytes);
        uint32_t address = (uint32_t)(uintptr_t)scratch;
        if (!ram(address, scratch_bytes)) return -6;
        if (overlap(address, scratch_bytes, planes[0], bytes) || overlap(address, scratch_bytes, planes[1], bytes) ||
            overlap(address, scratch_bytes, raw_source, raw_bytes) || overlap(address, scratch_bytes, recipe, 0x44cc) ||
            overlap(address, scratch_bytes, request, 0x3c) || overlap(address, scratch_bytes, shooting, 0x797) ||
            overlap(address, scratch_bytes, raw_dims, 4) || overlap(address, scratch_bytes, preview[1], preview_bytes) ||
            overlap(address, scratch_bytes, preview[2], preview_chroma_bytes)) {
            ((free_fn)0x536af2e4u)(scratch); return -6;
        }
    }
    m10v_library_image image = {(uint8_t *)(uintptr_t)planes[0], (uint8_t *)(uintptr_t)planes[1],
                                bytes, bytes, width, height, stride};
    uint32_t touched = (height - 1) * stride + width;
    ((cache_fn)0x5383c8a8u)(image.y, touched); ((cache_fn)0x5383c8a8u)(image.chroma, touched);
    int result = m10v_library_render(&image, &state, slot, (const m10v_library_date *)time,
                                     seed, scratch, scratch_bytes);
    if (!result) { ((cache_fn)0x5383c8a8u)(image.y, touched); ((cache_fn)0x5383c8a8u)(image.chroma, touched); }
    if (scratch) ((free_fn)0x536af2e4u)(scratch);
    return result;
}
