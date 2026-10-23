#include "m10v_isp_native_effects.h"
#include <stddef.h>
static int native_effects_span(uintptr_t p,uint32_t n){return p&&p<=UINTPTR_MAX-n;}
static int overlap(uintptr_t a,uint32_t an,uintptr_t b,uint32_t bn){return a<b+bn&&b<a+an;}
int m10v_isp_native_effects_settings(void *dst,const void *src,
    const struct m10v_isp_native_effects_config *cfg){
    uintptr_t d=(uintptr_t)dst,s=(uintptr_t)src,c=(uintptr_t)cfg;
    if(!native_effects_span(d,12)||!native_effects_span(s,12)||!native_effects_span(c,sizeof(*cfg))||(c&3)||
       (d!=s&&overlap(d,12,s,12))||overlap(d,12,c,sizeof(*cfg))||cfg->mask&~15u)return -1;
    for(uint32_t i=0;i<4;++i)if(cfg->mask&(1u<<i)){
        int v=cfg->value[i];if(i<2?(v< -4||v>4):(v<0||v>3))return -1;}
    for(uint32_t i=0;i<12;++i)((uint8_t *)dst)[i]=((const uint8_t *)src)[i];
    for(uint32_t i=0;i<4;++i)if(cfg->mask&(1u<<i)){
        uint16_t v=(uint16_t)cfg->value[i];((uint8_t *)dst)[2*i]=(uint8_t)v;((uint8_t *)dst)[2*i+1]=(uint8_t)(v>>8);}
    return 0;
}
#if defined(__arm__)
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static int ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
#endif
int m10v_isp_native_effects_grain_tables_owned(void *graph,
    const int16_t a[256],const int16_t b[256],const int16_t c[256]){
#if defined(__arm__)
    uint32_t g=(uint32_t)(uintptr_t)graph;const uint8_t *v=(const uint8_t *)graph;
    const int16_t *input[3]={a,b,c};uint32_t dest[3];
    if(!ram(g,0x120)||get32(v)!=0x54034ce0u)return -1;
    dest[0]=get32(v+0x5c);dest[1]=get32(v+0x6c);dest[2]=get32(v+0x60);
    if(get32(v+0x64)!=dest[0]||get32(v+0x70)!=dest[1]||get32(v+0x68)!=dest[2])return -1;
    for(uint32_t i=0;i<6;++i)if(get32(v+0x74+4*i)!=256)return -1;
    for(uint32_t i=0;i<3;++i){
        uint32_t s=(uint32_t)(uintptr_t)input[i];
        if(!ram(dest[i],512)||(s&1)||s<0x53000000u||s>0x80000000u-512||overlap(g,0x120,dest[i],512)||overlap(g,0x120,s,512))return -1;
        for(uint32_t j=0;j<3;++j){
            if(overlap(dest[i],512,(uintptr_t)input[j],512))return -1;
            if(i!=j&&overlap(dest[i],512,dest[j],512))return -1;}
        for(uint32_t k=0;k<256;++k)if(input[i][k]<0||input[i][k]>255)return -1;
    }
    for(uint32_t i=0;i<3;++i)for(uint32_t k=0;k<256;++k)((int16_t *)(uintptr_t)dest[i])[k]=input[i][k];
    return 0;
#else
    (void)graph;(void)a;(void)b;(void)c;return -3;
#endif
}
