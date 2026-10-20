#include "m10v_storage.h"
#include "../gr3/m10v_sd_library.h"
_Static_assert(sizeof(m10v_library_state)==104,"GR II state ABI changed");
static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static void put16(uint8_t *p,uint16_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void put32(uint8_t *p,uint32_t v){for(uint32_t i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static void copy(uint8_t *d,const uint8_t *s,uint32_t n){for(uint32_t i=0;i<n;i++)d[i]=s[i];}
int gr2_state_encode(const m10v_library_state *state,uint8_t *wire){
    if(!wire||!m10v_library_valid(state))return 0;
    uint8_t next[104];
    put32(next,state->magic);put16(next+4,state->version);put16(next+6,state->size);put32(next+8,state->sequence);
    for(uint32_t i=0;i<5;i++){
        const m10v_slot *v=&state->slots[i];uint8_t *p=next+12+8*i;
        put16(p,v->film);p[2]=v->grain;p[3]=v->soft;p[4]=v->halo_gain;p[5]=v->halo_spread;p[6]=v->halo_threshold;p[7]=v->halo_profile;
    }
    next[52]=state->stamp;next[53]=state->format;next[54]=state->corner;next[55]=state->color;
    copy(next+56,(const uint8_t *)state->effects,40);put32(next+96,state->reserved);
    put32(next+100,m10v_sd_crc(next,100));copy(wire,next,104);return 1;
}
int gr2_state_decode(const uint8_t *wire,m10v_library_state *state){
    if(!wire||!state||m10v_sd_crc(wire,100)!=m10v_sd_u32(wire+100))return 0;
    m10v_library_state next;
    next.magic=m10v_sd_u32(wire);next.version=u16(wire+4);next.size=u16(wire+6);next.sequence=m10v_sd_u32(wire+8);
    for(uint32_t i=0;i<5;i++){
        m10v_slot *v=&next.slots[i];const uint8_t *p=wire+12+8*i;
        v->film=u16(p);v->grain=p[2];v->soft=p[3];v->halo_gain=p[4];v->halo_spread=p[5];v->halo_threshold=p[6];v->halo_profile=p[7];
    }
    next.stamp=wire[52];next.format=wire[53];next.corner=wire[54];next.color=wire[55];
    copy((uint8_t *)next.effects,wire+56,40);next.reserved=m10v_sd_u32(wire+96);
    next.crc=m10v_sd_crc((const uint8_t *)&next,100);
    if(!m10v_library_valid(&next))return 0;
    copy((uint8_t *)state,(const uint8_t *)&next,104);return 1;
}
