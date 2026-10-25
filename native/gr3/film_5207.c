/* M10V camera implementation. Reference data attribution in 5207-reference.json.
 * Input is an assumed display-referred domain, NOT recovered scene radiance. */
#include "film_5207.h"
#ifndef M10V_TEXTURE_NEON
#define M10V_TEXTURE_NEON 0
#endif
#if M10V_FILM_COLOR_CANDIDATE
static const uint8_t m10v_5207_lut[3375][3] __attribute__((used));
#endif
#include "film_5207_data.h"
#include "film_harman.h"
#include "m10v_color_cache.h"
#if M10V_TEXTURE_NEON
#include "m10v_texture_accel.h"
#endif
#if M10V_FILM_COLOR_CANDIDATE
#include "m10v_film_color_candidates.h"
/* Retain the base payload for existing readback/provenance validation. */
#define m10v_5207_lut m10v_5207_candidate_lut
#endif

static uint8_t clip(int x){return (uint8_t)(x<0?0:x>255?255:x);}
static int roundq(int x,int bits){int h=1<<(bits-1);return x>=0?(x+h)>>bits:-((-x+h)>>bits);}
void m10v_5207_rgb(const uint8_t rgb[3],uint8_t out[3]){
    /* Exact tetrahedral barycentric weights. Sorting the fractions with
     * their axis steps keeps the same four vertices as the former loops.
     * Expanding telescoping differences yields nonnegative weights summing
     * to 255, so totals stay in [0,65025]; +127 and /255 are unchanged.
     * Scalars avoid per-pixel stack arrays and nested loops on ARM -Os. */
    uint32_t q0=(uint32_t)rgb[0]*14,q1=(uint32_t)rgb[1]*14,q2=(uint32_t)rgb[2]*14;
    uint32_t p0=q0/255,p1=q1/255,p2=q2/255;
    if(p0>13)p0=13;if(p1>13)p1=13;if(p2>13)p2=13;
    uint32_t f0=q0-p0*255,f1=q1-p1*255,f2=q2-p2*255;
    uint32_t s0=225,s1=15,s2=1,t;
    if(f1>f0){t=f0;f0=f1;f1=t;t=s0;s0=s1;s1=t;}
    if(f2>f0){t=f0;f0=f2;f2=t;t=s0;s0=s2;s2=t;}
    if(f2>f1){t=f1;f1=f2;f2=t;t=s1;s1=s2;s2=t;}
    uint32_t index=(p0*15+p1)*15+p2;
    const uint8_t *a=m10v_5207_lut[index],*b=m10v_5207_lut[index+s0],*c=m10v_5207_lut[index+s0+s1],*d=m10v_5207_lut[index+(225+15+1)];
    uint32_t w0=255-f0,w1=f0-f1,w2=f1-f2;
    out[0]=clip((int)((w0*a[0]+w1*b[0]+w2*c[0]+f2*d[0]+127)/255));
    out[1]=clip((int)((w0*a[1]+w1*b[1]+w2*c[1]+f2*d[1]+127)/255));
    out[2]=clip((int)((w0*a[2]+w1*b[2]+w2*c[2]+f2*d[2]+127)/255));
}
/* Exact CPU color fallback only. Legacy texture arguments remain ABI-compatible;
 * native ISP grain owns all grain and light leak has been retired. */
static void color_texture(m10v_library_image *im,uint32_t color,void *memory,uint32_t *stats){
#if M10V_TEXTURE_NEON
    /* Immutable retired ABI placeholders avoid a per-call stack clear and
     * its freestanding ARM memclr runtime helper. */
    static const m10v_texture_block_params block={0};
    const uint8_t *table=color==1?&m10v_5207_lut[0][0]:m10v_harman_texture_table(color-2);
#endif
    for(uint32_t y=0;y<im->height;y++)for(uint32_t x=0;x<im->width;x+=2){
        uint32_t at=y*im->stride+x;
#if M10V_TEXTURE_NEON
        if(x+8<=im->width){
            int hits=m10v_texture_block8_cached(im->y+at,im->chroma+at,table,&block,memory);
            if(hits>=0){if(stats){stats[0]+=8;stats[1]+=(uint32_t)hits;}x+=6;continue;}
            if(stats)stats[2]|=8;
        }
#endif
        int cb=(int)im->chroma[at]-128,cr=(int)im->chroma[at+1]-128;
        uint8_t mapped[2][3];
        for(uint32_t k=0;k<2;k++){
            int v=im->y[at+k];uint8_t rgb[3]={clip(v+roundq(91881*cr,16)),clip(v-roundq(22554*cb+46802*cr,16)),clip(v+roundq(116130*cb,16))};
            uint32_t key=(uint32_t)rgb[0]|((uint32_t)rgb[1]<<8)|((uint32_t)rgb[2]<<16);
            uint32_t *entry=memory?m10v_color_cache_slot(memory,key):0;
            if(entry&&entry[0]==(key|0x01000000u)){m10v_color_cache_read(entry,mapped[k]);if(stats)stats[1]++;}else{
                if(color==1)m10v_5207_rgb(rgb,mapped[k]);else m10v_harman_rgb(color-2,rgb,mapped[k]);
                if(entry)m10v_color_cache_write(entry,key,mapped[k]);
            }
            im->y[at+k]=clip(roundq(19595*mapped[k][0]+38470*mapped[k][1]+7471*mapped[k][2],16));
        }
        int r=mapped[0][0]+mapped[1][0],g=mapped[0][1]+mapped[1][1],b=mapped[0][2]+mapped[1][2];
        im->chroma[at]=clip(128+roundq(-11059*r-21709*g+32768*b,17));
        im->chroma[at+1]=clip(128+roundq(32768*r-27439*g-5329*b,17));
    }
}
void m10v_5207_texture_cached_stats_q8(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed,uint32_t color,void *memory,uint32_t stats[3]){
    (void)e;(void)grain;(void)seed;
    if(stats){stats[0]=0;stats[1]=0;stats[2]=(memory?4u:0u)|(M10V_TEXTURE_NEON?2u:0u);}
    if(!color)return;
    memory=m10v_color_cache_prepare(memory,im);
    if(stats&&memory)stats[2]|=1;
    color_texture(im,color,memory,stats);
}
void m10v_5207_texture_cached_q8(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed,uint32_t color,void *memory){m10v_5207_texture_cached_stats_q8(im,e,grain,seed,color,memory,0);}

void m10v_5207_texture_q8(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed,uint32_t color){m10v_5207_texture_cached_q8(im,e,grain,seed,color,0);}

void m10v_5207_texture(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed,uint32_t color){m10v_5207_texture_q8(im,e,grain<<8,seed,color);}
void m10v_5207_render(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed){m10v_5207_texture(im,e,grain,seed,1);}
