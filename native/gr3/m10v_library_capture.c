/* Still-JPEG bridge for the original GR III 2.10 recipe topology.
 * The original encoder call is chained separately by an ARM trampoline.
 * CFA is checked as a protected interval and is never read or written.
 */
#include "m10v_library.h"
#include "m10v_debug.h"
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
/* The UI date service can be unavailable in the capture thread. Never let
 * an unavailable/invalid date suppress unrelated image processing. */
static int capture_date_valid(const uint32_t time[3]) {
    const m10v_library_date *d = (const m10v_library_date *)time;
    static const uint8_t days[12] = {31,28,31,30,31,30,31,31,30,31,30,31};
    if (d->year < 1980 || d->year > 2199 || !d->month || d->month > 12 ||
        !d->day || d->hour > 23 || d->minute > 59 || ((const uint8_t *)time)[6] > 59) return 0;
    uint32_t max = days[d->month - 1];
    if (d->month == 2 && d->year % 4 == 0 && (d->year % 100 != 0 || d->year % 400 == 0)) ++max;
    return d->day <= max;
}
static void skip_capture_stamp(m10v_library_state *state) {
    /* This is a stack copy, never stored. Keep the serialized-state CRC valid
     * for render's validation without changing the persisted configuration. */
    state->stamp = 0;
    uint32_t crc = 0xffffffffu;
    const uint8_t *bytes = (const uint8_t *)state;
    for (uint32_t i = 0; i < sizeof(*state) - sizeof(state->crc); ++i) {
        crc ^= bytes[i];
        for (uint32_t bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    state->crc = ~crc;
}
#if M10V_DEBUG_MODE
static int capture_library_impl(uint32_t context) {
#else
int m10v_capture_library(uint32_t context) {
#endif
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
    if (!ram(request, 14) || !ram(shooting, 0x94c) || !ram(descriptor, 32) || !ram(jpeg, 17) ||
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
            overlap(planes[i], bytes, request, 0x3c) || overlap(planes[i], bytes, shooting, 0x94c) ||
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
    int settings_source=m10v_camera_library_load(&state);
    if (settings_source < 0) return -5;
    M10V_LOG(113,slot,(uint32_t)settings_source,state.sequence,3);
    uint32_t time[3] = {0,0,0};
    uint32_t seed = state.sequence ^ planes[0];
    if (state.stamp || state.slots[slot].grain || state.effects[slot].leak_variation) {
        /* Official producer 0x534322d8/0x534fa22c writes this capture
         * metadata date. +0x948 is weekday, not hour. Prefer exposure metadata
         * over the UI cache (which may be unavailable or from a later time). */
        const uint8_t *shot = (const uint8_t *)(uintptr_t)shooting;
        m10v_library_date *date = (m10v_library_date *)time;
        date->year = *(const uint16_t *)(shot + 0x944);
        date->month = shot[0x946]; date->day = shot[0x947];
        date->hour = shot[0x949]; date->minute = shot[0x94a];
        ((uint8_t *)time)[6] = shot[0x94b];
        uint32_t clock_status = 4, source = shooting + 0x944;
        /* 4 capture date, 1 UI date, 2 UI unavailable, 3 invalid date. */
        if (!capture_date_valid(time)) {
            uint32_t root = ((root_fn)0x5320ad88u)();
            source = ((get_fn)0x5320b97cu)(root);
            clock_status = 2;
            if (ram(source, 0x3cc) && ((clock_fn)0x532b36ccu)(source, time))
                clock_status = capture_date_valid(time) ? 1 : 3;
        }
        M10V_LOG(120,context,clock_status,state.stamp,source);
        if (clock_status != 1 && clock_status != 4) {
            skip_capture_stamp(&state);
        } else {
            const m10v_library_date *date = (const m10v_library_date *)time;
            seed ^= ((uint32_t)date->year << 16) ^ ((uint32_t)date->month << 8) ^ date->day ^
                    ((uint32_t)date->hour << 24) ^ ((uint32_t)date->minute << 16) ^
                    ((uint32_t)((const uint8_t *)time)[6] << 8);
        }
    }
    if(state.slots[slot].film==66||state.effects[slot].leak_variation){
        /* Content entropy changes with captured sensor noise; identical frames
         * can retain the same seed. No unverified timer/MMIO calls. */
        for(uint32_t yy=0;yy<height;yy+=height/16+1)for(uint32_t xx=0;xx<width;xx+=width/16+1){seed^=((const uint8_t *)(uintptr_t)planes[0])[yy*stride+xx];seed*=16777619u;}
        const uint8_t *e=(const uint8_t *)&state.effects[slot];(void)e;
        M10V_LOG(130,context,state.slots[slot].film,seed,(uint32_t)e[0]|((uint32_t)e[1]<<8)|((uint32_t)e[2]<<16)|((uint32_t)e[3]<<24));
        M10V_LOG(131,context,e[4],state.slots[slot].grain,state.slots[slot].soft);
    }
    uint8_t *scratch = (uint8_t *)0; uint32_t scratch_bytes = 0;
    uint32_t use_halo=state.slots[slot].film==33&&state.slots[slot].halo_gain;
    if (state.slots[slot].soft || use_halo) {
        uint32_t step = 1, shift = 0;
        while (((width + step - 1) >> shift) > 384 || ((height + step - 1) >> shift) > 256) { step <<= 1; ++shift; }
        scratch_bytes = ((state.slots[slot].film == 33 ? 6 : 2) * ((width + step - 1) >> shift) * ((height + step - 1) >> shift) + 3) & ~3u;
        scratch = ((allocate_fn)0x536af2a8u)(scratch_bytes);
        uint32_t address = (uint32_t)(uintptr_t)scratch;
        if (!ram(address, scratch_bytes)) return -6;
        if (overlap(address, scratch_bytes, planes[0], bytes) || overlap(address, scratch_bytes, planes[1], bytes) ||
            overlap(address, scratch_bytes, raw_source, raw_bytes) || overlap(address, scratch_bytes, recipe, 0x44cc) ||
            overlap(address, scratch_bytes, request, 0x3c) || overlap(address, scratch_bytes, shooting, 0x94c) ||
            overlap(address, scratch_bytes, raw_dims, 4) || overlap(address, scratch_bytes, preview[1], preview_bytes) ||
            overlap(address, scratch_bytes, preview[2], preview_chroma_bytes)) {
            ((free_fn)0x536af2e4u)(scratch); return -6;
        }
    }
    m10v_library_image image = {(uint8_t *)(uintptr_t)planes[0], (uint8_t *)(uintptr_t)planes[1],
                                bytes, bytes, width, height, stride};
    uint32_t touched = (height - 1) * stride + width;
    ((cache_fn)0x5383c8a8u)(image.y, touched); ((cache_fn)0x5383c8a8u)(image.chroma, touched);
    M10V_LOG(110,context,slot,state.slots[slot].film,(width<<16)|height);
    M10V_LOG(112,slot,(uint32_t)state.slots[slot].halo_gain|((uint32_t)state.slots[slot].halo_spread<<4)|
        ((uint32_t)state.slots[slot].halo_threshold<<8)|((uint32_t)state.slots[slot].grain<<12)|((uint32_t)state.slots[slot].soft<<16),state.sequence,3);
#if M10V_DEBUG_MODE
    if(state.slots[slot].film==33 && state.slots[slot].halo_gain) {
        uint32_t peak=0,active=0,gate=176+8u*state.slots[slot].halo_threshold;
        for(uint32_t row=0;row<height;++row)for(uint32_t x=0;x<width;++x) {
            uint32_t light=image.y[row*stride+x];
            int red=(int)light+((359*((int)image.chroma[row*stride+(x&~1u)+1]-128))>>8)-24;
            if(red>255)red=255;if(red>(int)light)light=(uint32_t)red;
            if(light>peak)peak=light;if(light>gate)++active;
        }
        uint32_t excess=peak>gate?peak-gate:0;
        M10V_LOG(114,excess*excess*8,active,width*height,gate);
    }
#endif
    int result = m10v_library_render(&image, &state, slot, (const m10v_library_date *)time,
                                     seed, scratch, scratch_bytes);
    M10V_LOG(111,context,(uint32_t)result,(uint32_t)state.slots[slot].halo_gain|((uint32_t)state.slots[slot].halo_spread<<4)|((uint32_t)state.slots[slot].halo_threshold<<8)|((uint32_t)state.slots[slot].halo_profile<<12),scratch_bytes);
    if (!result) { ((cache_fn)0x5383c8a8u)(image.y, touched); ((cache_fn)0x5383c8a8u)(image.chroma, touched); }
    if (scratch) ((free_fn)0x536af2e4u)(scratch);
    return result;
}
#if M10V_DEBUG_MODE
int m10v_capture_library(uint32_t context) {
    M10V_LOG(100,context,0,0,0);
    int result=capture_library_impl(context);
    M10V_LOG(101,context,(uint32_t)result,0,0);return result;
}
#endif
