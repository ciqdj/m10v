/* Independent HDF settings controller. Original TopMenu owns this small tail;
 * no film objects, film selection, film detail page or film journal is used. */
#include <stdint.h>
#include "m10v_hdf_state.h"
#ifndef M10V_HDF_OWNER_OFFSET
#define M10V_HDF_OWNER_OFFSET 0x193cu
#endif
#ifndef M10V_HDF_GROUPED
#define M10V_HDF_GROUPED 0
#endif
#define ROUTE 0x0200f102u
#define WORDS 9u
extern int m10v_hdf_load(uint32_t *);
extern int m10v_hdf_save(uint32_t);
extern uint32_t m10v_hdf_menu_parent_ctor(uint32_t);
extern uint32_t m10v_hdf_menu_parent_dtor(uint32_t);
extern uint32_t m10v_hdf_menu_parent_factory(uint32_t,uint32_t);
extern uint32_t m10v_hdf_menu_parent_key_route(uint32_t);
extern uint32_t m10v_hdf_menu_vtable(void);
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn2)(uint32_t,uint32_t);
typedef uint32_t (*fn3)(uint32_t,uint32_t,uint32_t);
typedef struct {uint8_t base[0x158];uint32_t widgets[WORDS],count,value,saved,error,root;} page;
_Static_assert(sizeof(page)<=M10V_HDF_CACHE_OFFSET,"HDF controller must not overlap its owned cache tail");
static uint32_t ptr(const void *p){return (uint32_t)(uintptr_t)p;}
static void caption(uint32_t w,uint32_t id){((fn3)0x53396f80u)(w,id,0);}
static int make(page *p,uint32_t type,uint32_t x,uint32_t y,uint32_t width,uint32_t height){
 uint32_t w=((fn1)0x536af2a8u)(type==1?0xf8:type==11?0xf0:0x110);if(!w)return -1;
 uint32_t ctor=type==1?0x5339199c:type==11?0x53393d84:0x53396944;
 ((uint32_t (*)(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t))ctor)(w,x,y,width,height);
 p->widgets[p->count++]=w;
 if(type!=1)((fn2)0x533aba64u)(p->widgets[0],w);
 return 0;
}
static void clear(page *p){
 ((fn3)0x5316cde8u)(0,ptr(p->widgets),p->count);
 for(uint32_t i=0;i<WORDS;i++)p->widgets[i]=0;p->count=0;
}
static void draw(page *p){
 caption(p->widgets[2],p->root?1140:970);caption(p->widgets[3],p->root?941:971);
 for(uint32_t i=0;i<4;i++){
  ((fn2)0x533ad3c0u)(p->widgets[4+i],!p->root||i==0);
  caption(p->widgets[4+i],p->root?1141:972+i);
  ((fn2)0x5339658cu)(p->widgets[4+i],p->root||p->value==i?10:31);
 }
 ((fn2)0x533ad3c0u)(p->widgets[8],!p->root);
 caption(p->widgets[8],p->error?976:977);
 ((fn1)0x533ad308u)(p->widgets[0]);
}
void m10v_hdf_menu_cache_init(uint32_t owner){
 m10v_hdf_ui *p=(m10v_hdf_ui *)(uintptr_t)(owner+M10V_HDF_OWNER_OFFSET+M10V_HDF_CACHE_OFFSET);
 for(uint32_t i=0;i<sizeof(*p)/4;i++)((uint32_t *)p)[i]=0;
 p->magic=M10V_HDF_CACHE_MAGIC;
}
uint32_t m10v_hdf_menu_top_ctor(uint32_t owner){
 m10v_hdf_menu_parent_ctor(owner);page *p=(page *)(uintptr_t)(owner+M10V_HDF_OWNER_OFFSET);
 for(uint32_t i=0;i<0x1c0u;i++)((uint8_t *)p)[i]=0;
 m10v_hdf_menu_cache_init(owner);
 ((fn1)0x5316c8d4u)(ptr(p));*(uint32_t *)p=m10v_hdf_menu_vtable();return owner;
}
uint32_t m10v_hdf_menu_destroy(page *p){
 ((fn1)0x5316ce8cu)(ptr(p));clear(p);((fn1)0x5316c774u)(ptr(p));return ptr(p);
}
uint32_t m10v_hdf_menu_top_dtor(uint32_t owner){
 ((m10v_hdf_ui *)(uintptr_t)(owner+M10V_HDF_OWNER_OFFSET+M10V_HDF_CACHE_OFFSET))->magic=0;
 m10v_hdf_menu_destroy((page *)(uintptr_t)(owner+M10V_HDF_OWNER_OFFSET));return m10v_hdf_menu_parent_dtor(owner);
}
uint32_t m10v_hdf_menu_factory(uint32_t factory,uint32_t route){
 if(route!=ROUTE)return m10v_hdf_menu_parent_factory(factory,route);
 uint32_t owner=m10v_hdf_menu_parent_factory(factory,0x0200004a);
 return owner?owner+M10V_HDF_OWNER_OFFSET:0;
}
uint32_t m10v_hdf_menu_ready(page *p,uint32_t route){
 (void)route;p->error=0;p->root=M10V_HDF_GROUPED;
 if(m10v_hdf_load(&p->saved)<0)return 0;p->value=p->saved;
 if(p->count==WORDS)return 1;
 if(p->count){clear(p);return 0;}
 if(make(p,1,0,0,720,480)||make(p,11,0,0,720,480)||make(p,17,20,20,680,50)||make(p,17,20,414,680,42))goto fail;
 ((fn2)0x53393e00u)(p->widgets[1],1);
 for(uint32_t i=0;i<4;i++)if(make(p,17,40+i*170,188,160,64))goto fail;
 if(make(p,17,20,320,680,50))goto fail;
 uint32_t root=p->widgets[0],*v=(uint32_t *)(uintptr_t)*(uint32_t *)(uintptr_t)root;
 ((fn1)(uintptr_t)v[0x28/4])(root);((fn1)(uintptr_t)v[0x34/4])(root);return 1;
fail:clear(p);return 0;
}
void m10v_hdf_menu_enter(page *p,uint32_t route,uint32_t flags){
 (void)route;(void)flags;draw(p);((fn3)0x5316d354u)(ptr(p),0,p->widgets[0]);
}
uint32_t m10v_hdf_menu_key(page *p,uint32_t event){
 uint32_t key=*(const uint16_t *)(uintptr_t)event;
 if(p->root){
  if(key==0xd8||key==0xcf||key==0xd3){p->root=0;draw(p);return 1;}
  if(key==0x86||key==0x89||key==0xda){((fn1)0x5316ca28u)(ptr(p));return 1;}
  return key==0xce||key==0xd0||key==0xd1||key==0xd4||key==0xd5;
 }
 if(M10V_HDF_GROUPED&&(key==0x86||key==0x89||key==0xda)){
  p->value=p->saved;p->root=1;p->error=0;draw(p);return 1;
 }
 if(key==0xce||key==0xd0||key==0xd4){if(p->value)p->value--;p->error=0;}
 else if(key==0xcf||key==0xd3||key==0xd1||key==0xd5){if(p->value<3)p->value++;p->error=0;}
 else if(key==0xd8){
  if(m10v_hdf_save(p->value)){
   /* A successful write followed by failed verification may already persist.
    * Reconcile with the same journal reader used by capture, rather than
    * falsely showing the previous value. Stay open with the error visible. */
   uint32_t actual;if(m10v_hdf_load(&actual)==0)p->saved=p->value=actual;
   p->error=1;
  }
  else{p->saved=p->value;if(M10V_HDF_GROUPED){p->root=1;draw(p);}else ((fn1)0x5316ca28u)(ptr(p));return 1;}
 }else if(key==0x86||key==0x89||key==0xda){((fn1)0x5316ca28u)(ptr(p));return 1;}
 else return 0;
 draw(p);return 1;
}
uint32_t m10v_hdf_menu_key_route(uint32_t model){
 uint32_t route=m10v_hdf_menu_parent_key_route(model);return route==ROUTE?0x0200004a:route;
}
