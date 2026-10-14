/* Temporary on-camera trace: snapshot the rejected/passed guard into a unique
 * SD file. Uses the same FileSystem facade and virtual ABI as the locked
 * timestamp settings module; never writes image, CFA or metadata buffers. */
#include <stdint.h>
#include "halation_controls.h"
static inline int ram(uint32_t p, uint32_t n) {
    return !(p & 3) && p >= 0x55000000u && p < 0x80000000u && n <= 0x80000000u-p;
}
static inline int code(uint32_t p, uint32_t n) {
    return !(p & 3) && p >= 0x53000000u && p < 0x540b6000u && n <= 0x540b6000u-p;
}
void m10v_trace_800t(uint32_t stage, uint32_t context, const uint32_t *stats) {
    uint32_t record[64];
    for (uint32_t i=0;i<64;i++) record[i]=0;
    record[0]=0x5630314du; record[1]=0x54303038u;
    record[2]=3;record[3]=stage;record[4]=context;
    if (stats && ram((uint32_t)stats,32))
        for(uint32_t i=0;i<8;i++)record[56+i]=stats[i];
    if (ram(context,0x60)) {
        const uint32_t *ctx=(const uint32_t *)context;
        for(uint32_t i=0;i<24;i++)record[8+i]=ctx[i];
        uint32_t desc=ctx[15],preview=ctx[18],shooting=ctx[13],request=ctx[14],jpeg=ctx[19];
        if(ram(desc,32))for(uint32_t i=0;i<8;i++)record[32+i]=((const uint32_t *)desc)[i];
        if(ram(preview,32))for(uint32_t i=0;i<8;i++)record[48+i]=((const uint32_t *)preview)[i];
        if(ram(shooting,0x785)) {
            record[44]=((const uint8_t *)shooting)[0x77c];
            record[47]=m10v_camera_controls((const uint8_t *)shooting,2);
            record[5]=((uint32_t (*)(uint32_t,uint32_t,uint32_t))0x540be000u)(6,0,0);
            record[6]=m10v_control_record();
        }
        if(ram(request,14))record[45]=((const uint8_t *)request)[12] | ((uint32_t)((const uint8_t *)request)[13]<<8);
        if(ram(jpeg,17))record[46]=((const uint8_t *)jpeg)[16];
        if(context>=0x550009b8u) {
            uint32_t recipe=context-0x9b8u;
            if(ram(recipe,0x44cc)) {
                const uint32_t *r=(const uint32_t *)recipe;
                record[40]=r[6];record[41]=r[24];record[42]=r[0x230/4];
                if(ram(record[42],4))record[43]=*(const uint32_t *)record[42];
            }
        }
    }
    typedef uint32_t (*get_fn)(void);
    typedef int (*open_fn)(uint32_t,const char *,uint32_t,uint32_t *,uint32_t *);
    typedef int (*write_fn)(uint32_t,uint32_t,const void *,uint32_t,uint32_t *);
    typedef int (*close_fn)(uint32_t,uint32_t,uint32_t *);
    uint32_t manager=((get_fn)0x535847d8u)();
    if(!ram(manager,24))return;
    uint32_t fs=((const uint32_t *)manager)[5];
    if(!ram(fs,4))return;
    uint32_t vt=*(const uint32_t *)fs;
    if(!code(vt,44))return;
    const uint32_t *v=(const uint32_t *)vt;
    if(!code(v[7],4)||!code(v[8],4)||!code(v[10],4))return;
    /* C: is the stock removable-media debug destination (BEPRCLAP.CSV etc).
     * Unique 8.3 name; overwrite only this trace file with the latest shot. */
    volatile uint32_t path_words[4];
    path_words[0]=0x4d5c3a43u;path_words[1]=0x38563031u;
    path_words[2]=0x4e49422eu;path_words[3]=0;
    const char *path=(const char *)path_words;
    uint32_t handle=0,error=0;
    if(!((open_fn)v[7])(fs,path,0,&handle,&error)||!handle)return;
    ((write_fn)v[10])(fs,handle,record,sizeof(record),&error);
    ((close_fn)v[8])(fs,handle,&error);
}
