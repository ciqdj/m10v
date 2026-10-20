#include "m10v_capture.h"
static int valid(uint32_t p,uint32_t n){return p&&n&&n<=UINT32_MAX-p;}
static int overlaps(uint32_t a,uint32_t an,uint32_t b,uint32_t bn){return a<b+bn&&b<a+an;}
static int hits(uint32_t p,uint32_t n,uint32_t y,uint32_t yn,uint32_t c,uint32_t cn){
    return !valid(p,n)||overlaps(p,n,y,yn)||overlaps(p,n,c,cn);
}
int gr2_render_planar(const m10v_gr2_image *im,const m10v_library_state *state,uint32_t slot,
                      const m10v_library_date *date,uint32_t seed,uint8_t *scratch,uint32_t scratch_bytes){
    if(!im||!m10v_library_valid(state)||slot>=5||im->format!=0x422||im->width<2||im->width>4928||
       im->height<2||im->height>3264||(im->width&1)||(im->height&1)||im->y_stride<im->width||
       im->y_stride>16384||im->chroma_stride>8192||im->chroma_stride*2!=im->y_stride)return -1;
    uint32_t yn=im->y_stride*im->height,cn=im->chroma_stride*im->height;
    uint32_t y=(uint32_t)(uintptr_t)im->y,u=(uint32_t)(uintptr_t)im->u,v=(uint32_t)(uintptr_t)im->v;
    if(im->y_bytes<yn||im->u_bytes!=cn||im->v_bytes!=cn||!valid(y,yn)||!valid(u,2*cn)||u+cn!=v||overlaps(y,yn,u,2*cn))return -1;
    if(hits((uint32_t)(uintptr_t)im,sizeof(*im),y,yn,u,2*cn)||
       hits((uint32_t)(uintptr_t)state,sizeof(*state),y,yn,u,2*cn)||
       (date&&hits((uint32_t)(uintptr_t)date,sizeof(*date),y,yn,u,2*cn))||
       (scratch_bytes&&hits((uint32_t)(uintptr_t)scratch,scratch_bytes,y,yn,u,2*cn)))return -1;
    m10v_library_image paired={im->y,im->u,yn,2*cn,im->width,im->height,im->y_stride};
    if(!gr2_chroma_shuffle(im->u,cn,0))return -1;
    int result=m10v_library_render(&paired,state,slot,date,seed,scratch,scratch_bytes);
    gr2_chroma_shuffle(im->u,cn,1);
    return result;
}
