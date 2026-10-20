#include "m10v_ui.h"
#include "../gr3/m10v_film_card.h"
/* The shared artwork renderer emits 0xAABBGGRR words for GR III's little
 * endian RGBA memory. Convert explicitly on BE32 before any GR II-specific
 * OSD/indexed/YUV upload. This function does not submit a screen bitmap. */
int gr2_film_card_rgba(uint8_t *out,uint32_t capacity,uint32_t film,uint32_t slot,uint32_t selected){
    uint32_t bytes=M10V_CARD_PIXELS*4u;
    if(!out||((uintptr_t)out&3)||capacity<bytes||(uintptr_t)out>UINTPTR_MAX-bytes||film<1||film>78||slot>=5)return 0;
    if(m10v_film_card_render((uint32_t *)out,film,slot,selected))return 0;
    for(uint32_t i=0;i<bytes;i+=4){uint8_t a=out[i],b=out[i+1];out[i]=out[i+3];out[i+1]=out[i+2];out[i+2]=b;out[i+3]=a;}
    return 1;
}
