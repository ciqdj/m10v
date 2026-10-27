#ifndef M10V_ANIME_H
#define M10V_ANIME_H
#include "m10v_library.h"

/* Post-ISP only. Existing image ABI is Y plus interleaved CbCr, both full
 * height with the same even stride (4:2:2), not a half-height 4:2:0 plane.
 * Width/height bounds deliberately match m10v_library.c. No LUT/color pass. */
static inline uint32_t m10v_anime_workspace(uint32_t width,uint32_t mode) {
    if (!mode || mode>3 || width<2 || width>6144 || (width&1u)) return 0;
    /* Three original rows from each plane, byte aligned; no whole-frame copy. */
    return width*6u;
}
static inline int m10v_anime_range(const void *p,uint32_t n) {
    return p && (uintptr_t)p<=UINTPTR_MAX-n;
}
static inline int m10v_anime_overlap(const void *a,uint32_t an,const void *b,uint32_t bn) {
    return (uintptr_t)a<(uintptr_t)b+bn && (uintptr_t)b<(uintptr_t)a+an;
}
static inline uint32_t m10v_anime_delta(uint32_t a,uint32_t b) {
    return a>b?a-b:b-a;
}
static inline uint8_t m10v_anime_quant(uint32_t a,uint32_t shift) {
    uint32_t v=((a+(1u<<(shift-1)))>>shift)<<shift;
    return (uint8_t)(v>255?255:v);
}
/* A fixed-weight bilateral approximation. Rejecting a neighbor substitutes
 * the center, so normalization is always eight (no division helper). */
static inline uint32_t m10v_anime_smooth(uint32_t c,uint32_t l,uint32_t r,uint32_t u,uint32_t d) {
    return (4*c+(m10v_anime_delta(c,l)<=24?l:c)+
        (m10v_anime_delta(c,r)<=24?r:c)+(m10v_anime_delta(c,u)<=24?u:c)+
        (m10v_anime_delta(c,d)<=24?d:c)+4)>>3;
}
static inline int m10v_anime_render_planes(m10v_library_image *image,uint32_t mode,void *scratch,uint32_t scratch_bytes,uint32_t half_chroma) {
    /* In particular, a poisoned image/scratch is legal when disabled. */
    if (!mode) return 0;
    if (mode>3 || !image) return -1;
    uint32_t w=image->width,h=image->height,stride=image->stride;
    uint32_t needed=m10v_anime_workspace(w,mode);
    if (!needed || !h || h>4096 || (half_chroma && (h&1u)) || stride<w || stride>16384 || (stride&1u)) return -1;
    uint32_t bytes=stride*h,chroma_bytes=stride*(half_chroma?h>>1:h);
    if (image->y_bytes<bytes || image->chroma_bytes<chroma_bytes || scratch_bytes<needed ||
        !m10v_anime_range(image,sizeof(*image)) ||
        !m10v_anime_range(image->y,image->y_bytes) ||
        !m10v_anime_range(image->chroma,image->chroma_bytes) ||
        !m10v_anime_range(scratch,scratch_bytes)) return -1;
    /* Reject aliases across the complete declared buffer extents, including
     * their padding/tails. All checks finish before the first scratch write. */
    if (m10v_anime_overlap(image->y,image->y_bytes,image->chroma,image->chroma_bytes) ||
        m10v_anime_overlap(image->y,image->y_bytes,image,sizeof(*image)) ||
        m10v_anime_overlap(image->chroma,image->chroma_bytes,image,sizeof(*image)) ||
        m10v_anime_overlap(scratch,scratch_bytes,image,sizeof(*image)) ||
        m10v_anime_overlap(scratch,scratch_bytes,image->y,image->y_bytes) ||
        m10v_anime_overlap(scratch,scratch_bytes,image->chroma,image->chroma_bytes)) return -1;
    /* Each plane has its own original-row ring. Processing chroma separately
     * also supports true 4:2:0 without repeating chroma or losing vertical Y
     * neighbors at each two-row boundary. */
    for (uint32_t plane=0;plane<2;plane++) {
        if (plane && mode==1) continue;
        uint32_t rows=(plane && half_chroma)?h>>1:h;
        uint8_t *pixels=plane?image->chroma:image->y;
        uint8_t *ring=(uint8_t *)scratch+plane*3*w;
        for (uint32_t row=0;row<rows;row++) {
            uint32_t first=row?row+1:0,last=row+1<rows?row+1:row;
            for (uint32_t r=first;r<=last;r++) {
                uint32_t base=(r%3)*w,at=r*stride;
                for (uint32_t x=0;x<w;x++) ring[base+x]=pixels[at+x];
            }
            uint8_t *cur=ring+(row%3)*w,*up=ring+((row?row-1:row)%3)*w;
            uint8_t *down=ring+((row+1<rows?row+1:row)%3)*w;
            for (uint32_t x=0;x<w;x++) {
                uint32_t step=plane?2:1;
                uint32_t left=x>=step?x-step:x,right=x+step<w?x+step:x,at=row*stride+x;
                uint32_t value=cur[x];
                if (mode==2) {
                    pixels[at]=m10v_anime_quant(value,5);
                    continue;
                }
                uint32_t edge=m10v_anime_delta(cur[left],cur[right])+m10v_anime_delta(up[x],down[x]);
                if (mode==1) {
                    uint32_t ink=edge>24?(edge-24)>>1:0;
                    if (ink>96) ink=96;
                    pixels[at]=(uint8_t)((value*(256-ink))>>8);
                } else {
                    value=m10v_anime_quant(m10v_anime_smooth(value,cur[left],cur[right],up[x],down[x]),4);
                    uint32_t contour=(!plane && edge>20)?(edge-20)>>3:0;
                    if (contour>24) contour=24;
                    pixels[at]=(uint8_t)((value*(256-contour))>>8);
                }
            }
        }
    }
    return 0;
}
static inline int m10v_anime_render(m10v_library_image *image,uint32_t mode,void *scratch,uint32_t scratch_bytes) {
    return m10v_anime_render_planes(image,mode,scratch,scratch_bytes,0);
}
/* 4:2:0 thumbnail: full-height luma, half-height interleaved CbCr, same
 * stride; enabled modes require even height. Workspace remains 6*width. */
static inline int m10v_anime_render420(m10v_library_image *image,uint32_t mode,void *scratch,uint32_t scratch_bytes) {
    return m10v_anime_render_planes(image,mode,scratch,scratch_bytes,1);
}
#endif
