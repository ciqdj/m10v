/* Frozen baseline f6078af; compare active, dark, tiny-source and padded images. */
static void reference_phoenix_source(const m10v_library_image *im,const m10v_slot *v,uint8_t *scratch,uint32_t gw,uint32_t gh,uint32_t shift){
    uint16_t *a=(uint16_t *)scratch,*b=a+gw*gh;
    uint32_t step=1u<<shift,gate=176+8u*v->halo_threshold;
    for(uint32_t gy=0;gy<gh;++gy)for(uint32_t gx=0;gx<gw;++gx){
        uint32_t sum=0,peak=0;
        for(uint32_t dy=0;dy<step;++dy){
            uint32_t row=(gy<<shift)+dy;if(row>=im->height)break;
            for(uint32_t dx=0;dx<step;++dx){
                uint32_t x=(gx<<shift)+dx;if(x>=im->width)break;
                uint32_t light=im->y[row*im->stride+x];
                uint32_t excess=light>gate?light-gate:0,energy=excess*excess*8;
                sum+=energy;if(energy>peak)peak=energy;
            }
        }
        /* Preserve tiny lamps at step16 without another image scan. A small
         * bounded peak contribution supplements integrated cell energy; it
         * is not a claim of calibrated source area or a measured near PSF.
         * Max 49928 + 49928/16 < 65536, including partial edge cells. */
        a[gy*gw+gx]=(uint16_t)((sum>>(2*shift))+(shift?peak>>4:0));
    }
    energy_blur(a,b,gw,gh,1+v->halo_spread,1);
}
static void reference_phoenix_compose(m10v_library_image *im,const m10v_slot *v,const uint8_t *scratch,uint32_t gw,uint32_t gh,uint32_t shift){
    const uint16_t *a=(const uint16_t *)scratch;
    for(uint32_t row=0;row<im->height;++row)for(uint32_t x=0;x<im->width;x+=2){
        uint32_t at=row*im->stride+x,y0=im->y[at],y1=im->y[at+1],peak=y0>y1?y0:y1;
        /* Shared chroma must not tint either member of a clipped bright pair. */
        if(peak>=240)continue;
        uint32_t protect=(255-peak)*4;if(protect>255)protect=255;
        uint32_t red=(energy_sample(a,gw,gh,x,row,shift)*v->halo_gain*protect)>>12;
        if(!red)continue;
        uint32_t limit=6u*v->halo_gain;if(red>limit)red=limit;
        /* Orange shoulder: more green than 800T, with a six-level red cap
         * per gain step (800T permits 192). All products fit uint32_t. */
        uint32_t green=red>>2,lift=(77*red+150*green+128)>>8;
        im->y[at]=clamp((int)(y0+lift));im->y[at+1]=clamp((int)(y1+lift));
        im->chroma[at]=clamp((int)im->chroma[at]-(int)((43*red+85*green+128)>>8));
        im->chroma[at+1]=clamp((int)im->chroma[at+1]+(int)((128*red-107*green+128)>>8));
    }
}
