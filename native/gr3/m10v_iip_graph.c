#include "m10v_iip_graph.h"
#include <stddef.h>
static int span(uintptr_t p,uint32_t n,uint32_t align){return p&&!(p&(align-1))&&p<=UINTPTR_MAX-n;}
static int overlaps(uintptr_t a,uint32_t an,uintptr_t b,uint32_t bn){return a<b+bn&&b<a+an;}
static uint16_t get16(const uint8_t *p){return (uint16_t)((uint32_t)p[0]|((uint32_t)p[1]<<8));}
static void put16(uint8_t *p,uint16_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static uint32_t get32(const uint8_t *p){return get16(p)|((uint32_t)get16(p+2)<<16);}
static void put32(uint8_t *p,uint32_t v){put16(p,(uint16_t)v);put16(p+2,(uint16_t)(v>>16));}
int m10v_iip_lut_words(uint32_t *dst,uint32_t capacity,const int16_t *src,
    uint32_t samples,uint32_t count,uint32_t stride){
    if(!count||count>1024||capacity<count||!samples||samples>UINT32_MAX/2||
       ((uint64_t)(count-1)*stride>=samples))return -1;
    uint32_t used=1+(count-1)*stride;
    if(!span((uintptr_t)dst,count*4,4)||!span((uintptr_t)src,used*2,2)||
       overlaps((uintptr_t)dst,count*4,(uintptr_t)src,used*2))return -1;
    for(uint32_t i=0;i<count;++i)dst[i]=(uint32_t)(int32_t)src[i*stride];
    return 0;
}
int m10v_iip_gpc_patch(uint8_t *image,uint32_t bytes,uint32_t alpha,
    const uint32_t element[4],const uint32_t round[4],const uint32_t flags[5]){
    uintptr_t out=(uintptr_t)image,e=(uintptr_t)element,r=(uintptr_t)round,f=(uintptr_t)flags;
    if(bytes<64||!span(out,64,4)||!span(e,16,4)||!span(r,16,4)||!span(f,20,4)||
       overlaps(out,64,e,16)||overlaps(out,64,r,16)||overlaps(out,64,f,20))return -1;
    put16(image,(uint16_t)((get16(image)&0xf000u)|(alpha&0xfffu)));
    for(uint32_t i=0;i<4;++i){
        uint8_t *p=image+0x10+4*i;uint32_t value=get32(p);
        value=(value&~0x013fffffu)|(element[i]&0xfffffu)|((round[i]&3)<<20)|((flags[i]&1)<<24);
        if(!i)value=(value&0x0fffffffu)|((flags[4]&15)<<28);
        put32(p,value);
    }
    return 0;
}
int m10v_iip_spf_bank_patch(uint8_t *image,uint32_t bytes,uint32_t bank,const uint32_t values[17]){
    uintptr_t out=(uintptr_t)image,v=(uintptr_t)values;
    if(bytes<0x284||bank>3||!span(out,0x284,4)||!span(v,68,4)||overlaps(out,0x284,v,68))return -1;
    for(uint32_t i=0;i<17;++i){uint8_t *p=image+0x84+bank*0x40+2*i;
        put16(p,(uint16_t)((get16(p)&0xe000u)|(values[i]&0x1fff)));}
    return 0;
}
#if defined(__arm__)
static int native_ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
#endif
int m10v_iip_original_copy_owned(uint32_t context,const void *rectangle,
    void *destination,void *source){
#if defined(__arm__)
    uint32_t dst=(uint32_t)(uintptr_t)destination,src=(uint32_t)(uintptr_t)source,rect=(uint32_t)(uintptr_t)rectangle;
    if(!native_ram(context,0x38)||!native_ram(dst,0x50)||!native_ram(src,0x50)||
       (rect&&!native_ram(rect,16))||overlaps(dst,0x50,src,0x50)||
       overlaps(dst,0x50,context,0x38)||overlaps(src,0x50,context,0x38))return -1;
    /* This is the ORIGINAL operation used by 0x53685f38. Never construct a
     * scheduler/task object here or point it at invented storage. */
    uint32_t graph_owner=((const uint32_t *)(uintptr_t)context)[2];
    if(!native_ram(graph_owner,16)||!native_ram(((const uint32_t *)(uintptr_t)graph_owner)[1],0x110))return -1;
    /* Only the native format=6 single-plane descriptor shape is admitted in
     * this first adapter. Cache span arithmetic is from 0x5376bd18. Pixel
     * interpretation remains the original unit's responsibility. */
    const uint8_t *s=(const uint8_t *)source,*d=(const uint8_t *)destination;
    uint32_t w=get16(s+0x28),h=get16(s+0x2a),ss=get32(s+0x2c),ds=get32(d+0x2c);
    if(s[9]!=6||d[9]!=6||!w||w>6144||!h||h>4096||get16(d+0x28)!=w||get16(d+0x2a)!=h||
       !ss||ss>32768||!ds||ds>32768||get32(s+0x40)||get32(s+0x44)||get32(s+0x48)||
       get32(d+0x40)||get32(d+0x44)||get32(d+0x48))return -1;
    uint32_t sp=get32(s+0x3c),dp=get32(d+0x3c),sn=ss*h,dn=ds*h;
    if(!native_ram(sp,sn)||!native_ram(dp,dn)||overlaps(sp,sn,dp,dn)||
       overlaps(sp,sn,src,0x50)||overlaps(sp,sn,dst,0x50)||overlaps(sp,sn,context,0x38)||
       overlaps(dp,dn,src,0x50)||overlaps(dp,dn,dst,0x50)||overlaps(dp,dn,context,0x38))return -1;
    typedef int (*original_fn)(uint32_t,const void *,void *,void *);
    return ((original_fn)0x53681260u)(context,rectangle,destination,source)?0:-4;
#else
    (void)context;(void)rectangle;(void)destination;(void)source;return -3;
#endif
}
int m10v_iip_original_stage_owned(uint32_t context,void *parameters){
#if defined(__arm__)
    uint32_t p=(uint32_t)(uintptr_t)parameters;
    if(!native_ram(context,0x38)||!native_ram(p,0x34)||overlaps(context,0x38,p,0x34))return -1;
    const uint8_t *v=(const uint8_t *)parameters;
    if(!native_ram(get32(v+4),0x50)||!native_ram(get32(v+8),0x50)||
       !native_ram(get32(v+0x10),12))return -1;
    uint32_t owner=((const uint32_t *)(uintptr_t)context)[2];
    if(!native_ram(owner,16)||!native_ram(((const uint32_t *)(uintptr_t)owner)[1],0x110))return -1;
    typedef int (*original_fn)(uint32_t,void *,void *);
    /* Non-null third argument is ONLY sizing/query, not execution. */
    return ((original_fn)0x53680dbcu)(context,parameters,NULL)?0:-4;
#else
    (void)context;(void)parameters;return -3;
#endif
}
int m10v_iip_spf_probe_owned(uint32_t context,void *workspace,uint32_t bytes,
    uint32_t coefficient_index,uint32_t coefficient_bits,uint32_t impulse){
#if defined(__arm__)
    uint32_t work=(uint32_t)(uintptr_t)workspace;
    if(bytes<M10V_IIP_SPF_PROBE_BYTES||!native_ram(work,M10V_IIP_SPF_PROBE_BYTES)||(work&15)||
       !native_ram(context,0x38)||overlaps(work,M10V_IIP_SPF_PROBE_BYTES,context,0x38)||
       coefficient_index>=17||coefficient_bits>0x1fff||impulse>0x3fff)return -1;
    uint32_t owner=((const uint32_t *)(uintptr_t)context)[2];
    if(!native_ram(owner,16)||!native_ram(((const uint32_t *)(uintptr_t)owner)[1],0x110)||
       overlaps(work,M10V_IIP_SPF_PROBE_BYTES,owner,16)||
       overlaps(work,M10V_IIP_SPF_PROBE_BYTES,((const uint32_t *)(uintptr_t)owner)[1],0x110))return -1;
    uint8_t *base=(uint8_t *)workspace;
    for(uint32_t i=0;i<M10V_IIP_SPF_PROBE_BYTES;++i)base[i]=0;
    uint32_t *report=(uint32_t *)base;
    uint8_t *src=base+0x40,*dst=base+0x90,*loader=base+0xe0,*spf=base+0x1a0;
    uint8_t *store=base+0x4a0,*graph=base+0x660;
    uint16_t *kernel=(uint16_t *)(base+0x780),*input=(uint16_t *)(base+0x800),*output=(uint16_t *)(base+0x1000);
    report[0]=0x31504653;report[1]=1;report[2]=coefficient_index;report[3]=coefficient_bits;
    report[4]=impulse;report[5]=0xfffffffe; /* staged; not yet completed */
    kernel[coefficient_index]=(uint16_t)coefficient_bits;
    input[16*32+16]=(uint16_t)impulse;
    for(uint32_t i=0;i<1024;++i)output[i]=0xa55a;
    typedef void *(*ctor)(void *,uint32_t,const void *);
    typedef void *(*desc_ctor)(void *,uint32_t,uint32_t,uint32_t,uint32_t);
    typedef void *(*plane_fn)(void *,void *,uint32_t,uint32_t);
    typedef void *(*link_fn)(void *,void *);
    typedef void (*one_fn)(void *);
    typedef void (*bounds_fn)(void *,uint32_t,uint32_t,uint32_t,uint32_t);
    typedef void (*kernel_fn)(void *,const uint16_t *,uint32_t);
    typedef void (*raw_fn)(void *,uint32_t);
    typedef int (*register_fn)(uint32_t,void *,void *);
    typedef int (*submit_fn)(uint32_t,void *,uint32_t,void *,void *,void *);
    typedef int (*wait_fn)(uint32_t,uint32_t);
    ((desc_ctor)0x5376bba0u)(src,32,32,6,0x100000);
    ((desc_ctor)0x5376bba0u)(dst,32,32,6,0x100000);
    ((plane_fn)0x5376bc08u)(src,input,64,0);
    ((plane_fn)0x5376bc08u)(dst,output,64,0);
    ((one_fn)0x5376bc64u)(src);
    /* Sentinel initialization dirtied destination cache lines as well. Clean
     * them BEFORE DMA so a later eviction cannot overwrite hardware output. */
    ((one_fn)0x5376bc64u)(dst);
    ((ctor)0x536789f0u)(loader,2,0);
    /* Actual original lowpass-bank call at 0x5367a7c0..0x5367a810:
     * template headerB=0 | 0x1f800 | 0x300, followed by mode0 and17values. */
    ((ctor)0x5368b6b4u)(spf,0x1fb00,0);
    ((bounds_fn)0x5368b9a8u)(spf,0x40,0x40,32,1);
    ((raw_fn)0x5377ae04u)(spf+0x40,0);
    ((kernel_fn)0x5368bd78u)(spf,kernel,1);
    ((ctor)0x5368c3d8u)(store,8,0);
    ((bounds_fn)0x5368c5b4u)(store,0x40,0x40,32,1);
    /* Same zero-initialized Composite fields as 0x5367b1bc..0x5367b300. */
    put32(graph,0x54034ce0u);graph[0xa1]=1;put32(graph+0x38,context+4);
    ((register_fn)0x5376bfdcu)(owner,graph,src);
    ((register_fn)0x5376bfdcu)(owner,graph,dst);
    void *port=((link_fn)0x5376be78u)(src,loader);
    port=((link_fn)0x5376bec8u)(port,spf);
    port=((link_fn)0x5376bec8u)(port,store);
    ((link_fn)0x5376bf58u)(port,dst);
    report[6]=((submit_fn)0x5376cd10u)(owner,graph,3,loader,spf,store);
    int ok=((wait_fn)0x5368a510u)(context,0x400);
    ((one_fn)0x5376c044u)(graph);
    ((one_fn)0x5376bd18u)(dst);
    /* Explicit NON-deleting destructors; workspace is caller RAM. */
    ((one_fn)0x536787d8u)(loader);
    ((one_fn)0x5368b634u)(spf);
    ((one_fn)0x5368c174u)(store);
    report[5]=ok?0:0xfffffffcu;
    if(ok){
        uint32_t hash=2166136261u,min=0xffff,max=0,changed=0,nonzero=0,recorded=0,peak=0;
        uint32_t *sparse=(uint32_t *)(base+0x7c0);
        for(uint32_t i=0;i<1024;++i){uint32_t v=output[i];hash=(hash^(v&255))*16777619u;hash=(hash^(v>>8))*16777619u;
            if(v<min)min=v;if(v>max){max=v;peak=i;}if(v!=0xa55a)++changed;
            if(v){++nonzero;if(recorded<16)sparse[recorded++]=(v<<16)|i;}}
        report[7]=hash;report[8]=min;report[9]=max;report[10]=changed;
        report[11]=nonzero;report[12]=recorded;report[13]=peak;
    }
    return ok?0:-4;
#else
    (void)context;(void)workspace;(void)bytes;(void)coefficient_index;(void)coefficient_bits;(void)impulse;return -3;
#endif
}
