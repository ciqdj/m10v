/* GR III Street 2.10 native AppData ABI adapter, independently traced from
 * the official firmware. Stock FS services own their header/CRC/backup path.
 * M10V's two private journal names never overwrite an APData setting record.
 */
#include "m10v_library.h"
#include <stddef.h>

typedef uint32_t (*manager_fn)(void);
typedef int (*read_fn)(uint32_t, const char *, uint32_t, void *);
typedef int (*write_fn)(uint32_t, const char *, uint32_t, const void *);
static const char state_names[2][12] = {"M10V3A.bin", "M10V3B.bin"};

static int ram(const void *ptr, uint32_t size) {
    uintptr_t p = (uintptr_t)ptr;
    return !(p & 3) && p >= 0x55000000u && p < 0x80000000u && size <= 0x80000000u - p;
}
static uint32_t filesystem(void) {
    uint32_t manager = ((manager_fn)0x53828014u)();
    if (!ram((void *)(uintptr_t)manager, 12)) return 0;
    uint32_t appdata = ((const uint32_t *)(uintptr_t)manager)[2];
    if (!ram((void *)(uintptr_t)appdata, 4)) return 0;
    uint32_t fs = *(const uint32_t *)(uintptr_t)appdata;
    if (!ram((void *)(uintptr_t)fs, 0x24) || !((const uint8_t *)(uintptr_t)fs)[0x20]) return 0;
    return fs;
}
static void copy(m10v_library_state *dst, const m10v_library_state *src) {
    for (uint32_t i = 0; i < sizeof(*src); ++i) ((uint8_t *)dst)[i] = ((const uint8_t *)src)[i];
}
static int store(void *context, const m10v_library_state *next) {
    uint32_t fs = (uint32_t)(uintptr_t)context;
    const char *name = state_names[next->sequence & 1];
    m10v_library_state readback;
    for (uint32_t i = 0; i < sizeof(readback); ++i) ((uint8_t *)&readback)[i] = 0;
    if (!((write_fn)0x53825fa8u)(fs, name, sizeof(*next), next) ||
        !((read_fn)0x53825648u)(fs, name, sizeof(readback), &readback) ||
        !m10v_library_valid(&readback)) return -1;
    for (uint32_t i = 0; i < sizeof(readback); ++i)
        if (((const uint8_t *)&readback)[i] != ((const uint8_t *)next)[i]) return -1;
    return 0;
}
static uint32_t little32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int legacy_valid(const uint8_t *p){
    if(little32(p)!=0x5630314du||p[4]!=1||p[5]||p[6]!=44||p[7]||p[32]>2||p[33]>3||p[34]>3||p[35]>3||little32(p+36))return 0;
    for(uint32_t i=0;i<5;++i){const uint8_t *v=p+12+4*i;if(!v[0]||v[0]>33||v[1]||v[2]>3||v[3]>3)return 0;}
    uint32_t crc=0xffffffffu;for(uint32_t i=0;i<40;++i){crc^=p[i];for(uint32_t bit=0;bit<8;++bit)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}
    return ~crc==little32(p+40);
}
static int migrate(uint32_t fs,m10v_library_state *state){
    static const char names[2][12]={"M10V0.bin","M10V1.bin"};
    uint8_t records[2][44];int good[2];
    for(uint32_t i=0;i<88;++i)((uint8_t *)records)[i]=0;
    for(uint32_t i=0;i<2;++i)good[i]=((read_fn)0x53825648u)(fs,names[i],44,records[i])&&legacy_valid(records[i]);
    if(!good[0]&&!good[1])return 1;
    uint32_t selected=!good[0]||(good[1]&&little32(records[1]+8)>little32(records[0]+8));const uint8_t *old=records[selected];
    state->sequence=little32(old+8);
    for(uint32_t i=0;i<5;++i){state->slots[i].film=old[12+4*i];state->slots[i].grain=old[14+4*i];state->slots[i].soft=old[15+4*i];}
    state->stamp=old[32];state->format=old[33];state->corner=old[34];state->color=old[35];
    uint32_t crc=0xffffffffu;const uint8_t *bytes=(const uint8_t *)state;
    for(uint32_t i=0;i<60;++i){crc^=bytes[i];for(uint32_t bit=0;bit<8;++bit)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}state->crc=~crc;
    return m10v_library_valid(state)?3:-1;
}
/* New journal namespace isolates the new exposure model from saved old
 * aggressive defaults. Old files remain intact for firmware rollback. */
