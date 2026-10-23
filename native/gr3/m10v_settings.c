#include "m10v_tone.h"
#include "m10v_settings.h"
#define CATALOG_LIMIT 256u
static int ready(const m10v_settings_ops *o){return o&&o->load&&o->item&&o->install&&o->stamp&&o->film_name_stamp;}
static uint32_t item(const m10v_settings_ops *o,uint32_t i){
 if(i>=CATALOG_LIMIT)return 0;
 uint32_t id=o->item(o->context,i);return id>=33&&(id<=M10V_CUSTOM_MAX_ID||M10V_BUILTIN(id))?id:0;
}
static uint32_t value(const m10v_library_state *s,uint32_t field){
 return field==0?s->stamp:field==1?s->format:field==2?s->corner:field==3?s->color:s->reserved&1u;
}
int m10v_settings_open(m10v_settings *p,const m10v_settings_ops *o,uint32_t screen){
 if(!p||!ready(o))return -1;
 p->screen=M10V_SETTINGS_CLOSED;
 if(screen!=M10V_SETTINGS_FILMS&&screen!=M10V_SETTINGS_STAMP&&screen!=M10V_SETTINGS_NAME&&screen!=M10V_SETTINGS_AB)return -1;
 if(o->load(o->context,&p->saved)<0)return -1;
 if(p->saved.stamp>2||p->saved.format>3||p->saved.corner>3||p->saved.color>3)return -1;
 for(uint32_t i=0;i<5;i++)if(!p->saved.slots[i].film||(p->saved.slots[i].film>M10V_CUSTOM_MAX_ID&&!M10V_BUILTIN(p->saved.slots[i].film)))return -1;
 p->focus=p->slot=p->index=p->expected=p->value=p->error=0;
 p->screen=screen;if(screen==M10V_SETTINGS_AB){p->slot=1;p->index=5;}if(screen==M10V_SETTINGS_NAME)p->value=p->saved.reserved&1u;return 0;
}
void m10v_settings_key(m10v_settings *p,const m10v_settings_ops *o,uint32_t key){
 if(!p||!ready(o)||key>M10V_KEY_DISP)return;
 uint32_t previous=key==M10V_KEY_LEFT||key==M10V_KEY_UP;
 uint32_t next=key==M10V_KEY_RIGHT||key==M10V_KEY_DOWN;
 if(p->screen==M10V_SETTINGS_FILMS){
  if(p->focus>=5)return;
  if(previous&&p->focus)p->focus--;
  if(next&&p->focus<4)p->focus++;
  if(key==M10V_KEY_BACK)p->screen=M10V_SETTINGS_CLOSED;
  if(key==M10V_KEY_OK){
   uint32_t id=item(o,0);p->error=id?0:M10V_SETTINGS_EMPTY;
   if(id){p->slot=p->focus;p->index=0;p->expected=id;p->screen=M10V_SETTINGS_CATALOG;}
  }
 }else if(p->screen==M10V_SETTINGS_AB){
  p->value=0;
  if(key==M10V_KEY_UP&&p->focus)p->focus--;
  if(key==M10V_KEY_DOWN&&p->focus<3)p->focus++;
  uint32_t *slot=p->focus==0?&p->slot:&p->index;
  if(p->focus<2){
   if(key==M10V_KEY_LEFT&&*slot)(*slot)--;
   if(key==M10V_KEY_RIGHT&&*slot+1<M10V_TONE_CHOICES)(*slot)++;
  }
  if(key==M10V_KEY_BACK){p->screen=M10V_SETTINGS_CLOSED;p->error=0;}
  if(key==M10V_KEY_OK&&p->focus>=2)p->value=p->focus-1;
 }else if(p->screen==M10V_SETTINGS_CATALOG){
  if(p->slot>=5||p->index>=CATALOG_LIMIT)return;
  if(key==M10V_KEY_BACK){p->screen=M10V_SETTINGS_FILMS;p->focus=p->slot;p->error=0;return;}
  uint32_t i=p->index;
  if(previous&&i)i--;
  if(next)i++;
  if(key==M10V_KEY_PREVIOUS||key==M10V_KEY_UP)i=p->index>=5?p->index-5:0;
  if(key==M10V_KEY_NEXT||key==M10V_KEY_DOWN)i=p->index+5;
  if(i!=p->index){uint32_t id=item(o,i);if(id){p->index=i;p->expected=id;p->error=0;}}
  if(key==M10V_KEY_OK){
   if(!p->expected||item(o,p->index)!=p->expected){p->error=M10V_SETTINGS_CHANGED;return;}
   if(o->install(o->context,p->index,p->expected,p->slot)!=0){p->error=M10V_SETTINGS_SAVE_FAILED;return;}
   if(o->load(o->context,&p->saved)<0){p->error=M10V_SETTINGS_SAVE_FAILED;return;}
   p->focus=p->slot;p->screen=M10V_SETTINGS_FILMS;p->error=0;
  }
 }else if(p->screen==M10V_SETTINGS_NAME){
  if(previous)p->value=0;
  if(next)p->value=1;
  if(key==M10V_KEY_BACK)p->screen=M10V_SETTINGS_CLOSED;
  if(key==M10V_KEY_OK){
   if(o->film_name_stamp(o->context,p->value)!=0){p->error=M10V_SETTINGS_SAVE_FAILED;return;}
   p->saved.reserved=p->value;p->screen=M10V_SETTINGS_CLOSED;p->error=0;
  }
 }else if(p->screen==M10V_SETTINGS_STAMP){
  if(p->focus>=4)return;
  if(previous&&p->focus)p->focus--;
  if(next&&p->focus<3)p->focus++;
  if(key==M10V_KEY_BACK)p->screen=M10V_SETTINGS_CLOSED;
  if(key==M10V_KEY_OK){p->value=value(&p->saved,p->focus);p->screen=M10V_SETTINGS_VALUE;p->error=0;}
 }else if(p->screen==M10V_SETTINGS_VALUE){
  if(p->focus>=4)return;
  uint32_t max=p->focus==0?2:3;
  if(previous&&p->value)p->value--;
  if(next&&p->value<max)p->value++;
  if(key==M10V_KEY_BACK){p->screen=M10V_SETTINGS_STAMP;p->error=0;}
  if(key==M10V_KEY_OK){
   uint32_t v[4]={p->saved.stamp,p->saved.format,p->saved.corner,p->saved.color};
   if(p->value>max)return;
   if(p->focus<4)v[p->focus]=p->value;
   if(o->stamp(o->context,v[0],v[1],v[2],v[3])!=0){p->error=M10V_SETTINGS_SAVE_FAILED;return;}
   p->saved.stamp=(uint8_t)v[0];p->saved.format=(uint8_t)v[1];
   p->saved.corner=(uint8_t)v[2];p->saved.color=(uint8_t)v[3];
   p->screen=M10V_SETTINGS_STAMP;p->error=0;
  }
 }
}
