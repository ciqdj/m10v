#include "m10v_isp_frame_color.h"
typedef void (*pack_fn)(const void *,const uint16_t *,uint16_t *,void *,uint32_t);
static int signed_field(uint16_t v,uint32_t bits){
    uint32_t mask=(1u<<bits)-1u;
    return (int)((v&mask)^(1u<<(bits-1)))-(int)(1u<<(bits-1));
}
static int compose(const uint16_t *src,const int16_t *relative,int *out,uint32_t bits,uint32_t shift,int left){
    for(uint32_t r=0;r<3;r++)for(uint32_t c=0;c<3;c++){
        int sum=0;
        for(uint32_t k=0;k<3;k++)sum+=left?relative[r*3+k]*signed_field(src[k*3+c],bits):signed_field(src[r*3+k],bits)*relative[k*3+c];
        int v=(sum+(1<<(shift-1)))>>shift;
        if(v<-(1<<(bits-1))||v>=(1<<(bits-1)))return 0;
        out[r*3+c]=v;
    }
    return 1;
}
int m10v_isp_frame_apply(const void *gamma,void *frame,const m10v_isp_frame_target *t,uint32_t cs){
    if(!gamma||!frame||!t||cs>1)return 0;
    uint8_t *f=frame;const uint8_t *g=gamma;
    int matrix[9],post[9];
    uint16_t mapped[4][256];
    if(!compose((const uint16_t *)(f+0x140),t->matrix_q13,matrix,12,13,1)||
       !compose((const uint16_t *)(f+0x12a0),t->post_q9,post,9,9,0))return 0;
    for(uint32_t c=0;c<3;c++)for(uint32_t i=0;i<256;i++){
        if(t->curves[c][i]>16383||(i&&t->curves[c][i]<t->curves[c][i-1]))return 0;
        uint32_t v=((const uint16_t *)(g+0x2a08+c*512))[i],j=v>>6,frac=v&63;
        /* Original curve endpoint is 16384; original converter clamps all
         * indices above 254 to the final sample as well. */
        mapped[c][i]=(uint16_t)(j>=255?t->curves[c][255]:
            (t->curves[c][j]*(64-frac)+t->curves[c][j+1]*frac+32)>>6);
    }
    for(uint32_t i=0;i<256;i++)mapped[3][i]=(uint16_t)((77u*mapped[0][i]+150u*mapped[1][i]+29u*mapped[2][i])>>8);
    /* All validation precedes frame mutation. Preserve unrelated register bits. */
    for(uint32_t i=0;i<9;i++){
        uint16_t *m=(uint16_t *)(f+0x140),*p=(uint16_t *)(f+0x12a0);
        m[i]=(uint16_t)((m[i]&0xf000u)|((uint32_t)matrix[i]&4095u));
        p[i]=(uint16_t)((p[i]&0xfe00u)|((uint32_t)post[i]&511u));
    }
    /* Exact original hardware table packer: its r0 argument is unused. No
     * cloned object or restoration window is needed; only frame banks change.
     * 2048-byte local workspace, independent of image size and burst depth. */
    for(uint32_t c=0;c<4;c++)((pack_fn)0x536e89ecu)(gamma,mapped[c],
        (uint16_t *)(f+0x4888+c*512),f+0x2688+c*2048,cs);
    return 1;
}
