/* M10V camera implementation. Reference data attribution in 5207-reference.json.
 * Input is an assumed display-referred domain, NOT recovered scene radiance. */
#include "film_5207.h"
#include "film_5207_data.h"
#include "film_harman.h"

static uint8_t clip(int x){return (uint8_t)(x<0?0:x>255?255:x);}
static int roundq(int x,int bits){int h=1<<(bits-1);return x>=0?(x+h)>>bits:-((-x+h)>>bits);}
static uint32_t random32(uint32_t x){x^=x>>16;x*=0x7feb352du;x^=x>>15;x*=0x846ca68bu;return x^(x>>16);}
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
static int noise(uint32_t x,uint32_t y,uint32_t seed,uint32_t size){
    uint32_t scale=1u<<size,xx=x>>size,yy=y>>size;
    uint32_t dx=x&(scale-1),dy=y&(scale-1);
    int a=(int)(random32(seed^xx*0x9e3779b9u^yy*0x85ebca6bu)&255)-128;
    int b=(int)(random32(seed^(xx+1)*0x9e3779b9u^yy*0x85ebca6bu)&255)-128;
    int c=(int)(random32(seed^xx*0x9e3779b9u^(yy+1)*0x85ebca6bu)&255)-128;
    int d=(int)(random32(seed^(xx+1)*0x9e3779b9u^(yy+1)*0x85ebca6bu)&255)-128;
    return (a*(int)(scale-dx)*(int)(scale-dy)+b*(int)dx*(int)(scale-dy)+c*(int)(scale-dx)*(int)dy+d*(int)dx*(int)dy)>>(size*2);
}
static uint32_t leak(uint32_t px,uint32_t py,const m10v_film_effects *e,uint32_t seed){
    if(!e->leak_gain)return 0;
    uint32_t position=e->leak_position;
    if(position==5)position=random32(seed^0x5207u)%5;
    uint32_t d=position==0?px:position==1?255-px:position==2?py:position==3?255-py:px+py;
    uint32_t span=24+e->leak_spread*24;
    if(d>=span)return 0;
    static const uint32_t reciprocal[9]={699050,349525,233016,174762,139810,116508,99864,87381,77672};
    uint32_t weight=((span-d)*reciprocal[e->leak_spread])>>16;weight=weight*weight>>8;
    int ripple=noise(px>>1,py>>1,seed^0xa1734u,3);
    return weight*e->leak_gain*(uint32_t)(192+ripple/4)/(8*256);
}
static uint32_t divide(uint32_t n,uint32_t d){uint32_t q=0,r=0;for(int i=31;i>=0;i--){r=(r<<1)|((n>>i)&1);if(r>=d){r-=d;q|=1u<<i;}}return q;}
void m10v_5207_texture_q8(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed,uint32_t color){
    if(!color&&!grain&&!e->leak_gain)return;
    uint32_t sx=divide(256u<<16,im->width),sy=divide(256u<<16,im->height);
    uint32_t grain_sx=divide(6000u<<12,im->width),grain_sy=divide(4000u<<12,im->height);
    uint32_t leak_seed=e->leak_variation?seed:0x5207250du;
    for(uint32_t y=0;y<im->height;y++)for(uint32_t x=0;x<im->width;x+=2){
        uint32_t at=y*im->stride+x;int cb=(int)im->chroma[at]-128,cr=(int)im->chroma[at+1]-128;
        uint8_t mapped[2][3],original[2][3];
        for(uint32_t k=0;k<2;k++){
            int v=im->y[at+k];uint8_t rgb[3]={clip(v+roundq(91881*cr,16)),clip(v-roundq(22554*cb+46802*cr,16)),clip(v+roundq(116130*cb,16))};
            for(uint32_t c=0;c<3;c++)original[k][c]=rgb[c];
            uint32_t light=leak(((x+k)*sx)>>16,(y*sy)>>16,e,leak_seed);
            /* Bounded warm exposure approximation in the assumed encoded input. */
            static const uint32_t transmission[3]={256,112,36};
            for(uint32_t c=0;c<3;c++)rgb[c]=clip(rgb[c]+(int)(light*transmission[c]*(255-rgb[c])>>16));
            if(color==1)m10v_5207_rgb(rgb,mapped[k]);else if(color>=2)m10v_harman_rgb(color-2,rgb,mapped[k]);else for(uint32_t c=0;c<3;c++)mapped[k][c]=rgb[c];
            if(grain){
                uint32_t gx=((x+k)*grain_sx)>>12,gy=(y*grain_sy)>>12;
                uint32_t h=random32(seed^gx*0x9e3779b9u^gy*0x85ebca6bu);
                int n=noise(gx,gy,seed,e->grain_size)+((int)(h&255)-128)/3;
                int lum=(54*mapped[k][0]+183*mapped[k][1]+19*mapped[k][2])>>8;
                int weight=32+(lum<128?lum:255-lum);
                int delta=n*(int)grain*weight/(128*24*256);
                for(uint32_t c=0;c<3;c++)mapped[k][c]=clip((int)mapped[k][c]+delta+((int)((h>>(c*8))&255)-128)*(int)grain/(192*256));
            }
            int r=mapped[k][0],g=mapped[k][1],b=mapped[k][2];
            if(!color){r-=original[k][0];g-=original[k][1];b-=original[k][2];}
            im->y[at+k]=clip((color?0:im->y[at+k])+roundq(19595*r+38470*g+7471*b,16));
        }
        int r=mapped[0][0]+mapped[1][0],g=mapped[0][1]+mapped[1][1],b=mapped[0][2]+mapped[1][2];
        if(!color){r-=original[0][0]+original[1][0];g-=original[0][1]+original[1][1];b-=original[0][2]+original[1][2];}
        if(color||e->leak_gain){im->chroma[at]=clip((color?128:im->chroma[at])+roundq(-11059*r-21709*g+32768*b,17));
        im->chroma[at+1]=clip((color?128:im->chroma[at+1])+roundq(32768*r-27439*g-5329*b,17));}
    }
}

void m10v_5207_texture(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed,uint32_t color){m10v_5207_texture_q8(im,e,grain<<8,seed,color);}
void m10v_5207_render(m10v_library_image *im,const m10v_film_effects *e,uint32_t grain,uint32_t seed){m10v_5207_texture(im,e,grain,seed,1);}
