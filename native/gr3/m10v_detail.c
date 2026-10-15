/* Stock ImageControlDetailController adapter. No private allocator, shadow
 * settings or stock parameter storage. Callbacks follow stock immediate update
 * semantics; journal failure restores the visible slider to committed state. */
#include "m10v_library.h"
#include "m10v_debug.h"
extern const uint32_t m10v_detail_tables;
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn2)(uint32_t,uint32_t);
typedef void (*text_fn)(uint32_t,uint32_t,const uint16_t *);
static int ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<0x80000000u&&n<=0x80000000u-p;}
static int slot(uint32_t ui){
 static const uint8_t tones[5]={12,18,19,20,21};
 if(!ram(ui,0x1a0))return -1;
 const uint8_t *m=(const uint8_t *)(uintptr_t)ui;
 if(m[0x199]>2||m[0x19a]>11||m[0x19b]||m[0x19d])return -1;
 for(uint32_t i=0;i<5;i++)if(m[0x198]==tones[i])return (int)i;
 return -1;
}
static int load(uint32_t ui,m10v_library_state *s){
 int i=slot(ui);if(i<0)return -1;
 m10v_camera_library_load(s);
 return m10v_library_valid(s)&&s->slots[i].film==33?i:-1;
}
uint32_t m10v_detail_table(uint32_t ui){
 m10v_library_state s;
 return load(ui,&s)<0?0x53b3488cu:(uint32_t)(uintptr_t)&m10v_detail_tables;
}
static uint32_t value(const m10v_slot *s,uint32_t field){
 if(field==0)return s->halo_gain;if(field==1)return s->halo_spread;
 if(field==2)return s->halo_threshold;if(field==3)return s->grain;return s->soft;
}
uint32_t m10v_detail_control(uint32_t op,uint32_t ui,uint32_t arg){
 m10v_library_state s;int target=load(ui,&s);if(target<0)return 0;
 uint32_t field=arg,v=arg&255;
 if(op==2)field=arg>>8;
 if(op==3)field=arg>>16;
 if(op==4)field=((fn1)0x531b01d0u)(ui)-18;
 if(op!=7&&field>4)return 0;
 if(op==4){m10v_library_state defaults;m10v_library_init(&defaults);return value(&defaults.slots[target],field);}
 const m10v_slot *old=&s.slots[target];
 if(op==1)return value(old,field);
 if(op==2||op==7){
  if(op==2&&v>(field<3?8u:3u))return 0;
  uint32_t gain=old->halo_gain,spread=old->halo_spread,threshold=old->halo_threshold,grain=old->grain,soft=old->soft;
  if(op==7){m10v_library_state defaults;m10v_library_init(&defaults);const m10v_slot *d=&defaults.slots[target];gain=d->halo_gain;spread=d->halo_spread;threshold=d->halo_threshold;grain=d->grain;soft=d->soft;}
  else if(field==0)gain=v;else if(field==1)spread=v;else if(field==2)threshold=v;else if(field==3)grain=v;else soft=v;
  uint32_t previous=op==2?value(old,field):0;
  int result=m10v_camera_library_detail(&s,(uint32_t)target,gain,spread,threshold,grain,soft);
  M10V_LOG(70,18+field,previous,v,((uint32_t)target<<16)|(uint16_t)result);
  if(result){
   uint32_t slider=*(const uint32_t *)(uintptr_t)(ui+0x164),caption=*(const uint32_t *)(uintptr_t)(ui+0x160);
   if(op==2&&ram(slider,4))((fn2)0x5339ee0cu)(slider,previous);
   if(ram(caption,4))((uint32_t (*)(uint32_t,uint32_t,uint32_t))0x53396f80u)(caption,824,0);
   return 0;
  }
  return 1;
 }
 if(op==3){
  v=value(old,field);uint16_t text[8];
  /* Explicit volatile stores prevent older clang from requiring __aeabi_memclr. */
  for(uint32_t i=0;i<8;i++)((volatile uint16_t *)text)[i]=0;
  if(field<3){text[0]=(uint16_t)('0'+v);text[1]='/';text[2]='8';}
  else if(!v){text[0]=0x5173;text[1]=0x95ed;}
  else if(v==1){text[0]=0x5f31;}
  else if(v==2){text[0]=0x4e2d;}
  else {text[0]=0x5f3a;}
  uint32_t list=*(const uint32_t *)(uintptr_t)(ui+0x194);if(!ram(list,4))return 0;
  uint32_t row=((fn2)0x53394758u)(list,arg&65535);if(!ram(row,4))return 0;
  ((text_fn)0x5339e2f8u)(row,0x1e3,text);return 1;
 }
 return 0;
}
