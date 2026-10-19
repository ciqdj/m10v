/* GR III Street 2.10 native AppData ABI adapter, independently traced from
 * the official firmware. Stock FS services own their header/CRC/backup path.
 * M10V's two private journal names never overwrite an APData setting record.
 */
#include "m10v_library.h"
#include <stddef.h>

typedef uint32_t (*manager_fn)(void);
typedef int (*read_fn)(uint32_t, const char *, uint32_t, void *);
typedef int (*write_fn)(uint32_t, const char *, uint32_t, const void *);
static const char state_names[2][12] = {"M10V5A.bin", "M10V5B.bin"};

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
#ifndef M10V_LIVE_COLOR
#define M10V_LIVE_COLOR 0
#endif
#if M10V_LIVE_COLOR
#define PREVIEW_OFFSET 0x193cu
#define PREVIEW_BYTES 128u
#define PREVIEW_MAGIC 0x3856504du
typedef struct {uint32_t magic,version; m10v_library_state state;} preview_cache;
_Static_assert(sizeof(preview_cache)<=PREVIEW_BYTES,"preview owner capacity");
static preview_cache *preview_owner(void){
    /* Original5316f350 singleton guard,5316fce0 factory+74 TopMenu owner.
     * Read only: never initialize a UI singleton or allocate from LiveView. */
    if(!(*(const volatile uint32_t *)0x55063910u&1u))return 0;
    uint32_t owner=*(const volatile uint32_t *)(0x55063914u+0x74u);
    if(!ram((const void *)(uintptr_t)owner,PREVIEW_OFFSET+PREVIEW_BYTES))return 0;
    preview_cache *p=(preview_cache *)(uintptr_t)(owner+PREVIEW_OFFSET);
    return p->magic==PREVIEW_MAGIC?p:0;
}
static void publish_preview(preview_cache *p,const m10v_library_state *s){
    if(!p||!m10v_library_valid(s))return;
    uint32_t v=__atomic_load_n(&p->version,__ATOMIC_ACQUIRE);
    if((v&1u)||!__atomic_compare_exchange_n(&p->version,&v,v+1,0,__ATOMIC_ACQ_REL,__ATOMIC_RELAXED))return;
    copy(&p->state,s);__atomic_store_n(&p->version,v+2,__ATOMIC_RELEASE);
}
#endif
int m10v_camera_library_preview(m10v_library_state *out){
#if M10V_LIVE_COLOR
    preview_cache *p=preview_owner();if(!p||!ram(out,sizeof(*out)))return 0;
    uint32_t before=__atomic_load_n(&p->version,__ATOMIC_ACQUIRE);
    if(!before||(before&1u))return 0;
    copy(out,&p->state);__atomic_thread_fence(__ATOMIC_ACQUIRE);
    return p->magic==PREVIEW_MAGIC&&before==__atomic_load_n(&p->version,__ATOMIC_RELAXED)&&m10v_library_valid(out);
#else
    (void)out;return 0;
#endif
}
void m10v_camera_library_preview_init(uint32_t owner){
#if M10V_LIVE_COLOR
    if(!ram((void *)(uintptr_t)owner,PREVIEW_OFFSET+PREVIEW_BYTES))return;
    preview_cache *p=(preview_cache *)(uintptr_t)(owner+PREVIEW_OFFSET);
    p->magic=0;p->version=0;p->magic=PREVIEW_MAGIC;
    /* Constructor is allocation-only: storage may re-enter the factory.
     * Ready/load publishes after the original factory has installed owner+74. */
#else
    (void)owner;
#endif
}
void m10v_camera_library_preview_clear(uint32_t owner){
#if M10V_LIVE_COLOR
    if(ram((void *)(uintptr_t)owner,PREVIEW_OFFSET+PREVIEW_BYTES))
        ((preview_cache *)(uintptr_t)(owner+PREVIEW_OFFSET))->magic=0;
#else
    (void)owner;
#endif
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
#if M10V_LIVE_COLOR
    publish_preview(preview_owner(),next);
#endif
    return 0;
}
static uint32_t little32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int legacy_valid(const uint8_t *p){
    if(little32(p)!=0x5630314du||p[4]!=1||p[5]||p[6]!=44||p[7]||p[32]>2||p[33]>3||p[34]>3||p[35]>3||little32(p+36))return 0;
    for(uint32_t i=0;i<5;++i){const uint8_t *v=p+12+4*i;if(!v[0]||v[0]>33||v[1]||v[2]>3||v[3]>3)return 0;}
    uint32_t crc=0xffffffffu;for(uint32_t i=0;i<40;++i){crc^=p[i];for(uint32_t bit=0;bit<8;++bit)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}
    return ~crc==little32(p+40);
}
static void reset_migrated_effects(m10v_library_state *state){
    for(uint32_t i=0;i<5;i++){m10v_film_effects e={1,0,0,4,0,0,{0,0}};state->effects[i]=e;}
}
static int migrate_v2(uint32_t fs,m10v_library_state *state,uint32_t energy){
    static const char energy_names[2][12]={"M10V3A.bin","M10V3B.bin"};
    static const char old_names[2][12]={"M10V2A.bin","M10V2B.bin"};
    const char (*names)[12]=energy?energy_names:old_names;
    uint8_t records[2][64];int good[2]={0,0};
    for(uint32_t k=0;k<2;k++){
        for(uint32_t i=0;i<64;i++)records[k][i]=0;
        uint8_t *p=records[k];
        if(!((read_fn)0x53825648u)(fs,names[k],64,p))continue;
        if(little32(p)!=0x5630314du||p[4]!=2||p[5]||p[6]!=64||p[7]||p[52]>2||p[53]>3||p[54]>3||p[55]>3||little32(p+56))continue;
        int valid=1;
        for(uint32_t i=0;i<5;i++){uint8_t *v=p+12+i*8;
            if(!v[0]||v[0]>65||v[1]||v[2]>3||v[3]>3||v[4]>8||v[5]>8||v[6]>8||v[7]>3)valid=0;}
        uint32_t crc=0xffffffffu;for(uint32_t i=0;i<60;i++){crc^=p[i];for(uint32_t bit=0;bit<8;bit++)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}
        good[k]=valid&&~crc==little32(p+60);
    }
    if(!good[0]&&!good[1])return 1;
    uint32_t index=!good[0]||(good[1]&&little32(records[1]+8)>little32(records[0]+8));
    reset_migrated_effects(state);
    for(uint32_t i=8;i<56;i++)((uint8_t *)state)[i]=records[index][i];
    if(!energy)for(uint32_t i=0;i<5;i++){m10v_slot *v=&state->slots[i];v->halo_gain=(v->halo_gain&&v->halo_profile)?3:0;v->halo_spread=3;v->halo_threshold=5;v->halo_profile=2;}
    uint32_t crc=0xffffffffu;for(uint32_t i=0;i<100;i++){crc^=((uint8_t *)state)[i];for(uint32_t bit=0;bit<8;bit++)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}state->crc=~crc;
    return m10v_library_valid(state)?2:-1;
}
static int migrate(uint32_t fs,m10v_library_state *state){
    static const char names[2][12]={"M10V0.bin","M10V1.bin"};
    uint8_t records[2][44];int good[2];
    for(uint32_t i=0;i<88;++i)((uint8_t *)records)[i]=0;
    for(uint32_t i=0;i<2;++i)good[i]=((read_fn)0x53825648u)(fs,names[i],44,records[i])&&legacy_valid(records[i]);
    if(!good[0]&&!good[1])return 1;
    uint32_t selected=!good[0]||(good[1]&&little32(records[1]+8)>little32(records[0]+8));const uint8_t *old=records[selected];
    reset_migrated_effects(state);
    state->sequence=little32(old+8);
    for(uint32_t i=0;i<5;++i){state->slots[i].film=old[12+4*i];state->slots[i].grain=old[14+4*i];state->slots[i].soft=old[15+4*i];}
    state->stamp=old[32];state->format=old[33];state->corner=old[34];state->color=old[35];
    uint32_t crc=0xffffffffu;const uint8_t *bytes=(const uint8_t *)state;
    for(uint32_t i=0;i<100;++i){crc^=bytes[i];for(uint32_t bit=0;bit<8;++bit)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}state->crc=~crc;
    return m10v_library_valid(state)?3:-1;
}
/* Published texture schema3: verify old CRC before converting the header.
 * The new exposure byte was reserved and must be zero in every old slot. */
