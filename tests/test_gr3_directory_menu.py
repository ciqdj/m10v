"""Real menu + journal functions: grouping, bounds, zero-write browsing and cap."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "m10v_settings.h"
#include <assert.h>
#include <string.h>
static const unsigned ids[]={33,66,62,78,298,77,69,37,70,73,56,36,35,58,74,34,71,67,68,292,75,289,72,293,296,290,76,291,297,65};
static m10v_library_state saved;
static unsigned writes,broken;
static int store(void *c,const m10v_library_state *s){(void)c;(void)s;writes++;return 0;}
static int load(void *c,m10v_library_state *s){(void)c;*s=saved;return 0;}
static unsigned item(void *c,unsigned i){(void)c;return i<30?broken==2?(i==2||i==5?ids[i]:0):broken==1&&i==0?34:ids[i]:0;}
static int install(void *c,unsigned i,unsigned id,unsigned slot){(void)c;assert(i<30&&ids[i]==id);return m10v_library_select(&saved,slot,id,store,0);}
static int remove_film(void *c,unsigned slot){(void)c;return m10v_library_remove(&saved,slot,store,0);}
static int stamp(void *c,unsigned a,unsigned b,unsigned d,unsigned e){(void)c;return m10v_library_stamp(&saved,a,b,d,e,store,0);}
static int name(void *c,unsigned v){(void)c;return m10v_library_film_name_stamp(&saved,v,store,0);}
int main(void){
 m10v_settings_ops o={0,load,item,install,remove_film,stamp,name};m10v_settings p;
 m10v_library_init(&saved);assert(m10v_settings_open(&p,&o,M10V_SETTINGS_FILMS)==0);
 assert(p.screen==8); /* group selector, not the old ungrouped catalogue */
 const unsigned first[]={0,6,20,21,27},count[]={6,14,1,6,3};
 for(unsigned g=0;g<5;g++){
  assert(p.focus==g);m10v_settings_key(&p,&o,M10V_KEY_OK);assert(p.screen==2&&p.index==first[g]&&p.expected==ids[first[g]]);
  for(unsigned n=1;n<count[g];n++){m10v_settings_key(&p,&o,M10V_KEY_RIGHT);assert(p.expected==ids[first[g]+n]);}
  m10v_settings_key(&p,&o,M10V_KEY_RIGHT);assert(p.index==first[g]+count[g]-1);
  m10v_settings_key(&p,&o,M10V_KEY_NEXT);assert(p.index==first[g]+count[g]-1);
  m10v_settings_key(&p,&o,M10V_KEY_BACK);assert(p.screen==8&&p.focus==g&&writes==0);
  if(g<4)m10v_settings_key(&p,&o,M10V_KEY_DOWN);
 }
 m10v_settings_key(&p,&o,M10V_KEY_BACK);assert(p.screen==0&&writes==0);
 m10v_settings_open(&p,&o,M10V_SETTINGS_FILMS);m10v_settings_key(&p,&o,M10V_KEY_DOWN);m10v_settings_key(&p,&o,M10V_KEY_OK);
 m10v_settings_key(&p,&o,M10V_KEY_NEXT);assert(p.index==16&&p.expected==71);
 m10v_settings_key(&p,&o,M10V_KEY_DOWN);assert(p.index==19&&p.expected==292);
 m10v_settings_key(&p,&o,M10V_KEY_PREVIOUS);assert(p.index==9&&p.expected==73&&writes==0);
 m10v_settings_key(&p,&o,M10V_KEY_BACK);m10v_settings_key(&p,&o,M10V_KEY_DOWN);m10v_settings_key(&p,&o,M10V_KEY_OK);
 m10v_settings_key(&p,&o,M10V_KEY_LEFT);m10v_settings_key(&p,&o,M10V_KEY_UP);assert(p.index==20&&p.expected==75&&writes==0);
 for(unsigned n=1;m10v_library_count(&saved)<10;n++){
  unsigned exists=0;for(unsigned k=0;k<10;k++)exists|=saved.slots[k].film==ids[n];
  if(!exists)assert(m10v_library_select(&saved,m10v_library_count(&saved),ids[n],store,0)==0);
 }
 unsigned before=writes;m10v_settings_open(&p,&o,M10V_SETTINGS_FILMS);m10v_settings_key(&p,&o,M10V_KEY_DOWN);m10v_settings_key(&p,&o,M10V_KEY_OK);m10v_settings_key(&p,&o,M10V_KEY_OK);
 assert(p.error==M10V_SETTINGS_FULL&&writes==before&&m10v_library_count(&saved)==10);
 m10v_settings_open(&p,&o,M10V_SETTINGS_FILMS);m10v_settings_key(&p,&o,M10V_KEY_OK);broken=1;m10v_settings_key(&p,&o,M10V_KEY_OK);assert(writes==before&&p.error);
 broken=2;m10v_settings_open(&p,&o,M10V_SETTINGS_FILMS);m10v_settings_key(&p,&o,M10V_KEY_OK);assert(p.index==2&&p.expected==62);m10v_settings_key(&p,&o,M10V_KEY_RIGHT);assert(p.index==5&&p.expected==77&&writes==before);
 const unsigned spectral[]={77,298};
 for(unsigned j=0;j<2;j++){
  m10v_library_state s;m10v_library_init(&s);assert(m10v_library_select(&s,0,spectral[j],store,0)==0);
  uint8_t y0[]={80,90,100,110,91,92,120,130,140,150,93,94},uv0[]={120,140,130,150,95,96,125,135,145,155,97,98};
  uint8_t y1[12],u1[12],y2[12],u2[12],scratch[4096];memcpy(y1,y0,12);memcpy(y2,y0,12);memcpy(u1,uv0,12);memcpy(u2,uv0,12);
  m10v_library_image a={y1,u1,12,12,4,2,6},b={y2,u2,12,12,4,2,6};
  assert(m10v_library_render_native(&a,&s,0,0,1,scratch,sizeof(scratch),0)==0);
  assert(m10v_library_render_native(&b,&s,0,0,1,scratch,sizeof(scratch),31)==0);
  assert(!memcmp(y1,y2,12)&&!memcmp(u1,u2,12));assert(memcmp(y1,y0,12)||memcmp(u1,uv0,12));
  assert(y1[4]==91&&y1[5]==92&&y1[10]==93&&y1[11]==94);
 }
 assert(!strcmp(m10v_library_name(298),"5213"));assert(!strcmp(m10v_library_name(290),"Pixel Worlds"));
 return 0;
}
'''
class DirectoryMenuTests(unittest.TestCase):
 def test_groups_navigation_cancel_stale_card_and_ten_film_limit(self):
  with tempfile.TemporaryDirectory() as tmp:
   t=Path(tmp);(t/'test.c').write_text(HARNESS)
   sources=['m10v_settings.c','m10v_library.c','halation_core.c','film_5207.c','film_harman.c','film_curated.c','film_newstocks.c','film_style_filters_0.c','film_style_filters_1.c']
   subprocess.run(['clang','-O1','-g','-DM10V_APPENDED_SLOTS=1','-fsanitize=address,undefined','-I',str(ROOT/'native/gr3'),str(t/'test.c'),*[str(ROOT/'native/gr3'/s) for s in sources],'-o',str(t/'test')],check=True,capture_output=True)
   result=subprocess.run([str(t/'test')],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
