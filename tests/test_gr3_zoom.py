"""Two editable crop slots: transactional edits and independent durable storage.

These host tests do not establish native capture/preview support.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include "m10v_zoom.h"
#include <assert.h>
#include <string.h>
static unsigned char pages[2][M10V_ZOOM_BYTES];
static int present[2], fail_write, fail_read, corrupt_read, writes;
static int read_page(void *ctx,unsigned page,void *out,unsigned size){
 (void)ctx;if(fail_read)return -1;if(!present[page])return 0;
 memcpy(out,pages[page],size);if(corrupt_read)((unsigned char *)out)[15]^=1;return 1;
}
static int write_page(void *ctx,unsigned page,const void *in,unsigned size){
 (void)ctx;if(fail_write)return 0;
 memcpy(pages[page],in,size);present[page]=1;writes++;return 1;
}
int main(void){
 for(unsigned mm=28;mm<=100;mm++){
  union {float f;unsigned u;} native={(float)mm/28.0f};
  assert(m10v_zoom_bits(mm)==native.u);
  assert(m10v_zoom_mm(native.u)==mm);
 }
 assert(m10v_zoom_bits(27)==0&&m10v_zoom_bits(101)==0);
 assert(m10v_zoom_mm(0)==0&&m10v_zoom_mm(0x7fc00000)==0);
 assert(m10v_zoom_mm(0x7f800000)==0&&m10v_zoom_mm(0xbf800000)==0);
 assert(m10v_zoom_mm(0x3f800001)==0);
 m10v_zoom_io io={0,read_page,write_page};m10v_zoom_state s,t;
 assert(m10v_zoom_load(&s,&io)==0);
 assert(s.mm[0]==35&&s.mm[1]==50);
 fail_read=1;assert(m10v_zoom_load(&s,&io)<0);fail_read=0;
 m10v_zoom_editor e;m10v_zoom_open(&e,&s,0);
 m10v_zoom_adjust(&e,1);assert(e.value==36&&s.mm[0]==35&&writes==0);
 m10v_zoom_adjust(&e,-1);assert(e.value==35);
 m10v_zoom_adjust(&e,1);assert(m10v_zoom_save(&s,&e,&io)==0);
 assert(s.mm[0]==36&&s.mm[1]==50&&writes==1);
 assert(m10v_zoom_load(&t,&io)==1&&t.mm[0]==36&&t.mm[1]==50);
 m10v_zoom_open(&e,&s,1);m10v_zoom_adjust(&e,-1);
 fail_write=1;t=s;assert(m10v_zoom_save(&s,&e,&io)<0);
 assert(!memcmp(&s,&t,sizeof(s))&&e.value==49);
 fail_write=0;assert(m10v_zoom_save(&s,&e,&io)==0);
 assert(s.mm[0]==36&&s.mm[1]==49);
 /* Damage the newest page. Reboot must recover the previous whole record. */
 pages[s.sequence&1][15]^=1;
 assert(m10v_zoom_load(&t,&io)==1&&t.mm[0]==36&&t.mm[1]==50);
 /* Stale editor must not overwrite a change made after opening it. */
 m10v_zoom_open(&e,&t,0);m10v_zoom_adjust(&e,1);
 m10v_zoom_editor other;m10v_zoom_open(&other,&t,1);
 m10v_zoom_adjust(&other,-1);assert(m10v_zoom_save(&t,&other,&io)==0);
 s=t;assert(m10v_zoom_save(&t,&e,&io)==M10V_ZOOM_STALE);
 assert(!memcmp(&s,&t,sizeof(s)));
 /* Identical slots are valid; their identities must remain distinct. */
 m10v_zoom_open(&e,&t,1);e.value=t.mm[0];
 assert(m10v_zoom_save(&t,&e,&io)==0&&t.mm[0]==t.mm[1]);
 m10v_zoom_open(&e,&t,0);
 for(unsigned i=0;i<300;i++)m10v_zoom_adjust(&e,-1);
 assert(e.value==28);
 for(unsigned i=0;i<300;i++)m10v_zoom_adjust(&e,1);
 assert(e.value==M10V_ZOOM_MAX_MM);
 /* No-op saves do not wear storage. Cancel discards the editor. */
 m10v_zoom_open(&e,&t,0);int before=writes;
 assert(m10v_zoom_save(&t,&e,&io)==0&&writes==before);
 m10v_zoom_adjust(&e,1);m10v_zoom_open(&e,&t,0);
 assert(e.value==t.mm[0]&&writes==before);
 /* A successful write with a failed readback must not publish new state. */
 m10v_zoom_adjust(&e,1);s=t;corrupt_read=1;
 assert(m10v_zoom_save(&t,&e,&io)<0&&!memcmp(&s,&t,sizeof(s)));
 corrupt_read=0;
 /* Invalid slot and corrupted records cannot become active geometry. */
 m10v_zoom_open(&e,&t,2);assert(m10v_zoom_save(&t,&e,&io)<0);
 memset(pages,0xff,sizeof(pages));assert(m10v_zoom_load(&s,&io)==0);
 assert(s.mm[0]==35&&s.mm[1]==50);
 return 0;
}
'''

class ZoomTests(unittest.TestCase):
    def test_two_slots_edit_save_cancel_and_recovery(self):
        source = ROOT/'native/gr3/m10v_zoom.c'
        self.assertTrue(source.exists(), 'two-slot focal-length editor is missing')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'test.c').write_text(HARNESS)
            subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror',
                '-fsanitize=address,undefined','-I',str(source.parent),
                str(path/'test.c'),str(source),'-o',str(path/'test')],check=True)
            subprocess.run([str(path/'test')],check=True)
