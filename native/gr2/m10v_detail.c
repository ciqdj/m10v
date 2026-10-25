#include "m10v_detail.h"
#define INVALID UINT32_MAX
_Static_assert(sizeof(gr2_detail)==116,"GR II detail state ABI");
_Static_assert(sizeof(gr2_detail_ops)==12,"GR II detail callback ABI");
static void copy(m10v_library_state *out,const m10v_library_state *in){for(uint32_t i=0;i<sizeof(*out);i++)((uint8_t *)out)[i]=((const uint8_t *)in)[i];}
static int valid(const gr2_detail *d){return d&&d->ready&&d->slot<5&&m10v_library_valid(&d->saved);}
uint32_t gr2_detail_limit(const gr2_detail *d,uint32_t field){
 if(!valid(d)||field>11||field==4)return INVALID;
 uint32_t film=d->saved.slots[d->slot].film;
 if(field<3&&film!=33&&film!=67)return INVALID;
 if(field==10)return film==67?1:film==68?2:INVALID;
 static const uint8_t limits[12]={8,8,8,3,0,2,8,5,8,1,2,0};return limits[field];
}
uint32_t gr2_detail_field(const gr2_detail *d,uint32_t row){
 if(!valid(d))return INVALID;
 for(uint32_t field=0;field<12;field++)if(gr2_detail_limit(d,field)!=INVALID){if(!row)return field;row--;}
 return INVALID;
}
uint32_t gr2_detail_value(const gr2_detail *d,uint32_t field){
 if(gr2_detail_limit(d,field)==INVALID)return INVALID;
 const m10v_slot *s=&d->saved.slots[d->slot];
 if(field<3)return ((const uint8_t *)&s->halo_gain)[field];
 if(field==3)return s->grain;
 if(field==11)return 0;
 return ((const uint8_t *)&d->saved.effects[d->slot])[field-5];
}
int gr2_detail_open(gr2_detail *d,const gr2_detail_ops *ops,uint32_t slot){
 if(!d)return 0;
 d->ready=0;d->error=1;d->slot=slot;
 if(slot>=5||!ops||!ops->load||!ops->store||ops->load(ops->context,&d->saved)||!m10v_library_valid(&d->saved))return 0;
 d->ready=1;d->error=0;return 1;
}
int gr2_detail_set(gr2_detail *d,const gr2_detail_ops *ops,uint32_t packed){
 uint32_t field=packed>>8,value=packed&255u;
 if(!valid(d)||!ops||!ops->load||!ops->store||gr2_detail_limit(d,field)==INVALID||value>gr2_detail_limit(d,field))return 0;
 /* Reload before each write so changes committed by another UI operation
  * are never overwritten. A replacement film invalidates this session. */
 m10v_library_state actual;
 if(ops->load(ops->context,&actual)||!m10v_library_valid(&actual)) {d->ready=0;d->error=1;return 0;}
 if(actual.slots[d->slot].film!=d->saved.slots[d->slot].film||
    actual.effects[d->slot].reserved[0]!=d->saved.effects[d->slot].reserved[0]){d->ready=0;d->error=1;return 0;}
 copy(&d->saved,&actual);
 const m10v_slot *old=&d->saved.slots[d->slot];int result;
 if(field==11)result=m10v_library_reset(&d->saved,d->slot,ops->store,ops->context);
 else if(field>=5)result=m10v_library_effects(&d->saved,d->slot,field==10?6:field-5,value,ops->store,ops->context);
 else if(field==3){
  if(old->film==33)result=m10v_library_detail(&d->saved,d->slot,old->halo_gain,old->halo_spread,old->halo_threshold,value,old->soft,ops->store,ops->context);
  else result=m10v_library_texture(&d->saved,d->slot,value,old->soft,ops->store,ops->context);
 }
 else {
  uint32_t gain=old->halo_gain,spread=old->halo_spread,threshold=old->halo_threshold;
  if(field==0)gain=value;else if(field==1)spread=value;else threshold=value;
  if(old->film==33)result=m10v_library_detail(&d->saved,d->slot,gain,spread,threshold,old->grain,old->soft,ops->store,ops->context);
  else result=m10v_library_halation(&d->saved,d->slot,gain,spread,threshold,old->halo_profile,ops->store,ops->context);
 }
 /* A failed close/activation may still have committed the disk journal.
  * Always reconcile with the backend; never show an unverified local value. */
 d->error=result!=0;
 if(ops->load(ops->context,&actual)||!m10v_library_valid(&actual)){d->ready=0;d->error=1;return 0;}
 if(actual.slots[d->slot].film!=d->saved.slots[d->slot].film||actual.effects[d->slot].reserved[0]!=d->saved.effects[d->slot].reserved[0]){d->ready=0;d->error=1;return 0;}
 if(!result&&actual.sequence!=d->saved.sequence)d->error=1;
 copy(&d->saved,&actual);return !d->error;
}
