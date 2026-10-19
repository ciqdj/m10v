/* Standalone primitive view. No ImageControl objects, model padding or hooks.
 * ABI evidence: original GR III 2.10 factory 533ad7f0 and constructors below.
 * Every top-level allocation is checked BEFORE invoking its constructor.
 * Remaining stock limitation: child-vector growth and text setters allocate
 * internally without a recoverable OOM contract. This is NOT a hardware proof.
 */
#include "m10v_settings_view.h"
#include "m10v_film_card.h"
#ifndef M10V_NATIVE_BASE
#define M10V_NATIVE_BASE 0x540b6000u
#endif
/* One film controller owns five live bitmaps; timestamp views allocate none.
 * Reserved widgets[39] is storage, outside the 37 child-widget entries. */
static uint32_t *card_descriptors(const m10v_settings_view *v){return (uint32_t *)(uintptr_t)(v->widgets[39]+5*M10V_CARD_PIXELS*4);}
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn2)(uint32_t,uint32_t);
typedef uint32_t (*fn3)(uint32_t,uint32_t,uint32_t);
typedef uint32_t (*ctor)(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t);
enum { ROOT, BACKGROUND, TITLE, NAME, FOOTER, ERROR_TEXT,
 FRAME=6, INNER=11, ICON=16, ROW_FRAME=21, ROW_INNER=25, ROW=29, VALUE=33, COUNT=M10V_VIEW_COUNT };
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
 if(!v||v->count>M10V_VIEW_CAPACITY)return;
 ((fn3)0x5316cde8u)(0,ptr(v->widgets),v->count);
 if(v->widgets[39]){
  uint32_t heap=v->widgets[39];v->widgets[39]=0;
  ((fn1)0x536af2e4u)(heap);
 }
 for(uint32_t i=0;i<M10V_VIEW_CAPACITY;i++)v->widgets[i]=0;
 v->count=0;
}
int m10v_settings_view_create(m10v_settings_view *v){
 if(!v||v->count)return -1;
 for(uint32_t i=0;i<M10V_VIEW_CAPACITY;i++)v->widgets[i]=0;
 if(make(v,1,0,0,720,480)||make(v,11,0,0,720,480)||
    make(v,17,20,12,680,42)||make(v,0,24,348,672,44)||
    make(v,17,20,430,680,40)||make(v,17,20,375,680,40))goto fail;
 for(uint32_t i=0;i<5;i++)if(make(v,11,24+i*136,102,128,204))goto fail;
 for(uint32_t i=0;i<5;i++)if(make(v,11,26+i*136,104,124,200))goto fail;
 for(uint32_t i=0;i<5;i++)if(make(v,10,28+i*136,106,120,196))goto fail;
 /* Selection rectangles precede text in the child draw order. */
 for(uint32_t i=0;i<4;i++)if(make(v,11,24,84+i*72,672,64))goto fail;
 for(uint32_t i=0;i<4;i++)if(make(v,11,30,90+i*72,660,52))goto fail;
 for(uint32_t i=0;i<4;i++)if(make(v,17,36,90+i*72,300,52))goto fail;
 for(uint32_t i=0;i<4;i++)if(make(v,17,350,90+i*72,330,52))goto fail;
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
 caption(v->widgets[TITLE],s->screen==M10V_SETTINGS_CATALOG?M10V_VIEW_CHOOSE_FILM:films?M10V_VIEW_FILMS:M10V_VIEW_STAMP);
 caption(v->widgets[FOOTER],s->screen==M10V_SETTINGS_CATALOG?M10V_VIEW_CATALOG_HELP:
   s->screen==M10V_SETTINGS_FILMS?M10V_VIEW_FILM_HELP:
   s->screen==M10V_SETTINGS_VALUE?M10V_VIEW_VALUE_HELP:M10V_VIEW_STAMP_HELP);
 visible(v->widgets[NAME],films);
 visible(v->widgets[ERROR_TEXT],s->error>=1&&s->error<=3);
 if(s->error>=1&&s->error<=3)caption(v->widgets[ERROR_TEXT],M10V_VIEW_EMPTY+s->error-1);
 if(films&&!v->widgets[39])v->widgets[39]=((fn1)0x536af2a8u)(5*M10V_CARD_PIXELS*4+64);
 for(uint32_t i=0;i<5;i++){
  uint32_t id=films?film(s,o,i):0;
  visible(v->widgets[FRAME+i],films);visible(v->widgets[INNER+i],films);
  visible(v->widgets[ICON+i],films&&id);
  /* Rectangle palette6 is yellow; unselected frames use background1. */
  color(v->widgets[FRAME+i],i==focus?6:1);
  if(id){
   uint32_t icon=670+id;
   if(v->widgets[39]){
    uint32_t *pixels=(uint32_t *)(uintptr_t)(v->widgets[39]+i*M10V_CARD_PIXELS*4);
    m10v_film_card_render(pixels,id,i,i==focus);
    uint32_t *all=card_descriptors(v),*d=all+i*2;
    d[0]=M10V_CARD_WIDTH|(M10V_CARD_HEIGHT<<16);d[1]=ptr(pixels)/4;
    all[10+i]=ptr(d);
    icon=M10V_CARD_FIRST+i;
   }
   ((fn2)0x5339a9a0u)(v->widgets[ICON+i],icon);
  }
 }
 if(films){
  uint32_t id=focus<5?film(s,o,focus):0;
  const char *name=id?m10v_library_name(id):0;
  /* Bounded ASCII copy; the stock setter owns its UTF-16 copy afterwards. */
  char label[96];uint32_t n=0,number=s->screen==M10V_SETTINGS_CATALOG?s->index+1:focus+1;
  if(number>=100)label[n++]=(char)('0'+number/100);
  if(number>=10)label[n++]=(char)('0'+(number/10)%10);
  label[n++]=(char)('0'+number%10);
  if(s->screen==M10V_SETTINGS_FILMS){label[n++]=' ';label[n++]='/';label[n++]=' ';label[n++]='5';}
  label[n++]=' ';label[n++]=' ';
  if(name)for(uint32_t j=0;name[j]&&n<sizeof(label)-1;j++)label[n++]=name[j];
  label[n]=0;
  ((fn2)0x53390ef8u)(v->widgets[NAME],ptr(label));
 }
 uint32_t values[4]={s->saved.stamp,s->saved.format,s->saved.corner,s->saved.color};
 if(s->screen==M10V_SETTINGS_VALUE&&s->focus<4)values[s->focus]=s->value;
 for(uint32_t i=0;i<4;i++){
  uint32_t w=v->widgets[ROW+i],value=v->widgets[VALUE+i];
  uint32_t selected=!films&&i==s->focus;
  visible(v->widgets[ROW_FRAME+i],selected);visible(v->widgets[ROW_INNER+i],selected);
  color(v->widgets[ROW_FRAME+i],6);color(v->widgets[ROW_INNER+i],1);
  visible(w,!films);visible(value,!films);
  caption(w,M10V_VIEW_MODE+i);caption(value,valueres(i,values[i]));
  /* Text enum10 selects the yellow glyph table; enum6 falls back to WHITE. */
  ((fn2)0x5339658cu)(w,selected&&s->screen!=M10V_SETTINGS_VALUE?10:31);
  ((fn2)0x5339658cu)(value,selected?10:31);
 }
 if(!films&&s->focus<4)caption(v->widgets[TITLE],s->screen==M10V_SETTINGS_VALUE?
   M10V_VIEW_EDIT_MODE+s->focus:M10V_VIEW_STAMP);
 ((fn1)0x533ad308u)(v->widgets[ROOT]);
}
