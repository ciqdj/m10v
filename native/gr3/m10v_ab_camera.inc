/* Included in the settings adapter: uses its explicit owner and stock ABI.
 * Only UI code accesses this state. No capture worker, mutable global or new
 * parameter bank. The separately journalled pair contains no active flag. */
extern uint32_t m10v_ab_adj_event_original(uint32_t,uint32_t);
extern uint32_t m10v_ab_mapper_original(uint32_t,uint32_t);
extern uint32_t m10v_ab_selector_original(uint32_t,uint32_t);
extern uint32_t m10v_ab_live_enter_original(uint32_t,uint32_t,uint32_t);
extern uint32_t m10v_ab_live_leave_original(uint32_t);
extern uint32_t m10v_ab_live_destroy_original(uint32_t);
extern uint32_t m10v_ab_live_event_original(uint32_t,uint32_t);
static int ab_ram(uint32_t p,uint32_t n){return !(p&3)&&p>=0x55000000u&&p<=0x80000000u-n;}
static m10v_settings_controller *ab_owner(void){
 if(!(*(const volatile uint32_t *)0x55063910u&1u))return 0;
 uint32_t owner=*(const volatile uint32_t *)0x55063988u;
 if(!ab_ram(owner,M10V_SETTINGS_OWNER_BYTES+M10V_SETTINGS_CONTROLLER_BYTES))return 0;
 m10v_settings_controller *p=page(owner,0);
 return *(const uint32_t *)p==m10v_settings_controller_vtable()?p:0;
}
static uint32_t ab_current(void){
 uint32_t tone=((uint32_t (*)(void))0x532bd6b4u)();
 for(uint32_t i=0;i<M10V_TONE_CHOICES;i++)if(tone==m10v_ab_tone(i))return i;return M10V_TONE_CHOICES;
}
static uint32_t ab_route(void){
 uint32_t root=((uint32_t (*)(void))0x5320ad88u)();
 return ((fn1)0x53228c4cu)(((fn1)0x5320aefcu)(root));
}
static int ab_apply(uint32_t slot){
 if(slot>=M10V_TONE_CHOICES)return -1;
 uint32_t root=((uint32_t (*)(void))0x5320ad88u)();
 uint32_t model=((fn1)0x5320ba9cu)(root);
 uint8_t *m=(uint8_t *)(uintptr_t)model;uint8_t prior=m[0x1b];m[0x1b]=0;
 if(M10V_APPENDED_SLOTS)((fn2)0x532bd61cu)(model,0);
 ((fn2)0x532c26c0u)(model,m10v_ab_tone(slot));m[0x1b]=prior;
 return ab_current()==slot?0:-1;
}
typedef struct {uint32_t magic,version,sequence,pair,reserved,crc;} ab_record;
static const char ab_files[2][12]={"M10VAB0.BIN","M10VAB1.BIN"};
static uint32_t ab_crc(const ab_record *r){
 uint32_t c=0xffffffffu;for(uint32_t i=0;i<20;i++){c^=((const uint8_t *)r)[i];for(uint32_t b=0;b<8;b++)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));}return ~c;
}
static __attribute__((always_inline)) inline int ab_valid(const ab_record *r){return r->magic==0x3142414du&&(r->version==1||r->version==2||(M10V_APPENDED_SLOTS&&r->version==3))&&!r->reserved&&(r->pair&255)<(r->version==1?5u:r->version==2?12u:17u)&&(r->pair>>8)<(r->version==1?5u:r->version==2?12u:17u)&&(r->pair&255)!=(r->pair>>8)&&r->crc==ab_crc(r);}
static uint32_t ab_fs(void){
 uint32_t m=((uint32_t (*)(void))0x53828014u)();if(!ab_ram(m,12))return 0;
 uint32_t a=*(const uint32_t *)(uintptr_t)(m+8);if(!ab_ram(a,4))return 0;
 uint32_t fs=*(const uint32_t *)(uintptr_t)a;
 return ab_ram(fs,0x24)&&*(const uint8_t *)(uintptr_t)(fs+0x20)?fs:0;
}
static int ab_latest(uint32_t fs,ab_record *out){
 ab_record r[2];int good[2];
 for(uint32_t i=0;i<sizeof(r);i++)((volatile uint8_t *)r)[i]=0;
 for(uint32_t i=0;i<2;i++)good[i]=((uint32_t (*)(uint32_t,const char *,uint32_t,void *))0x53825648u)(fs,ab_files[i],24,&r[i])&&ab_valid(&r[i]);
 if(!good[0]&&!good[1])return 0;
 uint32_t i=!good[0]||(good[1]&&r[1].sequence>r[0].sequence);
 for(uint32_t n=0;n<6;n++)((uint32_t *)out)[n]=((const uint32_t *)&r[i])[n];return 1;
}
static int ab_save(uint32_t a,uint32_t b){
 uint32_t fs=ab_fs();if(!fs||a>=M10V_TONE_CHOICES||b>=M10V_TONE_CHOICES||a==b)return -1;
 ab_record old,r,back;for(uint32_t i=0;i<sizeof(back);i++)((volatile uint8_t *)&back)[i]=0;uint32_t seq=ab_latest(fs,&old)?old.sequence:0;if(seq==0xffffffffu)return -1;
 r.magic=0x3142414du;r.version=M10V_APPENDED_SLOTS?3:2;r.sequence=seq+1;r.pair=a|(b<<8);r.reserved=0;r.crc=ab_crc(&r);
 if(!((uint32_t (*)(uint32_t,const char *,uint32_t,const void *))0x53825fa8u)(fs,ab_files[r.sequence&1],24,&r)||
    !((uint32_t (*)(uint32_t,const char *,uint32_t,void *))0x53825648u)(fs,ab_files[r.sequence&1],24,&back)||!ab_valid(&back))return -1;
 for(uint32_t i=0;i<6;i++)if(((const uint32_t *)&r)[i]!=((const uint32_t *)&back)[i])return -1;return 0;
}
static void ab_pair(m10v_ab *s){
 uint32_t fs=ab_fs();ab_record r;
 if(fs&&ab_latest(fs,&r)){s->a=r.pair&255;s->b=r.pair>>8;
  if(r.version==1){s->a=s->a?s->a+7:1;s->b=s->b?s->b+7:1;}
  if(M10V_APPENDED_SLOTS&&r.version<3){s->a=s->a==1?12:s->a>=8?s->a+5:s->a;s->b=s->b==1?12:s->b>=8?s->b+5:s->b;}
 }
}
static uint32_t ab_now(void){uint32_t t[2]={0,0};if(((int (*)(uint32_t *))0x53050b7cu)(t))return 0;return t[0]*1000u+t[1]/1000u;}
static void ab_text(m10v_settings_controller *p){
 m10v_ab *s=&p->ab;if(!s->widget)return;
 char label[80],custom[24];uint32_t n=0;label[n++]=s->selected==s->a?'A':'B';
 if(!s->compact){
  label[n++]=' ';label[n++]=' ';uint32_t slot=m10v_ab_slot(s->selected);
  uint32_t id=s->selected==s->a?s->film_a:s->film_b;
  const char *name=slot<5?m10v_library_name(id):m10v_ab_stock_name(s->selected);
  if(slot<5&&M10V_CUSTOM(id)&&m10v_sd_camera_custom_name(&p->state.saved,slot,custom,sizeof(custom)))name=custom;
  if(name)for(uint32_t i=0;name[i]&&n<sizeof(label)-1;i++)label[n++]=name[i];
 }
 label[n]=0;((fn2)0x53390ef8u)(s->widget,(uint32_t)(uintptr_t)label);
 ((fn2)0x533ad3c0u)(s->widget,s->enabled);((fn1)0x533ad308u)(s->root);
}
static void ab_clear(m10v_ab *s){
 if(s->widget){uint32_t w=s->widget;s->widget=0;((fn3)0x5316cde8u)(0,(uint32_t)(uintptr_t)&w,1);}
 s->root=0;s->down=0;
}
static void ab_overlay(m10v_settings_controller *p,uint32_t live){
 m10v_ab *s=&p->ab;if(!s->enabled||s->widget||!ab_ram(live,0x160))return;
 uint32_t root=*(const uint32_t *)(uintptr_t)(live+0x15c);if(!ab_ram(root,0xf8))return;
 uint32_t w=((fn1)0x536af2a8u)(0x110);if(!w)return;
 ((uint32_t (*)(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t))0x53390ca0u)(w,358,20,342,42);
 ((fn2)0x533aba64u)(root,w);s->widget=w;s->root=root;
 uint32_t *vt=(uint32_t *)(uintptr_t)*(uint32_t *)(uintptr_t)w;
 ((fn1)(uintptr_t)vt[0x28/4])(w);((fn1)(uintptr_t)vt[0x34/4])(w);
 s->notice_ms=ab_now();s->compact=0;ab_text(p);
}
/* UI controllers receive both raw switch packets and logical key events.
 * The global mapper is not on every device dispatch path. */