static int migrate_energy(uint32_t fs,m10v_library_state *state) {
    static const char old_names[2][12]={"M10V2A.bin","M10V2B.bin"};
    m10v_library_state old[2];int good[2];
    for(uint32_t i=0;i<sizeof(old);++i)((uint8_t *)old)[i]=0;
    for(uint32_t i=0;i<2;++i)good[i]=((read_fn)0x53825648u)(fs,old_names[i],sizeof(*state),&old[i])&&m10v_library_valid(&old[i]);
    if(!good[0]&&!good[1])return migrate(fs,state);
    uint32_t selected=!good[0]||(good[1]&&old[1].sequence>old[0].sequence);
    copy(state,&old[selected]);
    for(uint32_t i=0;i<5;++i) {
        m10v_slot *v=&state->slots[i];
        /* New units are not a calibrated mapping of the obsolete multiplier.
         * Preserve explicit off; otherwise reset to documented 3/3/5. */
        v->halo_gain=(v->halo_gain&&v->halo_profile)?3:0;
        v->halo_spread=3;v->halo_threshold=5;v->halo_profile=2;
    }
    uint32_t crc=0xffffffffu;const uint8_t *bytes=(const uint8_t *)state;
    for(uint32_t i=0;i<60;++i){crc^=bytes[i];for(uint32_t bit=0;bit<8;++bit)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}state->crc=~crc;
    return 2;
}
int m10v_camera_library_load(m10v_library_state *state) {
    if (!ram(state, sizeof(*state))) return M10V_LIBRARY_INVALID;
    m10v_library_init(state);
    uint32_t fs = filesystem(); if (!fs) return M10V_LIBRARY_INVALID;
    m10v_library_state candidates[2]; int available[2];
    for (uint32_t i = 0; i < sizeof(candidates); ++i) ((uint8_t *)candidates)[i] = 0;
    for (uint32_t i = 0; i < 2; ++i)
        available[i] = ((read_fn)0x53825648u)(fs, state_names[i], sizeof(*state), &candidates[i]) &&
                       m10v_library_valid(&candidates[i]);
    if (!available[0] && !available[1]) return migrate_energy(fs,state);
    uint32_t selected = !available[0] || (available[1] && candidates[1].sequence > candidates[0].sequence);
    copy(state, &candidates[selected]); return M10V_LIBRARY_OK;
}
int m10v_camera_library_select(m10v_library_state *state, uint32_t slot, uint32_t film) {
    if (!ram(state, sizeof(*state))) return M10V_LIBRARY_INVALID;
    uint32_t fs = filesystem();
    return fs ? m10v_library_select(state, slot, film, store, (void *)(uintptr_t)fs) : M10V_LIBRARY_STORE_FAILED;
}
int m10v_camera_library_texture(m10v_library_state *state, uint32_t slot, uint32_t grain, uint32_t soft) {
    if (!ram(state, sizeof(*state))) return M10V_LIBRARY_INVALID;
    uint32_t fs = filesystem();
    return fs ? m10v_library_texture(state, slot, grain, soft, store, (void *)(uintptr_t)fs) : M10V_LIBRARY_STORE_FAILED;
}
int m10v_camera_library_halation(m10v_library_state *state,uint32_t slot,uint32_t gain,uint32_t spread,uint32_t threshold,uint32_t profile){
    if(!ram(state,sizeof(*state)))return M10V_LIBRARY_INVALID;
    uint32_t fs=filesystem();return fs?m10v_library_halation(state,slot,gain,spread,threshold,profile,store,(void *)(uintptr_t)fs):M10V_LIBRARY_STORE_FAILED;
}
int m10v_camera_library_detail(m10v_library_state *state,uint32_t slot,uint32_t gain,uint32_t spread,uint32_t threshold,uint32_t grain,uint32_t soft){
    if(!ram(state,sizeof(*state)))return M10V_LIBRARY_INVALID;
    uint32_t fs=filesystem();
    return fs?m10v_library_detail(state,slot,gain,spread,threshold,grain,soft,store,(void *)(uintptr_t)fs):M10V_LIBRARY_STORE_FAILED;
}
int m10v_camera_library_stamp(m10v_library_state *state, uint32_t enabled, uint32_t format,
                             uint32_t corner, uint32_t color) {
    if (!ram(state, sizeof(*state))) return M10V_LIBRARY_INVALID;
    uint32_t fs = filesystem();
    return fs ? m10v_library_stamp(state, enabled, format, corner, color, store, (void *)(uintptr_t)fs) : M10V_LIBRARY_STORE_FAILED;
}
