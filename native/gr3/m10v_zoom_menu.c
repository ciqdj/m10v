#include "m10v_zoom_menu.h"
#include "m10v_settings.h"
static void draft(m10v_zoom_menu *s){
 s->editing=0;
 if(s->focus)m10v_zoom_open(&s->editor,&s->saved,s->focus-1);
}
void m10v_zoom_menu_open(m10v_zoom_menu *s,const m10v_zoom_menu_ops *o){
 for(unsigned i=0;i<sizeof(*s);i++)((uint8_t *)s)[i]=0;
 s->saved.mm[0]=M10V_ZOOM_DEFAULT_FIRST;s->saved.mm[1]=M10V_ZOOM_DEFAULT_SECOND;
 if(!o||!o->load||o->load(&s->saved)<0){s->error=2;return;}
 unsigned selected=o->current?o->current():2;
 s->selected=selected<2?selected:2;s->focus=s->selected==2?0:s->selected+1;draft(s);
}
void m10v_zoom_menu_key(m10v_zoom_menu *s,const m10v_zoom_menu_ops *o,uint32_t key){
 if(!s||s->closed)return;
 if(key==M10V_KEY_BACK){s->closed=1;return;}
 if(s->error==2)return;
 if(key==M10V_KEY_UP||key==M10V_KEY_DOWN){
  s->focus=(s->focus+(key==M10V_KEY_UP?2:1))%3;s->error=0;draft(s);return;
 }
 if(key==M10V_KEY_LEFT||key==M10V_KEY_RIGHT){
  if(s->focus){m10v_zoom_adjust(&s->editor,key==M10V_KEY_LEFT?-1:1);s->editing=1;s->error=0;}return;
 }
 if(key!=M10V_KEY_OK)return;
 unsigned slot=s->focus?s->focus-1:2;
 if(s->editing&&s->editor.value!=s->saved.mm[slot]){
  uint32_t sequence=s->saved.sequence;
  int result=o&&o->save?o->save(&s->saved,&s->editor):-1;
  if(result==M10V_ZOOM_STALE){
   if(!o||!o->load||o->load(&s->saved)<0){s->error=2;s->editing=0;}
   else{s->error=1;draft(s);}return;
  }
  if(result){s->error=1;if(sequence!=s->saved.sequence)draft(s);return;}
  draft(s);
 }
 if(!o||!o->select||o->select(slot)){s->error=1;return;}
 s->selected=slot;s->error=0;s->closed=1;
}
