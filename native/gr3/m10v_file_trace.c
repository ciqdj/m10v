/* SHA-locked WriteStillFile caller owns an optional heap trace until its
 * synchronous nested bridge returns and original cleanup has completed. */
#include "m10v_save_trace.h"
typedef uint32_t (*alloc_fn)(uint32_t);
typedef void (*free_fn)(uint32_t);
static void mark(m10v_save_trace *trace,uint32_t event,uint32_t task,uint32_t result){
 uint32_t time[2]={0,0};int status=((int (*)(uint32_t *))0x53050b7cu)(time);
 m10v_save_trace_append(trace,event,task,time[1],time[0],result|(status?0x80000000u:0));
}
extern void m10v_lifecycle_file_flush(m10v_save_trace *);
static int ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
void m10v_file_trace_begin(uint32_t outer_fp){
 /* Exact expanded caller frame: old locals end at -3c; outgoing arguments
  * occupy newSP=-5c through -54. Private pointer is at -50. */
 uint32_t *owner=(uint32_t *)(uintptr_t)(outer_fp-0x50u);
 *owner=0;
 uint32_t p=((alloc_fn)0x536af2a8u)(sizeof(m10v_save_trace));
 if(!ram(p,sizeof(m10v_save_trace)))return;
 m10v_save_trace_init((m10v_save_trace *)(uintptr_t)p);*owner=p;
 mark((m10v_save_trace *)(uintptr_t)p,195,*(const uint32_t *)(uintptr_t)(outer_fp-0x38u),0);
 m10v_save_trace_append((m10v_save_trace *)(uintptr_t)p,197,
  *(const uint32_t *)(uintptr_t)(outer_fp-0x38u),
  *(const uint32_t *)(uintptr_t)(outer_fp-0x58u),
  *(const uint32_t *)(uintptr_t)(outer_fp-0x5cu),
  *(const uint32_t *)(uintptr_t)(outer_fp-0x54u));
}
void m10v_file_trace_finish(uint32_t outer_fp,uint32_t result){
 uint32_t *owner=(uint32_t *)(uintptr_t)(outer_fp-0x50u);
 uint32_t p=*owner;*owner=0;
 if(!ram(p,sizeof(m10v_save_trace)))return;
 /* Flush occurs in the original caller after inner cleanup, never in the
  * storage callback. The supplied sink must be approved for this task. */
 mark((m10v_save_trace *)(uintptr_t)p,196,*(const uint32_t *)(uintptr_t)(outer_fp-0x38u),result);
 m10v_lifecycle_file_flush((m10v_save_trace *)(uintptr_t)p);
 ((free_fn)0x536af2e4u)(p);
}
