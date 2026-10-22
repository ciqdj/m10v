#include "m10v_zoom_menu.h"
#include "m10v_settings.h"
void m10v_zoom_menu_open(m10v_zoom_menu *s,const m10v_zoom_menu_ops *o){
 for(unsigned i=0;i<sizeof(*s);i++)((uint8_t *)s)[i]=0;
 s->saved.mm[0]=35;s->saved.mm[1]=50;
 if(!o||!o->load||o->load(&s->saved)<0)s->error=2;
}
void m10v_zoom_menu_key(m10v_zoom_menu *s,const m10v_zoom_menu_ops *o,uint32_t key){
 if(!s||s->closed)return;
 if(key==M10V_KEY_BACK){if(s->editing){s->editing=0;s->error=0;}else s->closed=1;return;}
 if(s->error==2)return;
 if(!s->editing){
  if(key==M10V_KEY_UP||key==M10V_KEY_DOWN){s->focus^=1;s->error=0;}
  else if(key==M10V_KEY_OK){m10v_zoom_open(&s->editor,&s->saved,s->focus);s->editing=1;s->error=0;}
  return;
 }
 if(key==M10V_KEY_LEFT||key==M10V_KEY_RIGHT){m10v_zoom_adjust(&s->editor,key==M10V_KEY_LEFT?-1:1);s->error=0;}
 else if(key==M10V_KEY_OK){
  uint32_t sequence=s->saved.sequence;
  int result=o&&o->save?o->save(&s->saved,&s->editor):-1;
  if(result==M10V_ZOOM_STALE){
   /* Another committed configuration invalidated this editor snapshot.
    * Reload before accepting a new edit; never retry a permanently stale ID. */
   if(!o||!o->load||o->load(&s->saved)<0){s->error=2;s->editing=0;}
   else{s->error=1;m10v_zoom_open(&s->editor,&s->saved,s->focus);}
  }else if(result){s->error=1;/* Commit may have succeeded but native apply failed. */
   if(sequence!=s->saved.sequence)m10v_zoom_open(&s->editor,&s->saved,s->focus);
  }else{s->editing=0;s->error=0;}
 }
}
