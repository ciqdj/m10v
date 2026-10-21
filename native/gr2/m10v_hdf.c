/* GR II BE32 coefficient primitive. Original Clarity still owns all pixels. */
#include "m10v_hdf.h"
#include "m10v_capture.h"
#include "../gr3/m10v_sd_library.h"
static const uint16_t gains[3][GR2_HDF_BANDS]={
 {820,740,700,700,740,840,940,1024,1024,1024,1024},
 {680,560,500,500,540,680,860,960,1024,1024,1024},
 {540,400,330,330,380,540,760,920,1024,1024,1024}
};
static uint32_t node(uint32_t i){
 if(i>255u)i=255u;
 return 8u*i+(i>=64u)+(i>=128u)+(i>=192u)+(i>=255u);
}
static uint32_t identity(uint32_t i){
 uint32_t segment=i>>3,fraction=i&7u;
 return (node(segment)*(8u-fraction)+node(segment+1u)*fraction)>>3;
}
int gr2_hdf_prepare_bands(uint16_t *workspace,uint32_t bytes,uint32_t strength){
 if(!strength)return 0;
 uintptr_t base=(uintptr_t)workspace;
 if(strength>3u||!base||(base&31u)||bytes<GR2_HDF_WORKSPACE_BYTES||
    bytes>0xe5800u||base>UINT32_MAX-bytes)return -1;
 const uint16_t *source=workspace+3u*4096u;
 /* Validate the entire source before publication. Stock positive Clarity/HDR
  * may use a nonlinear fourth curve and must never be mistaken for identity. */
 for(uint32_t i=0;i<2048u;i++){
  uint32_t value=identity(i);
  if(source[2048u+i]!=value||(i&&source[2048u-i]!=4096u-value))return -1;
 }
 if(source[0]!=source[1])return -1;
 for(uint32_t band=0;band<GR2_HDF_BANDS;band++){
  uint16_t *out=workspace+GR2_HDF_CURVE_OFFSET/2u+band*4096u;
  uint32_t gain=gains[strength-1u][band];
  for(uint32_t i=0;i<2048u;i++){
   uint32_t value=((uint32_t)source[2048u+i]*gain)>>10;
   out[2048u+i]=(uint16_t)value;
   if(i)out[2048u-i]=(uint16_t)(4096u-value);
  }
  out[0]=out[1];
 }
 return 1;
}

_Static_assert(sizeof(gr2_hdf_frame)==16,"GR II independent HDF snapshot ABI");
static void copy(void *out,const void *in,uint32_t bytes){
 for(uint32_t i=0;i<bytes;i++)((uint8_t *)out)[i]=((const uint8_t *)in)[i];
}
int gr2_hdf_frame_freeze(uint8_t *context,uint32_t strength,uint32_t sequence){
 if(strength>3u||gr2_image_owner_bytes(context)!=GR2_IMAGE_BODY_BYTES)return 0;
 uint8_t *tail=context+GR2_HDF_FRAME_OFFSET;
 for(uint32_t i=0;i<16u;i++)if(tail[i])return 0;
 gr2_hdf_frame next={0x47324844u,0x10000u|strength,sequence,0};
 next.crc=m10v_sd_crc((const uint8_t *)&next,12);
 /* Caller retains its stock image reference. Publish magic after the value. */
 copy(tail+4,(const uint8_t *)&next+4,12);copy(tail,&next,4);return 1;
}
int gr2_hdf_frame_read(const uint8_t *context,gr2_hdf_frame *out){
 if(gr2_image_owner_bytes(context)!=GR2_IMAGE_BODY_BYTES)return 0;
 uintptr_t a=(uintptr_t)out,b=(uintptr_t)context-8u;
 if(!a||(a&3u)||a>UINT32_MAX-16u||(a<b+GR2_IMAGE_BODY_BYTES+8u&&b<a+16u))return 0;
 gr2_hdf_frame next;copy(&next,context+GR2_HDF_FRAME_OFFSET,16);
 if(next.magic!=0x47324844u||(next.control&~3u)!=0x10000u||
    next.crc!=m10v_sd_crc((const uint8_t *)&next,12))return 0;
 copy(out,&next,16);return 1;
}

static uint32_t word(uint32_t address){return *(const volatile uint32_t *)(uintptr_t)address;}
/* A synchronous caller must retain the original tag20 BUFF handle. This
 * verifies a live singleton MPF lease; it does not lock against its release. */
uint32_t gr2_hdf_workspace_bytes(const void *data){
 uint32_t pointer=(uint32_t)(uintptr_t)data;
 if(!pointer||(pointer&31u)||word(0xa0129c20u)>>24>4u)return 0;
 uint32_t index=word(0xa06bcc6cu+4u*0x20u);
 if(index>=69u)return 0;
 uint32_t definition=0xa0112048u+44u*index;
 if(*(const volatile uint8_t *)(uintptr_t)definition!=0x20u||word(definition+4u)!=0xe5800u||word(definition+8u)!=32u)return 0;
 uint32_t record=0xa06bc708u+20u*index,head=word(record),heads=0xa05fb0ccu;
 uint32_t maximum=*(const volatile uint16_t *)(uintptr_t)0xa00b5bfcu;
 if(!maximum||maximum>64u||head<heads+28u||head>heads+28u*maximum||(head-heads)%28u)return 0;
 uint32_t id=(head-heads)/28u;
 if(word(head)!=0x4d504c20u||*(const volatile uint8_t *)(uintptr_t)(head+4u)!=1u||
    *(const volatile uint16_t *)(uintptr_t)(head+20u)!=id||word(head+8u)!=0xe5800u||word(head+12u)!=0xe5800u)return 0;
 uint32_t table=word(0xa00b5bdcu);
 if((table&3u)||!table||table>UINT32_MAX-24u*id)return 0;
 uint32_t kernel=table+24u*(id-1u),base=word(record+4u),end=word(0xa0129c2cu);
 if(base<0xa0900000u||end>0xbfdc0000u||base>end||0xe5800u>end-base||
    pointer!=((base&0x1fffffffu)|0x20000000u))return 0;
 if(*(const volatile uint16_t *)(uintptr_t)kernel!=0xffffu||word(kernel+4u)!=kernel+4u||
    word(kernel+12u)!=0xe5800u||word(kernel+16u)!=0xe5800u||word(kernel+20u)!=base)return 0;
 return 0xe5800u;
}
