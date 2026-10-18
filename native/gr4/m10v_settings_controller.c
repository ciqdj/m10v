/* Exact GR IV 1.11 BaseController ownership adapter. Not enabled until the
 * separately audited root/factory patches and key mapping are installed. */
#include "m10v_settings_controller.h"
#include "../gr3/m10v_debug.h"
#include "../gr3/m10v_sd_library.h"
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn2)(uint32_t,uint32_t);
typedef uint32_t (*fn3)(uint32_t,uint32_t,uint32_t);
extern uint32_t m10v_settings_factory_original(uint32_t,uint32_t);
extern uint32_t m10v_settings_top_dtor_original(uint32_t);
extern uint32_t m10v_settings_controller_vtable(void);
static int load(void *ctx,m10v_library_state *s){(void)ctx;return m10v_camera_library_load(s);}
static uint32_t item(void *ctx,uint32_t i){(void)ctx;return m10v_sd_camera_item(i/8,i%8);}
static int install(void *ctx,uint32_t i,uint32_t id,uint32_t slot){
 (void)ctx;
 int r=m10v_sd_camera_install(i/8,i%8,id,slot);
 if(!r){
  static const uint8_t tones[5]={36,37,38,39,40};
  uint32_t root=((uint32_t (*)(void))0x5323ea84u)();
  uint32_t model=((fn1)0x5323f928u)(root);
  ((fn2)0x533b70ccu)(model,tones[slot]);
 }
 return r;
}
static int stamp(void *ctx,uint32_t enabled,uint32_t format,uint32_t corner,uint32_t color){
 (void)ctx;m10v_library_state fresh;
 if(m10v_camera_library_load(&fresh)<0)return -1;
 return m10v_camera_library_stamp(&fresh,enabled,format,corner,color);
}
static void ops(m10v_settings_ops *o){o->context=0;o->load=load;o->item=item;o->install=install;o->stamp=stamp;}
static m10v_settings_controller *page(uint32_t owner,uint32_t i){
 return (m10v_settings_controller *)(uintptr_t)(owner+M10V_SETTINGS_OWNER_BYTES+i*M10V_SETTINGS_CONTROLLER_BYTES);
}
uint32_t m10v_settings_controller_owner_size(void){return M10V_SETTINGS_OWNER_BYTES+2*M10V_SETTINGS_CONTROLLER_BYTES;}
uint32_t m10v_settings_controller_top_ctor(uint32_t owner){
 ((fn1)0x531b421cu)(owner);
 for(uint32_t i=0;i<2;i++){
  m10v_settings_controller *p=page(owner,i);uint8_t *b=(uint8_t *)p;
  for(uint32_t n=0;n<sizeof(*p);n++)b[n]=0;
  ((fn1)0x53182d40u)((uint32_t)(uintptr_t)p);
  *(uint32_t *)p=m10v_settings_controller_vtable();
  p->page=i?M10V_SETTINGS_STAMP:M10V_SETTINGS_FILMS;
 }
 return owner;
}
uint32_t m10v_settings_controller_destroy(m10v_settings_controller *p){
 ((fn1)0x5318334cu)((uint32_t)(uintptr_t)p);
 m10v_settings_view_destroy(&p->view);
 ((fn1)0x53182be4u)((uint32_t)(uintptr_t)p);
 return (uint32_t)(uintptr_t)p;
}
uint32_t m10v_settings_controller_top_dtor(uint32_t owner){
 for(uint32_t i=0;i<2;i++)m10v_settings_controller_destroy(page(owner,i));
 return m10v_settings_top_dtor_original(owner);
}
uint32_t m10v_settings_controller_factory(uint32_t factory,uint32_t route){
 if(route!=M10V_SETTINGS_FILMS_ROUTE&&route!=M10V_SETTINGS_STAMP_ROUTE)
  return m10v_settings_factory_original(factory,route);
 uint32_t owner=m10v_settings_factory_original(factory,0x02000060u);
 return owner?(uint32_t)(uintptr_t)page(owner,route==M10V_SETTINGS_STAMP_ROUTE):0;
}
uint32_t m10v_settings_controller_ready(m10v_settings_controller *p,uint32_t route){
 (void)route;m10v_settings_ops o;ops(&o);
 if(m10v_settings_open(&p->state,&o,p->page))return 0;
 return p->view.count==M10V_VIEW_COUNT&&p->view.widgets[0] ? 1 : m10v_settings_view_create(&p->view)==0;
}
void m10v_settings_controller_enter(m10v_settings_controller *p,uint32_t route,uint32_t flags){
 (void)route;(void)flags;m10v_settings_ops o;ops(&o);
 M10V_LOG(80,p->page,route,p->state.screen,p->state.focus);
 m10v_settings_view_draw(&p->view,&p->state,&o);
 ((fn3)0x53183830u)((uint32_t)(uintptr_t)p,0,p->view.widgets[0]);
 M10V_LOG(81,p->page,route,p->state.screen,p->state.focus);
}
uint32_t m10v_settings_controller_key(m10v_settings_controller *p,uint32_t event){
 uint32_t raw=*(const uint16_t *)(uintptr_t)event,key;
 M10V_LOG(82,raw,p->state.screen,p->state.focus,p->state.value);
 switch(raw){
 case 0xd4:key=M10V_KEY_LEFT;break;
 case 0xd5:case 0xd9:key=M10V_KEY_RIGHT;break;
 case 0xd6:case 0xda:key=M10V_KEY_UP;break;
 case 0xd7:case 0xdb:key=M10V_KEY_DOWN;break;
 case 0xe0:key=M10V_KEY_OK;break;
 case 0x8a:case 0x8d:case 0xe2:key=M10V_KEY_BACK;break;
 default:return 0;
 }
 m10v_settings_ops o;ops(&o);m10v_settings_key(&p->state,&o,key);
 M10V_LOG(83,raw,p->state.screen,p->state.focus,(p->state.error<<16)|p->state.value);
 if(p->state.screen==M10V_SETTINGS_CLOSED)((fn1)0x53182e9cu)((uint32_t)(uintptr_t)p);
 else m10v_settings_view_draw(&p->view,&p->state,&o);
 M10V_LOG(84,raw,p->state.screen,p->state.focus,(p->state.error<<16)|p->state.value);
 return 1;
}

/* Scoped to the original key dispatch call site, never the global route getter. */
uint32_t m10v_settings_controller_key_route(uint32_t model){
 uint32_t route=((fn1)0x5325ca14u)(model);
 return route==M10V_SETTINGS_FILMS_ROUTE||route==M10V_SETTINGS_STAMP_ROUTE?0x02000060u:route;
}
