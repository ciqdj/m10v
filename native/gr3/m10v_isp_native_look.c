#include "m10v_isp_native_look.h"
#include "m10v_isp_multiaxis.h"
#include "m10v_library.h"
#include "m10v_isp_native_look_profiles.h"
#include <stddef.h>
_Static_assert(sizeof(m10v_isp_native_look)==1600,"bounded recipe color storage");
_Static_assert(sizeof(native_frame_packed)==48,"lossless profile storage");
static int supported(uint32_t film,uint32_t exposure){return film>=33&&film<=71&&exposure<3&&(film==68||!exposure);}
int m10v_isp_native_look_prepare(m10v_isp_native_look *s,uint32_t film,uint32_t exposure,uint32_t generation){
 if(!s)return 0;
 s->magic=M10V_ISP_NATIVE_LOOK_MAGIC;s->version=M10V_ISP_NATIVE_LOOK_VERSION;
 s->generation=generation;s->film=film;s->exposure=exposure;
 s->status=M10V_NATIVE_LOOK_REJECTED;s->applied_frame=0;
 if(!generation||!supported(film,exposure))return 0;
 if(film>=34&&film<=65){uint16_t knots[99];if(m10v_library_tables(film,s->target.matrix_q13,s->target.post_q9,&s->target.curves[0][0],knots))return 0;}
 else {
  const native_frame_packed *t=film==33?&native_800t_frame:film==66?&native_5207_frame:film==67?&native_phoenix_frame:film==68?&native_red_frame[exposure]:&native_curated_frame[film-69];
  for(uint32_t i=0;i<9;i++){s->target.matrix_q13[i]=t->matrix[i];s->target.post_q9[i]=t->post[i];}
  for(uint32_t c=0;c<3;c++){
   const uint8_t *stream=native_curve_stream+t->offset[c];
   uint32_t value=t->first[c],previous=0,acc=0,bits=0;
   s->target.curves[c][0]=(uint16_t)value;
   for(uint32_t i=1;i<256;i++){
    if(bits<2){acc|=(uint32_t)*stream++<<bits;bits+=8;}
    uint32_t code=acc&3u;acc>>=2;bits-=2;
    if(code==1)previous++;else if(code==2)previous--;
    else if(code==3){if(bits<8){acc|=(uint32_t)*stream++<<bits;bits+=8;}previous=acc&255u;acc>>=8;bits-=8;}
    value+=previous;s->target.curves[c][i]=(uint16_t)value;
   }
  }
 }
 s->status=M10V_NATIVE_LOOK_READY;return 1;
}
/* Keep the sector workspace out of the frame gamma packer call chain. */
static __attribute__((noinline)) void apply_native_sectors(void *frame,uint32_t film){
  m10v_isp_multiaxis_target t;
  const int16_t *h=film>=69?native_curated_hue[film-69]:film==66?native_5207_hue:native_phoenix_hue;
  const uint16_t boundaries[16]={1298,750,0,0,1448,843,0,0,1298,750,0,0,1205,843,0,0};
  const uint8_t selectors[20]={0,1,2,2,2,3,4,5,5,5,6,7,8,8,8,9,10,11,11,11};
  const uint16_t controls[21]={32,328,328,328,293,800,1600,2400,3200,32,1024,1024,1024,1024,0,0,0,0,0,640,1280};
  const uint16_t final9[9]={77,150,29,469,427,128,128,405,491};
  for(uint32_t i=0;i<16;i++)t.boundaries[i]=boundaries[i];
  for(uint32_t i=0;i<20;i++)t.selectors[i]=selectors[i];
  for(uint32_t i=0;i<60;i++)for(uint32_t j=0;j<9;j++)t.matrix12[i][j]=(uint32_t)h[(i/5)*9+j]&4095u;
  for(uint32_t i=0;i<40;i++)for(uint32_t j=0;j<9;j++)t.matrix10[i][j]=0;
  for(uint32_t i=0;i<21;i++){t.control[i*2]=(uint8_t)controls[i];t.control[i*2+1]=(uint8_t)(controls[i]>>8);}
  for(uint32_t i=0;i<9;i++)t.final9[i]=final9[i];
  (void)m10v_isp_multiaxis_apply(frame,0x9000u,&t);
}
int m10v_isp_native_look_apply(m10v_isp_native_look *s,const void *gamma,void *frame,uint32_t cs){
 if(!s||s->magic!=M10V_ISP_NATIVE_LOOK_MAGIC||s->version!=M10V_ISP_NATIVE_LOOK_VERSION||!s->generation||!supported(s->film,s->exposure)||s->status!=M10V_NATIVE_LOOK_READY)return 0;
 uintptr_t f=(uintptr_t)frame,p=(uintptr_t)s,g=(uintptr_t)gamma;
 if(!f||!g||(f&3)||(g&3)||f>UINTPTR_MAX-0x9000u||p>UINTPTR_MAX-sizeof(*s)||g>UINTPTR_MAX-0x3240u||
    (p<f+0x9000u&&f<p+sizeof(*s))||(g<f+0x9000u&&f<g+0x3240u)||cs>1)return 0;
 /* Frame writer validates all dynamic coefficients before mutation. The two
  * embedded multiaxis records are build-time certified; their writer writes
  * disjoint banks (CCA/CSP/gamma untouched), and cannot reject this frame. */
 if(!m10v_isp_frame_apply(gamma,frame,&s->target,cs)){s->status=M10V_NATIVE_LOOK_REJECTED;return 0;}
 if(s->film==66||s->film==67||s->film>=69)apply_native_sectors(frame,s->film);
 s->applied_frame=(uint32_t)f;s->status=M10V_NATIVE_LOOK_APPLIED;return 1;
}
int m10v_isp_native_look_matches(const m10v_isp_native_look *s,uint32_t film,uint32_t exposure,uint32_t generation){
 return s&&s->magic==M10V_ISP_NATIVE_LOOK_MAGIC&&s->version==M10V_ISP_NATIVE_LOOK_VERSION&&s->status==M10V_NATIVE_LOOK_APPLIED&&s->applied_frame&&generation&&s->generation==generation&&s->film==film&&s->exposure==exposure&&supported(film,exposure);
}
