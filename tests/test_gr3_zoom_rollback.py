"""28..50 rollback: preserve valid old journal values, bound future changes."""
import subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=r'''
#include "m10v_zoom.h"
#include <assert.h>
#include <string.h>
#include <stdint.h>
static uint8_t page[24];
static uint32_t crc(const uint8_t*b){uint32_t c=~0u;for(int i=0;i<20;i++){c^=b[i];for(int k=0;k<8;k++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return ~c;}
static int rd(void*c,unsigned p,void*out,unsigned n){(void)c;if(p)return 0;memcpy(out,page,n);return 1;}
static void put(unsigned o,uint32_t v){memcpy(page+o,&v,4);}
int main(){m10v_zoom_io io={0,rd,0};m10v_zoom_state s;m10v_zoom_editor e;
 for(unsigned mm=28;mm<=50;mm++){union{float f;uint32_t u;} v={(float)mm/28};assert(m10v_zoom_bits(mm)==v.u);assert(m10v_zoom_mm(v.u)==mm);}
 assert(m10v_zoom_bits(51)==0&&m10v_zoom_bits(80)==0);
 put(0,0x315a304d);put(4,1);put(8,20);put(12,40);put(16,80);put(20,crc(page));
 assert(m10v_zoom_load(&s,&io)==1);assert(s.sequence==20&&s.mm[0]==40&&s.mm[1]==50);
 m10v_zoom_open(&e,&s,1);m10v_zoom_adjust(&e,1);assert(e.value==50);
 m10v_zoom_open(&e,&s,0);for(int i=0;i<100;i++)m10v_zoom_adjust(&e,-1);assert(e.value==28);
 put(12,101);put(20,crc(page));assert(m10v_zoom_load(&s,&io)==0);assert(s.mm[0]==35&&s.mm[1]==50);
}
'''
class Rollback(unittest.TestCase):
 def test_range_and_legacy_journal(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(C)
   subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(ROOT/'native/gr3'),str(p/'test.c'),str(ROOT/'native/gr3/m10v_zoom.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
