/* Standalone primitive view. No ImageControl objects, model padding or hooks.
 * ABI evidence: original GR III 2.10 factory 533ad7f0 and constructors below.
 * Every top-level allocation is checked BEFORE invoking its constructor.
 * Remaining stock limitation: child-vector growth and text setters allocate
 * internally without a recoverable OOM contract. This is NOT a hardware proof.
 */
#include "m10v_settings_view.h"
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn2)(uint32_t,uint32_t);
typedef uint32_t (*fn3)(uint32_t,uint32_t,uint32_t);
typedef uint32_t (*ctor)(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t);
enum { ROOT, BACKGROUND, TITLE, NAME, FOOTER, ERROR_TEXT,
 FRAME=6, INNER=11, ICON=16, ROW=21, VALUE=25, COUNT=29 };
static uint32_t ptr(const void *p){return (uint32_t)(uintptr_t)p;}
static void visible(uint32_t w,uint32_t yes){((fn2)0x533ad3c0u)(w,yes);}
static void color(uint32_t w,uint32_t c){((fn2)0x53393e00u)(w,c);}
static void caption(uint32_t w,uint32_t id){((fn3)0x53396f80u)(w,id,0);}
static int make(m10v_settings_view *v,uint32_t type,uint32_t x,uint32_t y,uint32_t width,uint32_t height){
 uint32_t size=type==1||type==10?0xf8:type==11?0xf0:0x110;
 uint32_t address=type==1?0x5339199cu:type==10?0x5339a908u:type==11?0x53393d84u:type==17?0x53396944u:0x53390ca0u;
 uint32_t w=((fn1)0x536af2a8u)(size);if(!w)return -1;
 ((ctor)(uintptr_t)address)(w,x,y,width,height);
 v->widgets[v->count++]=w;
 if(type!=1)((fn2)0x533aba64u)(v->widgets[ROOT],w);
 return 0;
}
void m10v_settings_view_destroy(m10v_settings_view *v){
 if(!v||v->count>32)return;
 ((fn3)0x5316cde8u)(0,ptr(v->widgets),v->count);
 for(uint32_t i=0;i<32;i++)v->widgets[i]=0;
 v->count=0;
}
int m10v_settings_view_create(m10v_settings_view *v){
 if(!v||v->count)return -1;
 for(uint32_t i=0;i<32;i++)v->widgets[i]=0;
 if(make(v,1,0,0,720,480)||make(v,11,0,0,720,480)||
    make(v,17,20,12,680,42)||make(v,0,20,320,680,44)||
    make(v,17,20,430,680,40)||make(v,17,20,375,680,40))goto fail;
 for(uint32_t i=0;i<5;i++)if(make(v,11,24+i*136,150,128,128))goto fail;
 for(uint32_t i=0;i<5;i++)if(make(v,11,28+i*136,154,120,120))goto fail;
 for(uint32_t i=0;i<5;i++)if(make(v,10,28+i*136,154,120,120))goto fail;
 for(uint32_t i=0;i<4;i++)if(make(v,17,36,90+i*72,300,56))goto fail;
 for(uint32_t i=0;i<4;i++)if(make(v,17,350,90+i*72,330,56))goto fail;
 color(v->widgets[BACKGROUND],1);
 for(uint32_t i=0;i<5;i++){
  color(v->widgets[INNER+i],1);
  ((fn2)0x5339aa30u)(v->widgets[ICON+i],1);
  ((fn2)0x5339aa44u)(v->widgets[ICON+i],1);
 }
 /* Same root finalization order as stock5316cd28. */
 uint32_t root=v->widgets[ROOT],*table=(uint32_t *)(uintptr_t)*(uint32_t *)(uintptr_t)root;
 ((fn1)(uintptr_t)table[0x28/4])(root);
 ((fn1)(uintptr_t)table[0x34/4])(root);
 return 0;
fail:m10v_settings_view_destroy(v);return -1;
}
static uint32_t film(const m10v_settings *s,const m10v_settings_ops *o,uint32_t i){
 uint32_t id;
 if(s->screen==M10V_SETTINGS_CATALOG){
  uint32_t index=(s->index/5)*5+i;
  id=index<256&&o&&o->item?o->item(o->context,index):0;
  if(id<33)id=0;
 }else id=s->saved.slots[i].film;
 return id&&id<=M10V_FILM_COUNT?id:0;
}
static uint32_t valueres(uint32_t row,uint32_t value){
 static const uint16_t first[4]={M10V_VIEW_OFF,M10V_VIEW_YMD,M10V_VIEW_TOP_LEFT,M10V_VIEW_WHITE};
 return row<4&&value<(row?4u:3u)?first[row]+value:M10V_VIEW_OFF;
}
void m10v_settings_view_draw(m10v_settings_view *v,const m10v_settings *s,const m10v_settings_ops *o){
 if(!v||!s||v->count!=COUNT)return;
 uint32_t films=s->screen==M10V_SETTINGS_FILMS||s->screen==M10V_SETTINGS_CATALOG;
 uint32_t focus=s->screen==M10V_SETTINGS_CATALOG?s->index%5:s->focus;
 caption(v->widgets[TITLE],films?M10V_VIEW_FILMS:M10V_VIEW_STAMP);
 caption(v->widgets[FOOTER],s->screen==M10V_SETTINGS_CATALOG?M10V_VIEW_CATALOG_HELP:
   s->screen==M10V_SETTINGS_FILMS?M10V_VIEW_FILM_HELP:
   s->screen==M10V_SETTINGS_VALUE?M10V_VIEW_VALUE_HELP:M10V_VIEW_STAMP_HELP);
 visible(v->widgets[NAME],films);
 visible(v->widgets[ERROR_TEXT],s->error>=1&&s->error<=3);
 if(s->error>=1&&s->error<=3)caption(v->widgets[ERROR_TEXT],M10V_VIEW_EMPTY+s->error-1);
 for(uint32_t i=0;i<5;i++){
  uint32_t id=films?film(s,o,i):0;
  visible(v->widgets[FRAME+i],films);visible(v->widgets[INNER+i],films);
  visible(v->widgets[ICON+i],films&&id);
  /* Palette6 YCbCr=(225,0,148): stock yellow. Palette18 is gray. */
  color(v->widgets[FRAME+i],i==focus?6:18);
  if(id)((fn2)0x5339a9a0u)(v->widgets[ICON+i],670+id);
 }
 if(films){
  uint32_t id=focus<5?film(s,o,focus):0;
  const char *name=id?m10v_library_name(id):0;
  ((fn2)0x53390ef8u)(v->widgets[NAME],ptr(name?name:""));
 }
 uint32_t values[4]={s->saved.stamp,s->saved.format,s->saved.corner,s->saved.color};
 if(s->screen==M10V_SETTINGS_VALUE&&s->focus<4)values[s->focus]=s->value;
 for(uint32_t i=0;i<4;i++){
  uint32_t w=v->widgets[ROW+i],value=v->widgets[VALUE+i];
  visible(w,!films);visible(value,!films);
  caption(w,M10V_VIEW_MODE+i);caption(value,valueres(i,values[i]));
  ((fn2)0x5339658cu)(w,i==s->focus?6:31);
  ((fn2)0x5339658cu)(value,i==s->focus?6:31);
 }
 if(!films&&s->focus<4)caption(v->widgets[TITLE],s->screen==M10V_SETTINGS_VALUE?
   M10V_VIEW_MODE+s->focus:M10V_VIEW_STAMP);
 ((fn1)0x533ad308u)(v->widgets[ROOT]);
}
