/* Call-owned actual BE file trace. Context is an opaque cookie, never a recipe. */
#include "m10v_save_trace.h"
extern void m10v_lifecycle_file_flush(m10v_save_trace *);
static int ram(uint32_t p){return !(p&3)&&p>=0x55000000u&&p<=0x80000000u-sizeof(m10v_save_trace);}
static void mark(m10v_save_trace *t,uint32_t event,uint32_t cookie,uint32_t result){
 uint32_t time[2]={0,0};int status=((int (*)(uint32_t *))0x53050b7cu)(time);
 m10v_save_trace_append(t,event,cookie,time[1],time[0],result|(status?0x80000000u:0));
}
void m10v_be_file_begin(uint32_t fp,uint32_t cookie){
 /* Original caller SP=fp-54. Two outgoing slots precede descriptor fp-4c.
  * The exact three-argument callee never reads incoming stack arguments. */
 uint32_t *owner=(uint32_t *)(uintptr_t)(fp-0x54u);*owner=0;
 uint32_t p=((uint32_t (*)(uint32_t))0x536af2a8u)(sizeof(m10v_save_trace));
 if(!ram(p))return;
 m10v_save_trace *t=(m10v_save_trace *)(uintptr_t)p;
 m10v_save_trace_init(t);*owner=p;mark(t,200,cookie,0);
 /* Original caller accesses through cookie+82; retain scalar identity fields
  * only, without following parameters/SI or treating either as an owner. */
 if(!(cookie&3)&&cookie>=0x55000000u&&cookie<=0x80000000u-0x84u){
  const uint32_t *c=(const uint32_t *)(uintptr_t)cookie;
  m10v_save_trace_append(t,203,cookie,c[0],c[0x30/4],c[0x34/4]);
 }
}
void m10v_be_file_finish(uint32_t fp,uint32_t cookie,uint32_t result){
 uint32_t *owner=(uint32_t *)(uintptr_t)(fp-0x54u),p=*owner;*owner=0;
 if(!ram(p))return;
 m10v_save_trace *t=(m10v_save_trace *)(uintptr_t)p;
 mark(t,201,cookie,result);
 m10v_save_trace_append(t,202,cookie,*(const uint8_t *)(uintptr_t)(fp-0x3cu),*(const uint8_t *)(uintptr_t)(fp-0x4cu),result);
 /* Original blocking file operation has returned, outside service callback.
  * Sink must be synchronous and establish caller task filesystem safety. */
 m10v_lifecycle_file_flush(t);((void (*)(uint32_t))0x536af2e4u)(p);
}
