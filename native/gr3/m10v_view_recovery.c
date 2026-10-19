#include "m10v_view_recovery.h"
static uint32_t ram(uint32_t a,uint32_t n){return a>=0x55000000u&&a<=0x60000000u-n&&!(a&3u);}
uint32_t m10v_view_snapshot_read(m10v_view_snapshot *s,m10v_view_read_fn r,void *c){
 uint32_t q,i; uint32_t *p;
 if(!s||!r)return 0;
 p=(uint32_t *)s;for(i=0;i<sizeof(*s)/4;i++)p[i]=0;
 /* Constructor guards and exact vptr make this observation-only. */
 if(!(r(c,0x55064398u,4)&1u))return 0;
 s->model_vptr=r(c,M10V_VIEW_MODEL,4);
 if(s->model_vptr!=M10V_VIEW_MODEL_VPTR)return 0;
 s->model=M10V_VIEW_MODEL;
 s->actual=r(c,s->model+8,1);s->pending=r(c,s->model+9,1);s->inflight=r(c,s->model+10,1);
 s->shooting2f=r(c,s->model+0x2f,1);s->shooting30=r(c,s->model+0x30,1);s->shooting31=r(c,s->model+0x31,1);
 if(r(c,0x55063910u,4)&1u){
  q=r(c,M10V_VIEW_FACTORY+0xd8,4);
  if(q&&ram(q,0x184u)&&r(c,q,4)==M10V_VIEW_QUICK_VPTR){
   s->quick=q;s->quick_vptr=M10V_VIEW_QUICK_VPTR;s->quick_state=r(c,q+0x16c,1);
   s->timer_review=r(c,q+0x178,4);s->timer_wait=r(c,q+0x17c,4);
   s->quick_flags=r(c,q+0x180,1)|(r(c,q+0x181,1)<<8)|(r(c,q+0x182,1)<<16);
  }
 }
 s->magic=M10V_VIEW_SNAPSHOT_MAGIC;return 1;
}
static uint32_t camera_read(void *c,uint32_t a,uint32_t n){
 (void)c;if(n==1)return *(volatile const uint8_t *)(uintptr_t)a;
 return *(volatile const uint32_t *)(uintptr_t)a;
}
uint32_t m10v_view_snapshot_camera(m10v_view_snapshot *s){return m10v_view_snapshot_read(s,camera_read,0);}
uint32_t m10v_view_recovery_decide(const m10v_view_snapshot *s,uint32_t facts){
 if(!s||s->magic!=M10V_VIEW_SNAPSHOT_MAGIC||s->model!=M10V_VIEW_MODEL||s->model_vptr!=M10V_VIEW_MODEL_VPTR)return M10V_VIEW_OBSERVE;
 if((facts&M10V_VIEW_REQUIRED)!=M10V_VIEW_REQUIRED||s->inflight||s->pending||s->shooting2f||s->shooting30||s->shooting31)return M10V_VIEW_OBSERVE;
 if(s->actual==2)return M10V_VIEW_ALREADY_RUNNING;
 /* Resume only actual stock paused state4. Stopped/movie/unknown refused. */
 return s->actual==4?M10V_VIEW_CAN_REQUEST:M10V_VIEW_OBSERVE;
}
static uint32_t camera_start(void *c,uint32_t model,const uint32_t *fn){
 typedef uint32_t (*start_fn)(uint32_t,const uint32_t *);(void)c;
 return ((start_fn)(uintptr_t)0x5323830cu)(model,fn);
}
uint32_t m10v_view_recovery_request(m10v_view_snapshot *s,uint32_t facts,m10v_view_read_fn r,void *c,m10v_view_start_fn start,void *sc){
 uint32_t d;const uint32_t empty[4]={0,0,0,0};
 if(!r)r=camera_read;
 if(!m10v_view_snapshot_read(s,r,c))return M10V_VIEW_OBSERVE;
 d=m10v_view_recovery_decide(s,facts);if(d!=M10V_VIEW_CAN_REQUEST)return d;
 if(!start)start=camera_start;
 return start(sc,s->model,empty)?M10V_VIEW_REQUEST_ACCEPTED:M10V_VIEW_REQUEST_REJECTED;
}
uint32_t m10v_view_trace_append(m10v_view_trace *t,uint32_t boundary,uint32_t time,uint32_t payload,const m10v_view_snapshot *s){
 m10v_view_record *v;if(!t||!s||s->magic!=M10V_VIEW_SNAPSHOT_MAGIC)return 0;
 if(t->count>=M10V_VIEW_TRACE_CAPACITY){if(t->dropped!=0xffffffffu)t->dropped++;return 0;}
 v=&t->records[t->count++];v->boundary=boundary;v->time=time;v->payload=payload;v->state=*s;return 1;
}
