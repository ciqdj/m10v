#include "m10v_isp_multiaxis.h"
#include <stddef.h>
_Static_assert(offsetof(m10v_isp_multiaxis_target,matrix12)==52,"native layout");
_Static_assert(offsetof(m10v_isp_multiaxis_target,matrix10)==2212,"native layout");
_Static_assert(offsetof(m10v_isp_multiaxis_target,control)==3652,"native layout");
_Static_assert(offsetof(m10v_isp_multiaxis_target,final9)==3694,"native layout");
static const uint8_t control_mask[42]={63,0,255,15,255,15,255,15,255,15,255,15,255,15,255,15,255,15,63,0,255,7,255,7,255,7,255,7,255,1,255,1,255,1,255,1,255,15,255,15,255,15};
static int span(uintptr_t p,uint32_t n){return p&&!(p&3)&&p<=UINTPTR_MAX-n;}
int m10v_isp_multiaxis_apply(void *frame,uint32_t bytes,const m10v_isp_multiaxis_target *t){
 uintptr_t f=(uintptr_t)frame,p=(uintptr_t)t;
 if(bytes<0x9000||!span(f,bytes)||!span(p,sizeof(*t))||
   (f<p+sizeof(*t)&&p<f+bytes))return 0;
 for(uint32_t i=0;i<16;i++)if(t->boundaries[i]>4095)return 0;
 for(uint32_t i=0;i<20;i++)if(t->selectors[i]>15)return 0;
 for(uint32_t i=0;i<60;i++)for(uint32_t j=0;j<9;j++)if(t->matrix12[i][j]>4095)return 0;
 for(uint32_t i=0;i<40;i++)for(uint32_t j=0;j<9;j++)if(t->matrix10[i][j]>1023)return 0;
 for(uint32_t i=0;i<42;i++)if(t->control[i]&~control_mask[i])return 0;
 for(uint32_t i=0;i<9;i++)if(t->final9[i]>511)return 0;
#if defined(__arm__)
 /* The stack object contains only pointers; the original writer only reads
  * them. No tuning object, global record or shared cache is changed. */
 const void *record[6]={t->boundaries,t->selectors,t->matrix12,t->matrix10,t->control,t->final9};
 typedef void (*writer)(const void *,void *);
 ((writer)0x536df55cu)(record,(uint8_t *)frame+0x120);
 return 1;
#else
 return 0;
#endif
}