static uint32_t texture_crc(const m10v_library_state *state){
    uint32_t crc=0xffffffffu;for(uint32_t i=0;i<100;i++){crc^=((const uint8_t *)state)[i];for(uint32_t b=0;b<8;b++)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}return ~crc;
}
static int read_texture_v3(uint32_t fs,const char *name,m10v_library_state *state){
    if(!((read_fn)0x53825648u)(fs,name,sizeof(*state),state)||state->version!=3||state->size!=104||state->crc!=texture_crc(state))return 0;
    for(uint32_t i=0;i<5;i++)if(state->slots[i].film>66||state->effects[i].film_exposure)return 0;
    state->version=4;state->crc=texture_crc(state);return m10v_library_valid(state);
}
static int load_library(m10v_library_state *state) {
    if (!ram(state, sizeof(*state))) return M10V_LIBRARY_INVALID;
    m10v_library_init(state);
    uint32_t fs = filesystem(); if (!fs) return M10V_LIBRARY_INVALID;
    m10v_library_state candidates[2]; int available[2];uint32_t experimental_source=0;
    for (uint32_t i = 0; i < sizeof(candidates); ++i) ((uint8_t *)candidates)[i] = 0;
    for (uint32_t i = 0; i < 2; ++i)
        available[i] = ((read_fn)0x53825648u)(fs, state_names[i], sizeof(*state), &candidates[i]) &&
                       m10v_library_valid(&candidates[i]);
    if (!available[0] && !available[1]) {
        static const char published[2][12]={"M10V4A.bin","M10V4B.bin"};
        for(uint32_t i=0;i<2;i++)available[i]=read_texture_v3(fs,published[i],&candidates[i]);
        if(!available[0]&&!available[1]){
            static const char experimental[2][12]={"M10V3A.bin","M10V3B.bin"};
            for(uint32_t i=0;i<2;i++)available[i]=read_texture_v3(fs,experimental[i],&candidates[i]);
            experimental_source=1;
            if(!available[0]&&!available[1]){
                int old=migrate_v2(fs,state,1);if(old==1)old=migrate_v2(fs,state,0);
                return old==1?migrate(fs,state):old;
            }
        }
    }
    uint32_t selected = !available[0] || (available[1] && candidates[1].sequence > candidates[0].sequence);
    copy(state, &candidates[selected]);
    if(experimental_source){
        for(uint32_t i=0;i<5;i++){m10v_slot *v=&state->slots[i];v->halo_gain=(v->halo_gain&&v->halo_profile)?3:0;v->halo_spread=3;v->halo_threshold=5;v->halo_profile=2;}
        uint32_t crc=0xffffffffu;for(uint32_t i=0;i<100;i++){crc^=((uint8_t *)state)[i];for(uint32_t bit=0;bit<8;bit++)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}state->crc=~crc;return 2;
    }
    return M10V_LIBRARY_OK;
}
int m10v_camera_library_load(m10v_library_state *state){
    int result=load_library(state);
#if M10V_LIVE_COLOR
    if(result>=0)publish_preview(preview_owner(),state);
#endif
    return result;
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

int m10v_camera_library_effects(m10v_library_state *state,uint32_t slot,uint32_t field,uint32_t value){
    if(!ram(state,sizeof(*state)))return M10V_LIBRARY_INVALID;
    uint32_t fs=filesystem();return fs?m10v_library_effects(state,slot,field,value,store,(void *)(uintptr_t)fs):M10V_LIBRARY_STORE_FAILED;
}
int m10v_camera_library_reset(m10v_library_state *state,uint32_t slot){
    if(!ram(state,sizeof(*state)))return M10V_LIBRARY_INVALID;
    uint32_t fs=filesystem();return fs?m10v_library_reset(state,slot,store,(void *)(uintptr_t)fs):M10V_LIBRARY_STORE_FAILED;
}
