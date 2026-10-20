"""Independent-page interaction contract, with storage failures at the boundary."""
import subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include "m10v_settings.h"
#include <assert.h>
#include <string.h>
static m10v_library_state saved;
static unsigned ids[M10V_FILM_COUNT-32], writes, fail;
static int load(void *ctx,m10v_library_state *s){(void)ctx;*s=saved;return 0;}
static unsigned item(void *ctx,unsigned index){(void)ctx;return index<M10V_FILM_COUNT-32?ids[index]:0;}
static int install(void *ctx,unsigned index,unsigned id,unsigned slot){(void)ctx;
 if(fail||index>=M10V_FILM_COUNT-32||ids[index]!=id)return -1; saved.slots[slot].film=id;writes++;return 0;}
static int stamp(void *ctx,unsigned mode,unsigned format,unsigned corner,unsigned color){(void)ctx;
 if(fail)return -1;saved.stamp=mode;saved.format=format;saved.corner=corner;saved.color=color;writes++;return 0;}
static int name_stamp(void *ctx,unsigned enabled){(void)ctx;if(fail)return -1;saved.reserved=enabled;writes++;return 0;}
int main(void){
 m10v_settings p; m10v_settings_ops ops={0,load,item,install,stamp,name_stamp};
 memset(&saved,0,sizeof(saved));memset(saved.effects,7,sizeof(saved.effects));for(unsigned i=0;i<5;i++)saved.slots[i].film=33+i;
 for(unsigned i=0;i<M10V_FILM_COUNT-32;i++)ids[i]=33+i;
 assert(m10v_settings_open(&p,&ops,M10V_SETTINGS_FILMS)==0);
 assert(p.screen==M10V_SETTINGS_FILMS&&p.focus==0);
 for(unsigned i=0;i<4;i++)m10v_settings_key(&p,&ops,M10V_KEY_RIGHT);
 m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_CATALOG&&p.slot==4&&writes==0);
 m10v_settings_key(&p,&ops,M10V_KEY_DOWN);assert(p.index==5);
 m10v_settings_key(&p,&ops,M10V_KEY_UP);assert(p.index==0);
 m10v_settings_key(&p,&ops,M10V_KEY_RIGHT);assert(p.expected==34);
 ids[1]=35;m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(writes==0&&p.error==M10V_SETTINGS_CHANGED);
 ids[1]=34;m10v_settings_key(&p,&ops,M10V_KEY_LEFT);m10v_settings_key(&p,&ops,M10V_KEY_RIGHT);
 fail=1;m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(writes==0&&p.screen==M10V_SETTINGS_CATALOG);
 fail=0;m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(writes==1&&saved.slots[4].film==34&&p.screen==M10V_SETTINGS_FILMS);
 assert(p.focus==4);m10v_settings_key(&p,&ops,M10V_KEY_OK);m10v_settings_key(&p,&ops,M10V_KEY_BACK);assert(writes==1);
 m10v_settings_key(&p,&ops,M10V_KEY_BACK);assert(p.screen==M10V_SETTINGS_CLOSED);
 assert(m10v_settings_open(&p,&ops,M10V_SETTINGS_STAMP)==0);
 for(unsigned field=0;field<4;field++){
  unsigned max=field?4:3;
  for(unsigned value=1;value<max;value++){
   m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_VALUE);
   m10v_settings_key(&p,&ops,M10V_KEY_RIGHT);
   m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_STAMP);
   assert(((unsigned char*)&saved.stamp)[field]==value);
  }
  m10v_settings_key(&p,&ops,M10V_KEY_DOWN);
 }
 for(unsigned i=0;i<sizeof(saved.effects);i++)assert(((unsigned char*)saved.effects)[i]==7);
 assert(p.focus==3); /* Time page has exactly four fields. */
 assert(m10v_settings_open(&p,&ops,5)==0); /* Independent film-name page. */
 unsigned before=writes; m10v_settings_key(&p,&ops,M10V_KEY_RIGHT);
 m10v_settings_key(&p,&ops,M10V_KEY_BACK);assert(writes==before);
 assert(m10v_settings_open(&p,&ops,5)==0);
 m10v_settings_key(&p,&ops,M10V_KEY_RIGHT);fail=1;
 m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(writes==before&&p.screen==5&&p.error==M10V_SETTINGS_SAVE_FAILED);
 fail=0;m10v_settings_key(&p,&ops,M10V_KEY_OK);
 assert(saved.reserved==1&&p.screen==M10V_SETTINGS_CLOSED&&writes==before+1);
 ids[0]=73;assert(m10v_settings_open(&p,&ops,M10V_SETTINGS_FILMS)==0);
 m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(p.screen==M10V_SETTINGS_CATALOG&&p.expected==73);
 m10v_settings_key(&p,&ops,M10V_KEY_OK);assert(saved.slots[0].film==73&&p.screen==M10V_SETTINGS_FILMS);
 assert(m10v_settings_open(&p,&ops,M10V_SETTINGS_FILMS)==0);
 assert(m10v_settings_open(&p,&ops,99)<0);
 return 0;
}
'''
class IndependentSettingsTests(unittest.TestCase):
 def test_transactional_navigation_and_all_stamp_values(self):
  self.assertTrue((ROOT/'native/gr3/m10v_settings.c').exists(),'independent settings controller is missing')
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp);(path/'test.c').write_text(HARNESS)
   subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(ROOT/'native/gr3'),str(path/'test.c'),str(ROOT/'native/gr3/m10v_settings.c'),'-o',str(path/'test')],check=True)
   subprocess.run([str(path/'test')],check=True)
