#ifndef M10V_UNIVERSAL_HALATION_KERNEL_H
#define M10V_UNIVERSAL_HALATION_KERNEL_H
/* Display-domain, neutral light effects, not a measured film-emulsion model.
 * Uses two bounded u16 grids inside the caller's preflighted 4*cells scratch.
 * Separate source/blur/compose phases prevent feedback from modified pixels. */
static void halo_horizontal(uint16_t *a,uint16_t *b,uint32_t w,uint32_t h,uint32_t spread){
    uint32_t radius=4+3u*spread,denominator=2*radius+1;
    static const uint32_t reciprocal[9]={477218588u,286331153u,204522252u,159072862u,130150524u,110127366u,95443717u,84215045u,75350303u};
    for(uint32_t pass=0;pass<2;++pass){
        for(uint32_t y=0;y<h;++y){
            const uint16_t *row=a+y*w;uint16_t *dst=b+y*w;
            uint32_t sum=(radius+1)*row[0];
            for(uint32_t k=1;k<=radius;++k)sum+=row[k<w?k:w-1];
            for(uint32_t x=0;x<w;++x){
                uint32_t q=(uint32_t)(((uint64_t)sum*reciprocal[spread])>>32);
                if(sum-q*denominator>=denominator)++q;
                dst[x]=(uint16_t)q;
                uint32_t left=x>=radius?x-radius:0,right=x+radius+1;
                sum-=row[left];sum+=row[right<w?right:w-1];
            }
        }
        for(uint32_t i=0;i<w*h;++i)a[i]=b[i];
    }
}
static void m10v_universal_halation_source(m10v_library_image *im,const m10v_slot *v,uint8_t *scratch,uint32_t gw,uint32_t gh,uint32_t shift){
    uint16_t *a=(uint16_t *)scratch,*b=a+gw*gh;
    uint32_t step=1u<<shift,gate=176+8u*v->halo_threshold,active=0;
    for(uint32_t gy=0;gy<gh;++gy)for(uint32_t gx=0;gx<gw;++gx){
        uint32_t sum=0,peak=0;
        for(uint32_t dy=0;dy<step;++dy){
            uint32_t row=(gy<<shift)+dy;if(row>=im->height)break;
            for(uint32_t dx=0;dx<step;++dx){
                uint32_t x=(gx<<shift)+dx;if(x>=im->width)break;
                uint32_t light=im->y[row*im->stride+x],excess=light>gate?light-gate:0,energy=excess*excess*8;
                sum+=energy;if(energy>peak)peak=energy;
            }
        }
        uint32_t e=(sum>>(2*shift))+(shift?peak>>4:0);
        a[gy*gw+gx]=(uint16_t)e;active|=e;
    }
    if(!active)return;
    if(v->halo_profile==M10V_HALO_STREAK)halo_horizontal(a,b,gw,gh,v->halo_spread);
    else energy_blur(a,b,gw,gh,2+v->halo_spread,1);
}
static void m10v_universal_halation_compose(m10v_library_image *im,const m10v_slot *v,const uint8_t *scratch,uint32_t gw,uint32_t gh,uint32_t shift){
    const uint16_t *a=(const uint16_t *)scratch;
    for(uint32_t row=0;row<im->height;++row)for(uint32_t x=0;x<im->width;++x){
        uint32_t at=row*im->stride+x,light=im->y[at],protect=(255-light)*4;
        if(protect>255)protect=255;
        uint32_t lift=(energy_sample(a,gw,gh,x,row,shift)*v->halo_gain*protect)>>14;
        if(lift>96)lift=96;
        im->y[at]=energy_clamp((int)(light+lift));
    }
}
#endif
