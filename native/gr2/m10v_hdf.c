/* GR II BE32 coefficient primitive. Original Clarity still owns all pixels. */
#include "m10v_hdf.h"
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