static uint32_t ab_event_key(uint32_t event){
 uint32_t key=*(const uint16_t *)(uintptr_t)event;
 if(key!=4)return key;
 uint32_t payload=*(const uint32_t *)(uintptr_t)(event+4);
 if(!ab_ram(payload,8))return key;
 const uint8_t *p=(const uint8_t *)(uintptr_t)payload;
 M10V_LOG(95,event,payload,p[0],*(const uint32_t *)(uintptr_t)(payload+4));
 if(p[0]==1&&p[4]==1)return 0x37;
 if(p[0]==2)return p[4]==1?0x38:p[4]==0?0x36:key;
 return key;
}
#include "m10v_ab_host.inc"
uint32_t m10v_settings_controller_ab_setup(uint32_t controller,uint32_t event,uint32_t parent){
 uint32_t key=ab_event_key(event);
#if M10V_AB_NATIVE_HOST
 if(ab_host_followup(ab_owner(),controller,key,parent))return 1;
#endif
 /* Native A1 queues route 1. A DISP action can already have left this event
  * ahead of our queued 193 navigation. Consume it only for the exact source
  * while that navigation is pending; ready (including failure) clears it. */
 if(key==0xa1){
  m10v_settings_controller *p=ab_owner();
  if(!p||!p->pending_source||p->pending_source!=controller||ab_route()!=parent)return 0;
  p->pending_source=0;M10V_LOG(89,key,9,controller,parent);return 1;
 }
 if(key<0x36||key>0x38)return 0;
 uint32_t root=((uint32_t (*)(void))0x5320ad88u)();uint32_t model=((fn1)0x5320ba9cu)(root);
 if(!ab_ram(model,0x20)){M10V_LOG(89,key,1,model,parent);return 0;}
 M10V_LOG(88,key,parent,*(const uint8_t *)(uintptr_t)(model+0x1b)|((uint32_t)*(const uint8_t *)(uintptr_t)(model+0x1d)<<8),ab_route());
 if(*(const uint8_t *)(uintptr_t)(model+0x1b)){M10V_LOG(89,key,2,model,parent);return 0;}
 if(parent==0x02000012u&&*(const uint8_t *)(uintptr_t)(model+0x1d)){M10V_LOG(89,key,3,model,parent);return 0;}
 m10v_settings_controller *p=ab_owner();
 if(!p){m10v_settings_factory_original(0x55063914u,0x0200004au);p=ab_owner();}
#if M10V_DEBUG_MODE
 uint32_t owner=*(const volatile uint32_t *)0x55063988u;
 uint32_t actual=ab_ram(owner,M10V_SETTINGS_OWNER_BYTES+4)?*(const uint32_t *)(uintptr_t)(owner+M10V_SETTINGS_OWNER_BYTES):0;
 M10V_LOG(90,*(const volatile uint32_t *)0x55063910u,owner,actual,m10v_settings_controller_vtable());
#endif
 if(!p){M10V_LOG(89,key,4,0,parent);return 0;}
 if(key==0x36){p->ab.down=0;M10V_LOG(89,key,5,(uint32_t)(uintptr_t)p,0);return 1;}
 if(key==0x38||p->ab.down){M10V_LOG(89,key,key==0x38?6:7,(uint32_t)(uintptr_t)p,p->ab.down);return 1;}
 p->ab.down=1;M10V_LOG(89,key,8,(uint32_t)(uintptr_t)p,1);
#if M10V_DEBUG_MODE
 uint32_t gate=((fn1)0x5320afbcU)(root);
 M10V_LOG(99,gate,ab_ram(gate,0x14)?*(const uint8_t *)(uintptr_t)(gate+0x10):0xffffffffu,
  ab_ram(controller,0x128)?*(const uint32_t *)(uintptr_t)(controller+0x124):0,
  ab_ram(controller,0x150)?*(const uint8_t *)(uintptr_t)(controller+0x14c):0xffffffffu);
#endif
 M10V_LOG(86,controller,model,0,parent);
#if M10V_AB_NATIVE_HOST
 ab_host_open(p,controller,parent);
#else
 p->pending_source=controller;
 ((fn3)0x5316c9d8u)(controller,M10V_SETTINGS_AB_ROUTE,parent);M10V_LOG(96,controller,parent,key,ab_route());return 1;
#endif
 return 1;
}
uint32_t m10v_settings_controller_ab_adj_event(uint32_t controller,uint32_t event){
 uint32_t key=ab_event_key(event);
 if(key==0xa1&&m10v_settings_controller_ab_setup(controller,event,0x02000000u))return 1;
#if M10V_AB_NATIVE_HOST
 if(ab_host_event(ab_owner(),controller,event))return 1;
#endif
 if(key>=0x36&&key<=0x38)M10V_LOG(91,key,ab_route(),*(const uint32_t *)(uintptr_t)controller,*(const uint8_t *)(uintptr_t)(controller+0x270));
 if(key>=0x36&&key<=0x38&&ab_route()==0x02000000u&&
    *(const uint32_t *)(uintptr_t)controller==0x53b394e0u&&
    *(const uint8_t *)(uintptr_t)(controller+0x270)!=1&&
    ((fn2)0x531a2820u)(controller,*(const uint8_t *)(uintptr_t)(controller+0x1f4))==12&&
    m10v_settings_controller_ab_setup(controller,event,0x02000000u))return 1;
 return m10v_ab_adj_event_original(controller,event);
}
uint32_t m10v_settings_controller_ab_selector(uint32_t mapper,uint32_t key){
 /* ImageControl ignores stock DISP. Use its real controller as the navigation
  * owner, preserving the native parent/return route and all detail controls. */
 if(key==0x37)M10V_LOG(85,key,ab_route(),*(const volatile uint32_t *)0x55063910u,0);
 if(key>=0x36&&key<=0x38&&ab_route()==0x02000012u&&(*(const volatile uint32_t *)0x55063910u&1u)){
  uint32_t source=m10v_settings_factory_original(0x55063914u,0x02000012u);
  uint32_t event[2]={key,0};
  if(source&&m10v_settings_controller_ab_setup(source,(uint32_t)(uintptr_t)event,0x02000012u))return 1;
 }
 return m10v_ab_selector_original(mapper,key);
}
static uint32_t ab_live_key(m10v_settings_controller *p,uint32_t key){
 if(!p||!p->ab.enabled||key<0x36||key>0x38)return 0;
 if(ab_route()!=0x08000000u){p->ab.down=0;return 0;}
 m10v_ab *s=&p->ab;uint32_t current=ab_current();
 uint32_t dest=m10v_ab_key(s,key,current);
 if(!s->enabled){ab_clear(s);return 0;}
 if(dest){int result=ab_apply(dest-1);M10V_LOG(87,key,current,dest-1,(uint32_t)result);
  if(!result){m10v_ab_commit(s,dest-1);s->notice_ms=ab_now();ab_text(p);}
 }
 return 1;
}
uint32_t m10v_settings_controller_ab_mapper(uint32_t mapper,uint32_t key){
 return ab_live_key(ab_owner(),key)?1:m10v_ab_mapper_original(mapper,key);
}
uint32_t m10v_settings_controller_ab_live_enter(uint32_t live,uint32_t route,uint32_t flags){
 uint32_t r=m10v_ab_live_enter_original(live,route,flags);m10v_settings_controller *p=ab_owner();if(p&&route==0x08000000u)ab_overlay(p,live);return r;
}
uint32_t m10v_settings_controller_ab_live_leave(uint32_t live){
 m10v_settings_controller *p=ab_owner();if(p)ab_clear(&p->ab);return m10v_ab_live_leave_original(live);
}
uint32_t m10v_settings_controller_ab_live_destroy(uint32_t live){
 m10v_settings_controller *p=ab_owner();if(p)ab_clear(&p->ab);return m10v_ab_live_destroy_original(live);
}
uint32_t m10v_settings_controller_ab_live_event(uint32_t live,uint32_t event){
 m10v_settings_controller *p=ab_owner();
 if(ab_live_key(p,ab_event_key(event)))return 0;
 uint32_t r=m10v_ab_live_event_original(live,event);if(!p)return r;
 m10v_ab *s=&p->ab;
 if(s->enabled&&ab_current()!=s->selected){s->enabled=0;ab_clear(s);}
 if(s->widget&&s->enabled&&!s->compact&&(uint32_t)(ab_now()-s->notice_ms)>=1500u){s->compact=1;ab_text(p);}
 return r;
}

