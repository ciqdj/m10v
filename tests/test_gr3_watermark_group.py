import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class WatermarkGroupTests(unittest.TestCase):
 def test_children_return_to_parent_and_browsing_never_writes(self):
  source=r'''
#include "m10v_settings.h"
#include <assert.h>
#include <string.h>
static m10v_library_state saved;static unsigned writes,fail;
int m10v_library_valid(const m10v_library_state *s){(void)s;return 1;}
uint32_t m10v_library_count(const m10v_library_state *s){(void)s;return 0;}
static int load(void*c,m10v_library_state*s){(void)c;*s=saved;return 0;}
static unsigned item(void*c,unsigned i){(void)c;(void)i;return 0;}
static int install(void*c,unsigned i,unsigned id,unsigned k){(void)c;(void)i;(void)id;(void)k;return -1;}
static int remove_film(void*c,unsigned k){(void)c;(void)k;return -1;}
static int stamp(void*c,unsigned m,unsigned f,unsigned k,unsigned v){(void)c;if(fail)return -1;saved.stamp=m;saved.format=f;saved.corner=k;saved.color=v;writes++;return 0;}
static int name(void*c,unsigned v){(void)c;if(fail)return -1;saved.reserved=v;writes++;return 0;}
int main(void){
 m10v_settings p; m10v_settings_ops o={0,load,item,install,remove_film,stamp,name};
 memset(&saved,0,sizeof(saved));saved.format=3;saved.corner=2;saved.color=1;
 assert(m10v_settings_open(&p,&o,M10V_SETTINGS_WATERMARK)==0);
 assert(p.screen==M10V_SETTINGS_WATERMARK&&p.focus==0);
 m10v_settings_key(&p,&o,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_STAMP);
 m10v_settings_key(&p,&o,M10V_KEY_OK);m10v_settings_key(&p,&o,M10V_KEY_RIGHT);
 m10v_settings_key(&p,&o,M10V_KEY_BACK);assert(writes==0&&saved.stamp==0);
 m10v_settings_key(&p,&o,M10V_KEY_BACK);assert(p.screen==M10V_SETTINGS_WATERMARK&&p.focus==0);
 m10v_settings_key(&p,&o,M10V_KEY_DOWN);m10v_settings_key(&p,&o,M10V_KEY_OK);
 assert(p.screen==M10V_SETTINGS_NAME);m10v_settings_key(&p,&o,M10V_KEY_RIGHT);
 m10v_settings_key(&p,&o,M10V_KEY_BACK);assert(writes==0&&p.screen==M10V_SETTINGS_WATERMARK&&p.focus==1);
 m10v_settings_key(&p,&o,M10V_KEY_OK);m10v_settings_key(&p,&o,M10V_KEY_RIGHT);fail=1;
 m10v_settings_key(&p,&o,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_NAME&&writes==0);
 fail=0;m10v_settings_key(&p,&o,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_WATERMARK&&saved.reserved==1&&writes==1);
 assert(saved.format==3&&saved.corner==2&&saved.color==1);
 m10v_settings_key(&p,&o,M10V_KEY_BACK);assert(p.screen==M10V_SETTINGS_CLOSED);
 return 0;
}'''
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'test.c').write_text(source)
   subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-I',str(ROOT/'native/gr3'),str(p/'test.c'),str(ROOT/'native/gr3/m10v_settings.c'),'-o',str(p/'test')],check=True,capture_output=True)
   subprocess.run([str(p/'test')],check=True)
