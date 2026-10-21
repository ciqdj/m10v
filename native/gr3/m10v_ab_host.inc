/* Native ADJ host, stage one: read-only. No tone setter, capture hook, custom
 * controller, root allocation or shutdown navigation. See pinned GRKit's
 * enter/leave/exit ordering; firmware APIs remain owned by this adapter. */
extern uint32_t m10v_ab_adj_refresh_original(uint32_t);
extern uint32_t m10v_ab_adj_exit_original(uint32_t);
extern uint32_t m10v_ab_adj_destroy_original(uint32_t);
extern uint32_t m10v_ab_adj_changed_original(uint32_t);
#define AB_HOST_PAGE 7u
static m10v_native_ab_host *ab_host(m10v_settings_controller *p){return p&&p->page==AB_HOST_PAGE?&p->host:0;}
static int ab_host_owned(m10v_native_ab_host *h,uint32_t c){return h&&h->mode==2&&h->controller==c;}
static uint32_t ab_host_word(uint32_t c,uint32_t off){return *(const uint32_t *)(uintptr_t)(c+off);}
static void ab_host_caption(uint32_t w,uint32_t id){((fn3)0x53396f80u)(w,id,0);}
static void ab_host_render(m10v_native_ab_host *h){
 uint32_t c=h->controller,list=ab_host_word(c,0x1f0);h->rebuilding=1;
 ((fn2)0x53394e8cu)(list,3);
 for(uint32_t i=0;i<3;i++){
  uint32_t row=((fn2)0x53394758u)(list,i);
  ((fn2)0x533a1734u)(row,0);((fn2)0x533a18e0u)(row,0);
  ((fn2)0x533a1808u)(row,1003+i);((fn2)0x533a19b4u)(row,0);
 }
 uint32_t width=((fn1)0x533948c4u)(list),rect[4]={720-width,240,width,180};
 uint32_t vt=*(const uint32_t *)(uintptr_t)list;
 ((fn2)(uintptr_t)*(const uint32_t *)(uintptr_t)(vt+0x18))(list,(uint32_t)(uintptr_t)rect);
 ((fn2)0x53395430u)(list,0);
 ab_host_caption(ab_host_word(c,0x160),1002);ab_host_caption(ab_host_word(c,0x164),1006);
 ((fn2)0x533ad3c0u)(ab_host_word(c,0x168),0);
 ((fn2)0x533ad3c0u)(ab_host_word(c,0x1ac),0);
 ((fn1)0x533ad308u)(ab_host_word(c,0x15c));h->rebuilding=0;
 M10V_LOG(97,20,c,list,h->origin);
}
static int ab_host_valid(uint32_t c){
 return ab_ram(c,0x274)&&ab_host_word(c,0)==0x53b394e0u&&
  *(uint8_t *)(uintptr_t)(c+0x270)!=1&&ab_ram(ab_host_word(c,0x1f0),0x10c)&&ab_ram(ab_host_word(c,0x15c),0xf8);
}
static void ab_host_cancel(m10v_settings_controller *p,uint32_t c){
 (void)c;
 m10v_native_ab_host *h=&p->host;h->mode=0;h->controller=0;h->rebuilding=0;
 p->pending_source=0;p->ab.down=0;M10V_LOG(97,22,c,h->origin,0);
}
static void ab_host_attach(m10v_settings_controller *p,uint32_t c){
 if(!ab_host_valid(c)){ab_host_cancel(p,c);return;}
 m10v_native_ab_host *h=&p->host;
 uint32_t list=ab_host_word(c,0x1f0);
 h->controller=c;h->rebuilding=1;
 ((fn3)0x533947f0u)(list,(uint32_t)(uintptr_t)&h->position,(uint32_t)(uintptr_t)&h->offset);
 h->mode=2;ab_host_render(h);
}
static void ab_host_restore(m10v_settings_controller *p,uint32_t c){
 m10v_native_ab_host *h=ab_host(p);if(!ab_host_owned(h,c))return;
 h->mode=0;h->rebuilding=1;p->pending_source=0;
 m10v_ab_adj_refresh_original(c);
 ((fn3)0x53395224u)(ab_host_word(c,0x1f0),h->position,h->offset);
 h->controller=0;h->rebuilding=0;M10V_LOG(97,21,c,h->origin,0);
}
#if M10V_AB_NATIVE_HOST
static void ab_host_open(m10v_settings_controller *p,uint32_t c,uint32_t origin){
 p->page=AB_HOST_PAGE;m10v_native_ab_host *h=&p->host;
 for(uint32_t i=0;i<sizeof(*h);i++)((uint8_t *)h)[i]=0;
 h->mode=1;h->origin=origin;h->source=c;p->pending_source=c;
 if(origin==0x02000000u)ab_host_attach(p,c);
 else ((fn3)0x5316c9d8u)(c,0x02000000u,0x02000012u);
}
static int ab_host_followup(m10v_settings_controller *p,uint32_t c,uint32_t key,uint32_t route){
 m10v_native_ab_host *h=ab_host(p);
 if(!h||!h->back_pending||h->origin!=route||h->source!=c)return 0;
 if(key==8){h->back_pending=0;return 0;}
 if(key==0xd8){h->back_pending=0;return 1;}return 0;
}
static int ab_host_event(m10v_settings_controller *p,uint32_t c,uint32_t event){
 m10v_native_ab_host *h=ab_host(p);if(!ab_host_owned(h,c))return 0;
 uint32_t key=ab_event_key(event);
 if(key==0x36){p->ab.down=0;return 1;}
 if(key==0x37||key==0x38||key==0x30)return 1;
 if(key==0xd0||key==0xd4||key==0xd1||key==0xd5){
  ((fn3)0x53395260u)(ab_host_word(c,0x1f0),(key==0xd0||key==0xd4)?0xffffffffu:1,1);return 1;
 }
 /* Main/power and unrecognized events remain entirely native. */
 if(key==0xd8||key==5||key==0x89||key==0xaa||key==0xce||key==0xcf||key==0x1b){
  uint32_t origin=h->origin;ab_host_restore(p,c);
  if(origin==0x02000012u&&(key==0xd8||key==5||key==0x89||key==0xaa)){
   h->back_pending=key==5;((fn1)0x5316ca28u)(c);return 1;
  }
 }
 return 0;
}
#endif
uint32_t m10v_settings_controller_ab_adj_refresh(uint32_t c){
 m10v_settings_controller *p=ab_owner();m10v_native_ab_host *h=ab_host(p);
 int target=ab_ram(c,0x274)&&ab_host_word(c,0)==0x53b394e0u&&ab_host_word(c,0x124)==0x02000000u;
 int render=h&&(h->mode==1||ab_host_owned(h,c))&&target;
 if(render){h->controller=c;h->rebuilding=1;}
 uint32_t r=m10v_ab_adj_refresh_original(c);
 if(render){
  if(ab_host_valid(c)){if(h->mode==1)ab_host_attach(p,c);else ab_host_render(h);}
  else ab_host_cancel(p,c);
 }return r;
}
uint32_t m10v_settings_controller_ab_adj_changed(uint32_t c){
 m10v_native_ab_host *h=ab_host(ab_owner());
 if(h&&h->controller==c&&(h->rebuilding||ab_host_owned(h,c)))return 0;
 return m10v_ab_adj_changed_original(c);
}
uint32_t m10v_settings_controller_ab_adj_exit(uint32_t c){
 m10v_settings_controller *p=ab_owner();ab_host_restore(p,c);
 return m10v_ab_adj_exit_original(c);
}
uint32_t m10v_settings_controller_ab_adj_destroy(uint32_t c){
 m10v_settings_controller *p=ab_owner();m10v_native_ab_host *h=ab_host(p);
 if(h&&h->controller==c){h->controller=0;h->mode=0;h->rebuilding=0;p->pending_source=0;}
 return m10v_ab_adj_destroy_original(c);
}
