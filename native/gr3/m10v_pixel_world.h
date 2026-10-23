/* Original Pixel World effect. Full-range Y/CbCr 4:2:2, about 160 cells
 * along the long edge. Four bounded source samples per cell reduce aliasing.
 * In-place, allocation-free; source samples are read before writing each cell.
 * The validated caller owns JPEG planes; padding and RAW are never touched. */
#ifndef M10V_PIXEL_WORLD_H
#define M10V_PIXEL_WORLD_H
static uint8_t m10v_pixel_level(int value){
 value=(value+8)&~15;return (uint8_t)(value<0?0:value>255?255:value);
}
static void m10v_pixel_world_render(m10v_library_image *image){
 uint32_t longest=image->width>image->height?image->width:image->height;
 uint32_t step=((longest+319u)/320u)*2u;if(step<2)step=2;
 for(uint32_t top=0;top<image->height;top+=step){
  uint32_t bottom=top+step;if(bottom>image->height)bottom=image->height;
  for(uint32_t left=0;left<image->width;left+=step){
   uint32_t right=left+step;if(right>image->width)right=image->width;
   uint32_t w=right-left,h=bottom-top,sy=0,scb=0,scr=0;
   for(uint32_t j=0;j<2;j++)for(uint32_t i=0;i<2;i++){
    uint32_t x=left+((w*(1+2*i))>>2),y=top+((h*(1+2*j))>>2);
    uint32_t at=y*image->stride+x,uv=at&~1u;
    sy+=image->y[at];scb+=image->chroma[uv];scr+=image->chroma[uv+1];
   }
   uint8_t light=m10v_pixel_level((int)((sy+2)>>2));
   uint8_t cb=m10v_pixel_level(128+(((int)((scb+2)>>2)-128)*9)/8);
   uint8_t cr=m10v_pixel_level(128+(((int)((scr+2)>>2)-128)*9)/8);
   for(uint32_t y=top;y<bottom;y++)for(uint32_t x=left;x<right;x+=2){
    uint32_t at=y*image->stride+x;image->y[at]=image->y[at+1]=light;
    image->chroma[at]=cb;image->chroma[at+1]=cr;
   }
  }
 }
}
#endif
