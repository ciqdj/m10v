#include "m10v_isp_native_effects.h"
#include <stddef.h>
static int native_effects_span(uintptr_t p,uint32_t n){return p&&p<=UINTPTR_MAX-n;}
#ifndef M10V_NATIVE_NOISE_ONLY
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
/* Coordinate division only at frame entry; no EABI divide runtime and no
 * per-pixel division on Cortex-A9. Inputs are bounded below2^18. */
static uint32_t divide(uint32_t n,uint32_t d){
    uint32_t q=0,r=0;
    for(uint32_t i=18;i;--i){r=(r<<1)|((n>>(i-1))&1);q<<=1;if(r>=d){r-=d;++q;}}
    return q;
}
int m10v_isp_native_effects_field(uint8_t *noise,uint32_t bytes,
    uint32_t w,uint32_t h,uint32_t stride,const uint8_t *field,
    uint32_t fw,uint32_t fh,uint32_t fs,uint32_t mix){
    if(!w||w>6144||!h||h>4096||stride<w||stride>32768||!fw||fw>512||!fh||fh>512||
       fs<fw||fs>32768||mix>255||bytes<stride*h||!native_effects_span((uintptr_t)noise,stride*h)||
       !native_effects_span((uintptr_t)field,fs*fh)||overlap((uintptr_t)noise,stride*h,(uintptr_t)field,fs*fh))return -1;
    if(mix==255)return 0;
    uint32_t xd=w>1?w-1:1,yd=h>1?h-1:1;
    uint32_t xn=w>1?(fw-1)*256:0,yn=h>1?(fh-1)*256:0;
    uint32_t xs=divide(xn,xd),xr=xn-xs*xd,ys=divide(yn,yd),yr=yn-ys*yd;
    uint32_t py=0,ye=0;
    for(uint32_t y=0;y<h;++y){
        uint32_t iy=py>>8,dy=py&255;
        uint32_t jy=iy+1<fh?iy+1:iy;
        const uint8_t *a=field+iy*fs,*b=field+jy*fs;
        uint8_t *out=noise+y*stride;
        uint32_t px=0,xe=0;
        for(uint32_t x=0;x<w;++x){
            uint32_t ix=px>>8,dx=px&255;
            uint32_t jx=ix+1<fw?ix+1:ix;
            uint32_t top=a[ix]*(256-dx)+a[jx]*dx,bot=b[ix]*(256-dx)+b[jx]*dx;
            uint32_t v=(top*(256-dy)+bot*dy+32768)>>16;
            out[x]=(uint8_t)((out[x]*mix+v*(255-mix)+127)/255);
            px+=xs;xe+=xr;if(xe>=xd){xe-=xd;++px;}
        }
        py+=ys;ye+=yr;if(ye>=yd){ye-=yd;++py;}
    }
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

#endif /* M10V_NATIVE_NOISE_ONLY */

/* Mid-CDF maps of two separable floor-averages of k independent uniform8
 * samples. Generated with exact integer convolutions, not fitted image data.
 * Restores the original uniform mask marginal after correlation filtering. */
static const uint8_t noise_cdf2[256]={
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,
1,1,1,1,1,1,1,2,2,2,2,2,3,3,3,3,
4,4,4,5,5,5,6,6,7,7,8,8,9,9,10,11,
11,12,13,14,14,15,16,17,18,19,20,21,22,23,25,26,
27,28,30,31,33,34,36,37,39,40,42,44,46,47,49,51,
53,55,57,59,61,63,65,68,70,72,74,77,79,81,84,86,
89,91,94,96,99,101,104,106,109,112,114,117,120,122,125,128,
130,133,135,138,141,143,146,149,151,154,156,159,161,164,166,169,
171,174,176,178,181,183,185,187,190,192,194,196,198,200,202,204,
206,208,209,211,213,215,216,218,219,221,222,224,225,227,228,229,
230,232,233,234,235,236,237,238,239,240,241,241,242,243,244,244,
245,246,246,247,247,248,248,249,249,250,250,250,251,251,251,252,
252,252,252,253,253,253,253,253,254,254,254,254,254,254,254,254,
254,254,255,255,255,255,255,255,255,255,255,255,255,255,255,255,
255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255
};
static const uint8_t noise_cdf3[256]={
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,
1,1,2,2,2,2,2,3,3,3,4,4,5,5,6,7,
7,8,9,10,10,11,12,14,15,16,17,19,20,22,24,25,
27,29,31,34,36,38,41,43,46,49,52,54,57,61,64,67,
71,74,78,81,85,89,92,96,100,104,108,112,116,120,124,128,
132,136,140,144,148,152,156,160,164,168,171,175,179,182,186,189,
192,195,199,202,204,207,210,213,215,218,220,222,224,226,228,230,
232,234,235,237,238,239,241,242,243,244,245,246,247,247,248,249,
249,250,250,251,251,252,252,252,253,253,253,253,254,254,254,254,
254,254,254,254,255,255,255,255,255,255,255,255,255,255,255,255,
255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,
255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,
255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255
};

#if defined(M10V_NOISE_NEON)
#include <arm_neon.h>
/* For sum<=765, floor(sum*21846/65536)==floor(sum/3). SQDMULH
 * doubles10923 then keeps the signed high half, exactly that expression. */
static uint8x16_t noise_average3(uint8x16_t a,uint8x16_t b,uint8x16_t c){
    uint16x8_t lo=vaddw_u8(vaddl_u8(vget_low_u8(a),vget_low_u8(b)),vget_low_u8(c));
    uint16x8_t hi=vaddw_u8(vaddl_u8(vget_high_u8(a),vget_high_u8(b)),vget_high_u8(c));
    int16x8_t factor=vdupq_n_s16(10923);
    return vcombine_u8(vmovn_u16(vreinterpretq_u16_s16(vqdmulhq_s16(vreinterpretq_s16_u16(lo),factor))),
                      vmovn_u16(vreinterpretq_u16_s16(vqdmulhq_s16(vreinterpretq_s16_u16(hi),factor))));
}
int m10v_isp_native_effects_noise_shape(uint8_t *noise,uint32_t bytes,
    uint32_t w,uint32_t h,uint32_t stride,uint32_t size){
    if(!w||w>6144||!h||h>4096||stride<w||stride>32768||size>2||
       bytes<stride*h||!native_effects_span((uintptr_t)noise,stride*h))return -1;
    if(!size)return 0;
    /* Reverse traversal leaves all causal source neighbors untouched until
     * loaded. There is no row/history allocation, including skinny tails. */
    for(uint32_t y=0;y<h;++y){
        uint8_t *p=noise+y*stride;uint32_t x=w;
        for(;x>=18;x-=16){
            uint8x16_t a=vld1q_u8(p+x-16),b=vld1q_u8(p+x-17);
            uint8x16_t avg=size==1?vhaddq_u8(a,b):noise_average3(a,b,vld1q_u8(p+x-18));
            vst1q_u8(p+x-16,avg);
        }
        while(x){--x;uint32_t a=p[x],b=p[x?x-1:0],c=p[x>1?x-2:0];
            p[x]=(uint8_t)(size==1?(a+b)>>1:(a+b+c)/3);}
    }
    const uint8_t *cdf=size==1?noise_cdf2:noise_cdf3;
    for(uint32_t row=h;row;){
        uint32_t y=--row;uint8_t *p=noise+y*stride;
        const uint8_t *previous=noise+(y?y-1:0)*stride;
        const uint8_t *previous2=noise+(y>1?y-2:0)*stride;
        uint32_t x=0;
        for(;x+16<=w;x+=16){
            uint8x16_t a=vld1q_u8(p+x),b=vld1q_u8(previous+x);
            uint8x16_t avg=size==1?vhaddq_u8(a,b):noise_average3(a,b,vld1q_u8(previous2+x));
            uint8_t index[16];vst1q_u8(index,avg);
            #pragma clang loop unroll(full)
            for(uint32_t j=0;j<16;++j)p[x+j]=cdf[index[j]];
        }
        for(;x<w;++x){uint32_t a=p[x],b=previous[x],c=previous2[x];
            p[x]=cdf[size==1?(a+b)>>1:(a+b+c)/3];}
    }
    return 0;
}
#else
int m10v_isp_native_effects_noise_shape(uint8_t *noise,uint32_t bytes,
    uint32_t w,uint32_t h,uint32_t stride,uint32_t size){
    if(!w||w>6144||!h||h>4096||stride<w||stride>32768||size>2||
       bytes<stride*h||!native_effects_span((uintptr_t)noise,stride*h))return -1;
    if(!size)return 0;
    /* Horizontal causal FIR, keeping ORIGINAL previous samples in registers. */
    for(uint32_t y=0;y<h;++y){
        uint8_t *p=noise+y*stride;uint32_t prev=p[0],prev2=prev;
        for(uint32_t x=0;x<w;++x){
            uint32_t cur=p[x];
            p[x]=(uint8_t)(size==1?(cur+prev)>>1:(cur+prev+prev2)/3);
            prev2=prev;prev=cur;
        }
    }
    /* Vertical causal FIR in64-byte tiles. Only128 bytes of history, no frame
     * allocation. Read a tile before replacing it; history is pre-CDF input.
     * Traversing all rows of a tile keeps input/output memory sequential within
     * a cache line and avoids column-at-a-time full-frame cache amplification. */
    uint8_t previous[64],previous2[64];
    const uint8_t *cdf=size==1?noise_cdf2:noise_cdf3;
    for(uint32_t base=0;base<w;base+=64){
        uint32_t n=w-base<64?w-base:64;
        for(uint32_t x=0;x<n;++x)previous[x]=previous2[x]=noise[base+x];
        for(uint32_t y=0;y<h;++y){
            uint8_t *p=noise+y*stride+base;
            for(uint32_t x=0;x<n;++x){
                uint32_t cur=p[x],a=previous[x],b=previous2[x];
                uint32_t avg=size==1?(cur+a)>>1:(cur+a+b)/3;
                previous2[x]=(uint8_t)a;previous[x]=(uint8_t)cur;p[x]=cdf[avg];
            }
        }
    }
    return 0;
}

#endif /* M10V_NOISE_NEON */
