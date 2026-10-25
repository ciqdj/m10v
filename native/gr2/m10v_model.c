#include "m10v_model.h"
#include "m10v_boot.h"
_Static_assert(sizeof(m10v_gr2_image)==44,"GR II image ABI changed");
volatile uint32_t gr2_boot_count;
volatile uint32_t gr2_code_sync_status;
/* Caller continuation must retain the original -1 result and final callbacks.
 * Activate only already-loaded source hooks and their validated data gateway. */
uint32_t gr2_post_load(void){gr2_boot_count++;gr2_native_activate();return UINT32_MAX;}
int gr2_date_valid(const uint16_t f[6]){
    static const uint8_t days[12]={31,28,31,30,31,30,31,31,30,31,30,31};
    if(!f||f[0]<2000||f[0]>2127||!f[1]||f[1]>12||!f[2]||f[3]>23||f[4]>59||f[5]>59)return 0;
    uint32_t max=days[f[1]-1];
    if(f[1]==2&&!(f[0]&3)&&f[0]!=2100)max++;
    return f[2]<=max;
}
static uint32_t word(const uint8_t *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static int range(uint32_t p,uint32_t n){return p&&n&&n<=UINT32_MAX-p;}
static int overlap(uint32_t a,uint32_t an,uint32_t b,uint32_t bn){return a<b+bn&&b<a+an;}
int gr2_capture_decode(const uint8_t *p,m10v_gr2_image *out){
    if(!p||!out)return 0;
    uint32_t dims=word(p+8),w=dims&65535,h=dims>>16,kind=p[13];
    if(w<2||w>4928||h<2||h>3264||(w&1)||(h&1)||kind<2||kind>4)return 0;
    uint32_t ys=(w+15)&~15u,cs=kind==4?ys:((w>>1)+15)&~15u;
    if(kind!=4)ys=cs<<1;
    /* Stock computes plane addresses from default pitches BEFORE overrides. */
    uint32_t y=word(p),yn=ys*h,cn=cs*(kind==3?h>>1:h);
    if(!range(y,yn)||!range(y+yn,cn)||!range(y+yn+cn,cn))return 0;
    uint32_t u=word(p+24),v=word(p+28),override=word(p+32);
    if(!u)u=y+yn;if(!v)v=y+yn+cn;
    if(override)ys=override;
    override=word(p+36);if(override)cs=override;
    if(ys<w||ys>16384||cs<(kind==4?w:w>>1)||cs>16384)return 0;
    yn=ys*h;cn=cs*(kind==3?h>>1:h);
    if(!range(y,yn)||!range(u,cn)||!range(v,cn)||overlap(y,yn,u,cn)||overlap(y,yn,v,cn)||overlap(u,cn,v,cn))return 0;
    uint32_t dst=(uint32_t)(uintptr_t)out,src=(uint32_t)(uintptr_t)p;
    if(!range(dst,sizeof(*out))||!range(src,48)||overlap(dst,sizeof(*out),src,48)||
       overlap(dst,sizeof(*out),y,yn)||overlap(dst,sizeof(*out),u,cn)||overlap(dst,sizeof(*out),v,cn))return 0;
    out->y=(uint8_t *)(uintptr_t)y;out->u=(uint8_t *)(uintptr_t)u;out->v=(uint8_t *)(uintptr_t)v;
    out->y_bytes=yn;out->u_bytes=cn;out->v_bytes=cn;out->width=w;out->height=h;
    out->y_stride=ys;out->chroma_stride=cs;out->format=kind==2?0x422:kind==3?0x420:0x444;
    return 1;
}
