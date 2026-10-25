#include "m10v_spatial_accel.h"
#include <stddef.h>
#if defined(__arm__)
#include <arm_neon.h>
#endif

static uint16_t tap(uint16_t l,uint16_t m,uint16_t r){
    return (uint16_t)(((uint32_t)l+2u*m+r)>>2);
}
static __attribute__((always_inline)) inline void eight(const uint16_t *l,const uint16_t *m,const uint16_t *r,uint16_t *dst){
#if defined(__arm__)
    /* All additions widen BEFORE summing. Saturating/16-bit addition changes
     * highlights; each original pass rounds once, after the complete sum. */
    __asm__ volatile(
        "vld1.16 {d16,d17}, [%0]\n"
        "vld1.16 {d18,d19}, [%1]\n"
        "vld1.16 {d20,d21}, [%2]\n"
        "vaddl.u16 q11,d16,d20\n"
        "vaddl.u16 q12,d17,d21\n"
        "vaddw.u16 q11,q11,d18\n"
        "vaddw.u16 q12,q12,d19\n"
        "vaddw.u16 q11,q11,d18\n"
        "vaddw.u16 q12,q12,d19\n"
        "vshrn.i32 d16,q11,#2\n"
        "vshrn.i32 d17,q12,#2\n"
        "vst1.16 {d16,d17}, [%3]\n"
        : : "r"(l),"r"(m),"r"(r),"r"(dst)
        : "d16","d17","d18","d19","d20","d21","d22","d23","d24","d25","memory");
#else
    for(uint32_t i=0;i<8;++i)dst[i]=tap(l[i],m[i],r[i]);
#endif
}

int m10v_spatial_blur_u16(uint16_t *a,uint16_t *b,uint32_t capacity,
    uint32_t w,uint32_t h,uint32_t passes,uint32_t d){
    if(!a||!b||((uintptr_t)a&1)||((uintptr_t)b&1)||!w||w>384||!h||h>256||
       passes>9||d<1||d>2||capacity<w*h)return -1;
    uint32_t bytes=2*w*h;uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(aa>UINTPTR_MAX-bytes||bb>UINTPTR_MAX-bytes||(aa<bb+bytes&&bb<aa+bytes))return -1;
    for(uint32_t pass=0;pass<passes;++pass){
        for(uint32_t y=0;y<h;++y){
            const uint16_t *src=a+y*w;uint16_t *dst=b+y*w;uint32_t x=0;
            for(;x<w&&x<d;++x)dst[x]=tap(src[0],src[x],src[x+d<w?x+d:w-1]);
            for(;x+8+d<=w;x+=8)eight(src+x-d,src+x,src+x+d,dst+x);
            for(;x<w;++x)dst[x]=tap(src[x<d?0:x-d],src[x],src[x+d<w?x+d:w-1]);
        }
        for(uint32_t y=0;y<h;++y){
            const uint16_t *top=b+(y<d?0:y-d)*w,*mid=b+y*w,*bot=b+(y+d<h?y+d:h-1)*w;
            uint16_t *dst=a+y*w;uint32_t x=0;
            for(;x+8<=w;x+=8)eight(top+x,mid+x,bot+x,dst+x);
            for(;x<w;++x)dst[x]=tap(top[x],mid[x],bot[x]);
        }
    }
    return 0;
}

int m10v_spatial_grain_work_bytes(uint32_t w,uint32_t h,uint32_t address,uint32_t *required){
    if(!required||((uintptr_t)required&3)||!w||w>6144||!h||h>4096||address>UINT32_MAX-15)return -1;
    uint32_t bytes=((w+15)&~15u)*h,padding=(-address)&15;
    if(address>UINT32_MAX-bytes-padding)return -1;
    *required=bytes+padding;return 0;
}

#if defined(__arm__)
static int stock_ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
static int stock_overlap(uint32_t a,uint32_t an,uint32_t b,uint32_t bn){return a<b+bn&&b<a+an;}
#endif
int m10v_spatial_stock_grain_execute(uint32_t context,const void *source,
    const void *destination,uint32_t strength,void *workspace,uint32_t capacity){
#if defined(__arm__)
    uint32_t src=(uint32_t)(uintptr_t)source,dst=(uint32_t)(uintptr_t)destination,work=(uint32_t)(uintptr_t)workspace;
    if(!stock_ram(context,16)||!stock_ram(src,32)||!stock_ram(dst,32)||!stock_ram(work,capacity)||!capacity||strength<1||strength>3)return -1;
    const uint16_t *s=(const uint16_t *)(src+16),*d=(const uint16_t *)(dst+16);
    uint32_t w=s[0],h=s[1],required=0;
    if(w<2||(w&1)||w>6144||!h||h>4096||d[0]!=w||d[1]!=h||
       s[2]<w||s[2]>16384||d[2]<w||d[2]>16384||
       m10v_spatial_grain_work_bytes(w,h,work,&required)||capacity<required)return -1;
    uint32_t input=((const uint32_t *)source)[1],output=((const uint32_t *)destination)[1];
    uint32_t input_bytes=(uint32_t)s[2]*h,output_bytes=(uint32_t)d[2]*h;
    if(!stock_ram(input,input_bytes)||!stock_ram(output,output_bytes)||
       stock_overlap(src,32,dst,32)||stock_overlap(src,32,context,16)||stock_overlap(dst,32,context,16)||
       stock_overlap(input,input_bytes,src,32)||stock_overlap(input,input_bytes,dst,32)||stock_overlap(input,input_bytes,context,16)||
       stock_overlap(output,output_bytes,src,32)||stock_overlap(output,output_bytes,dst,32)||stock_overlap(output,output_bytes,context,16)||
       stock_overlap(input,input_bytes,output,output_bytes)||
       stock_overlap(work,capacity,input,input_bytes)||stock_overlap(work,capacity,output,output_bytes)||
       stock_overlap(work,capacity,src,32)||stock_overlap(work,capacity,dst,32)||stock_overlap(work,capacity,context,16))return -1;
    typedef int (*stock_fn)(uint32_t,const void *,const void *,uint32_t,void *,uint32_t *);
    return ((stock_fn)0x5367ad3cu)(context,source,destination,strength,workspace,&capacity)?0:-4;
#else
    (void)context;(void)source;(void)destination;(void)strength;(void)workspace;(void)capacity;
    return -3;
#endif
}