/* BaseController may discard physical phase-1 DISP before the ADJ virtual key
 * handler. Let the original dispatcher update all input/UI services first,
 * then supply the reserved action only to the unchanged native IC owner.
 * Release/hold, other ADJ slots, capture and power use the original result. */
extern uint32_t m10v_ab_dispatch_original(uint32_t,uint32_t);
uint32_t m10v_settings_controller_ab_dispatch(uint32_t c,uint32_t event){
 if(*(const uint16_t *)(uintptr_t)event!=4||!ab_ram(c,0x274))return m10v_ab_dispatch_original(c,event);
 uint32_t payload=*(const uint32_t *)(uintptr_t)(event+4);
 if(!ab_ram(payload,8)||*(const uint8_t *)(uintptr_t)payload!=1||
    *(const uint32_t *)(uintptr_t)(payload+4)!=1)return m10v_ab_dispatch_original(c,event);
 uint32_t route=ab_route(),vt=*(const uint32_t *)(uintptr_t)c,type=0xffffffffu;
 int scope=ab_host_word(c,0x124)==route;
 if(route==0x02000000u&&vt==0x53b394e0u&&*(const uint8_t *)(uintptr_t)(c+0x270)!=1){
  type=((fn2)0x531a2820u)(c,*(const uint8_t *)(uintptr_t)(c+0x1f4));scope=scope&&type==12;
 }else scope=scope&&route==0x02000012u&&vt==0x53b3b618u;
 if(!scope)return m10v_ab_dispatch_original(c,event);
#if M10V_DEBUG_MODE
 uint32_t keyboard=((fn1)0x5320b1fcu)(((uint32_t (*)(void))0x5320ad88u)());
 M10V_LOG(208,c,route,type,ab_ram(keyboard,0x524)?*(const uint8_t *)(uintptr_t)(keyboard+0x520):0xffffffffu);
#endif
 uint32_t r=m10v_ab_dispatch_original(c,event);
 if(ab_route()!=route)return r;
 m10v_settings_controller *p=ab_owner();
 if(ab_host_owned(ab_host(p),c))return r;
 uint32_t logical[2]={0x37,0};
 uint32_t handled=m10v_settings_controller_ab_setup(c,(uint32_t)(uintptr_t)logical,route);
 M10V_LOG(209,c,route,handled,ab_host(p)?p->host.mode:0);
 return handled?1:r;
}
