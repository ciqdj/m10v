/* No pointer passed as an identity/backing/source is ever dereferenced here. */
#include "m10v_capture_raw_lifetime.h"
#define MAGIC 0x31574c52u
#define IDLE 0u
#define RELEASING 1u
#define POOL_OK 2u
#define CLEARED 3u
#define RELEASED 4u
_Static_assert(sizeof(m10v_capture_raw_lifetime)==M10V_CAPTURE_RAW_TOKEN_BYTES,"raw lifetime extent");
static int valid(const m10v_capture_raw_lifetime *s,uint32_t owner){return s&&s->magic==MAGIC&&s->owner==owner;}
static void barrier(void){__atomic_thread_fence(__ATOMIC_SEQ_CST);}
void m10v_capture_raw_init(m10v_capture_raw_lifetime *s,uint32_t owner){
 uint32_t *p=(uint32_t *)s;for(uint32_t i=0;i<sizeof(*s)/4;i++)p[i]=0;
 s->owner=owner;barrier();s->magic=MAGIC;
}
void m10v_capture_raw_invalidate(m10v_capture_raw_lifetime *s,uint32_t owner){
 if(!valid(s,owner))return;s->phase=IDLE;barrier();s->generation++;s->shooting=0;s->pool_result=0;
}
void m10v_capture_raw_release_begin(m10v_capture_raw_lifetime *s,uint32_t owner,uint32_t si,uint32_t backing,uint32_t source,uint32_t caller){
 if(!valid(s,owner))return;
 m10v_capture_raw_invalidate(s,owner);
 /* Only the native planner boundary observed in the hardware evidence is
  * accepted. Other cleanup/transfer paths retain their old fail-closed guard. */
 if(!si||!backing||!source||caller!=0x5351fd54u)return;
 s->shooting=si;s->backing=backing;s->source=source;s->caller=caller;barrier();s->phase=RELEASING;
}
void m10v_capture_raw_pool_return(m10v_capture_raw_lifetime *s,uint32_t owner,uint32_t si,uint32_t id,uint32_t backing,uint32_t result){
 if(id!=1||!valid(s,owner))return;
 if(s->phase!=RELEASING||s->shooting!=si||s->backing!=backing||result!=1){m10v_capture_raw_invalidate(s,owner);return;}
 s->pool_result=result;barrier();s->phase=POOL_OK;
}
void m10v_capture_raw_set_after(m10v_capture_raw_lifetime *s,uint32_t owner,uint32_t si,uint32_t id,uint32_t input,uint32_t old_backing,uint32_t old_source,uint32_t backing,uint32_t source){
 if(id!=1||!valid(s,owner))return;
 if(input||s->phase!=POOL_OK||s->shooting!=si||s->backing!=old_backing||s->source!=old_source||backing||source){m10v_capture_raw_invalidate(s,owner);return;}
 barrier();s->phase=CLEARED;
}
void m10v_capture_raw_release_finish(m10v_capture_raw_lifetime *s,uint32_t owner,uint32_t si,uint32_t backing,uint32_t source){
 if(!valid(s,owner))return;
 if(s->phase!=CLEARED||s->shooting!=si||backing||source||s->pool_result!=1){m10v_capture_raw_invalidate(s,owner);return;}
 barrier();s->phase=RELEASED;
}
uint32_t m10v_capture_raw_classify(const m10v_capture_raw_lifetime *s,uint32_t owner,uint32_t si,uint32_t backing,uint32_t source){
 if(!valid(s,owner))return M10V_CAPTURE_RAW_REJECT;
 barrier();uint32_t phase=s->phase;
 if(phase==IDLE&&backing&&source)return M10V_CAPTURE_RAW_LIVE;
 if(phase==RELEASED&&s->shooting==si&&si&&!backing&&!source&&s->pool_result==1&&s->caller==0x5351fd54u)return M10V_CAPTURE_RAW_RELEASED;
 return M10V_CAPTURE_RAW_REJECT;
}
