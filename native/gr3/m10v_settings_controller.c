/* Exact GR III 2.10 BaseController ownership adapter. Not enabled until the
 * separately audited root/factory patches and key mapping are installed. */
#include "m10v_settings_controller.h"
#include "m10v_debug.h"
#include "m10v_sd_library.h"
#include "m10v_film_card.h"
#ifndef M10V_LIVE_COLOR
#define M10V_LIVE_COLOR 0
#endif
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
  static const uint8_t tones[5]={12,18,19,20,21};
  uint32_t root=((uint32_t (*)(void))0x5320ad88u)();
  uint32_t model=((fn1)0x5320ba9cu)(root);
  ((fn2)0x532c26c0u)(model,tones[slot]);
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
uint32_t m10v_settings_controller_owner_size(void){return M10V_SETTINGS_OWNER_BYTES+2*M10V_SETTINGS_CONTROLLER_BYTES+(M10V_LIVE_COLOR?128u:0u);}
uint32_t m10v_settings_controller_top_ctor(uint32_t owner){
 ((fn1)0x5319aa68u)(owner);
 for(uint32_t i=0;i<2;i++){
  m10v_settings_controller *p=page(owner,i);uint8_t *b=(uint8_t *)p;
  for(uint32_t n=0;n<sizeof(*p);n++)b[n]=0;
  ((fn1)0x5316c8d4u)((uint32_t)(uintptr_t)p);
  *(uint32_t *)p=m10v_settings_controller_vtable();
  p->page=i?M10V_SETTINGS_STAMP:M10V_SETTINGS_FILMS;
 }
#if M10V_LIVE_COLOR
 m10v_camera_library_preview_init(owner);
#endif
 return owner;
}
uint32_t m10v_settings_controller_destroy(m10v_settings_controller *p){
 ((fn1)0x5316ce8cu)((uint32_t)(uintptr_t)p);
 m10v_settings_view_destroy(&p->view);
 ((fn1)0x5316c774u)((uint32_t)(uintptr_t)p);
 return (uint32_t)(uintptr_t)p;
}
uint32_t m10v_settings_controller_top_dtor(uint32_t owner){
#if M10V_LIVE_COLOR
 m10v_camera_library_preview_clear(owner);
#endif
 for(uint32_t i=0;i<2;i++)m10v_settings_controller_destroy(page(owner,i));
 return m10v_settings_top_dtor_original(owner);
}
uint32_t m10v_settings_controller_factory(uint32_t factory,uint32_t route){
 if(route!=M10V_SETTINGS_FILMS_ROUTE&&route!=M10V_SETTINGS_STAMP_ROUTE)
  return m10v_settings_factory_original(factory,route);
 uint32_t owner=m10v_settings_factory_original(factory,0x0200004au);
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
 ((fn3)0x5316d354u)((uint32_t)(uintptr_t)p,0,p->view.widgets[0]);
 M10V_LOG(81,p->page,route,p->state.screen,p->state.focus);
}
uint32_t m10v_settings_controller_key(m10v_settings_controller *p,uint32_t event){
 uint32_t raw=*(const uint16_t *)(uintptr_t)event,key;
 M10V_LOG(82,raw,p->state.screen,p->state.focus,p->state.value);
 switch(raw){
 case 0xce:key=M10V_KEY_LEFT;break;
 case 0xcf:case 0xd3:key=M10V_KEY_RIGHT;break;
 case 0xd0:case 0xd4:key=M10V_KEY_UP;break;
 case 0xd1:case 0xd5:key=M10V_KEY_DOWN;break;
 case 0xd8:key=M10V_KEY_OK;break;
 case 0x86:case 0x89:case 0xda:key=M10V_KEY_BACK;break;
 default:return 0;
 }
 m10v_settings_ops o;ops(&o);m10v_settings_key(&p->state,&o,key);
 M10V_LOG(83,raw,p->state.screen,p->state.focus,(p->state.error<<16)|p->state.value);
 if(p->state.screen==M10V_SETTINGS_CLOSED)((fn1)0x5316ca28u)((uint32_t)(uintptr_t)p);
 else m10v_settings_view_draw(&p->view,&p->state,&o);
 M10V_LOG(84,raw,p->state.screen,p->state.focus,(p->state.error<<16)|p->state.value);
 return 1;
}

/* Scoped to the original key dispatch call site, never the global route getter. */
uint32_t m10v_settings_controller_key_route(uint32_t model){
 uint32_t route=((fn1)0x53228c4cu)(model);
 return route==M10V_SETTINGS_FILMS_ROUTE||route==M10V_SETTINGS_STAMP_ROUTE?0x0200004au:route;
}

/* Dynamic bitmap metadata belongs to the same heap allocation as its pixels.
 * Only the five private icon IDs call this provider. No ROM writes or retained
 * global heap pointers; original TopMenu/root lifetime owns the lookup. */
uint32_t m10v_settings_controller_card_directory(void){
 if(!(*(const volatile uint32_t *)0x55063910u&1u))return 0;
 uint32_t owner=*(const volatile uint32_t *)0x55063988u;
 if((owner&3)||owner<0x55000000u||owner>0x80000000u-0x193cu)return 0;
 m10v_settings_controller *p=page(owner,0);
 if(*(uint32_t *)p!=m10v_settings_controller_vtable()||p->view.count!=M10V_VIEW_COUNT)return 0;
 uint32_t heap=p->view.widgets[39];
 if((heap&3)||heap<0x55000000u||heap>0x80000000u-470464u)return 0;
 return heap+470440u-M10V_CARD_FIRST*4u;
}
