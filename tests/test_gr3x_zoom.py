"""IIIx lens adaptation exercises real shared C geometry and durable state."""
import subprocess
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Gr3xZoomTests(unittest.TestCase):
 def test_lens_ratios_defaults_persistence_and_capture_geometry(self):
  source=r'''
#include "m10v_zoom.h"
#include "m10v_zoom_capture.h"
#include <assert.h>
#include <string.h>
static unsigned char pages[2][24];static int present[2];
static int rd(void *c,unsigned p,void *b,unsigned n){(void)c;if(!present[p])return 0;memcpy(b,pages[p],n);return 1;}
static int wr(void *c,unsigned p,const void *b,unsigned n){(void)c;memcpy(pages[p],b,n);present[p]=1;return 1;}
int main(void){
 for(unsigned mm=40;mm<=71;mm++){union{float f;unsigned u;} ratio={(float)mm/40.0f};if(mm==71)ratio.u=0x3fe49249;assert(m10v_zoom_bits(mm)==ratio.u);assert(m10v_zoom_mm(ratio.u)==mm);}
 assert(!m10v_zoom_bits(39)&&!m10v_zoom_bits(72));
 m10v_zoom_state s,t;m10v_zoom_io io={0,rd,wr};assert(!m10v_zoom_load(&s,&io));assert(s.mm[0]==50&&s.mm[1]==71);
 m10v_zoom_editor e;m10v_zoom_open(&e,&s,0);m10v_zoom_adjust(&e,1);assert(!m10v_zoom_save(&s,&e,&io));
 assert(m10v_zoom_load(&t,&io)==1&&t.mm[0]==51&&t.mm[1]==71);
 assert(!m10v_zoom_bits(28));
 unsigned char marker[3];assert(m10v_zoom_capture_marker_encode(60,marker));assert(m10v_zoom_capture_marker_decode(marker)==60);
 assert(!m10v_zoom_capture_marker_encode(40,marker));assert(!m10v_zoom_capture_marker_encode(50,marker));assert(!m10v_zoom_capture_marker_encode(71,marker));
 m10v_zoom_capture_rect rect;assert(m10v_zoom_capture_geometry(60,6000,4000,6000,4000,&rect));assert(rect.width==4000&&rect.height==2656&&rect.x==1000);
 assert(m10v_zoom_capture_quality_count(45)==4&&m10v_zoom_capture_quality_count(60)==3);
 return 0;}
'''
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'test.c').write_text(source)
   subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-DM10V_CAMERA_GR3X=1','-I',str(ROOT/'native/gr3'),str(p/'test.c'),str(ROOT/'native/gr3/m10v_zoom.c'),str(ROOT/'native/gr3/m10v_zoom_capture.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_stock_40_50_71_captions_delegate_and_custom_60_uses_numeric_caption(self):
  import ctypes
  names=['m10v_zoom_original_marker_write','m10v_zoom_original_marker_read','m10v_zoom_original_marker_summary','m10v_zoom_original_raw_count','m10v_zoom_original_raw_value','m10v_zoom_capture_raw_bits','m10v_zoom_capture_native_resolution','m10v_zoom_native_ifd_byte','m10v_zoom_native_ifd_write_byte','m10v_zoom_native_summary_write','m10v_zoom_original_replay_rect']
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'stubs.c').write_text('#include <stdint.h>\n'+'\n'.join('uint32_t '+name+'(void){return 0;}' for name in names))
   subprocess.run(['clang','-shared','-fPIC','-DM10V_CAMERA_GR3X=1',str(ROOT/'native/gr3/m10v_zoom.c'),str(ROOT/'native/gr3/m10v_zoom_capture.c'),str(ROOT/'native/gr3/m10v_zoom_capture_adapters.c'),str(p/'stubs.c'),'-o',str(p/'zoom.dylib')],check=True,capture_output=True)
   lib=ctypes.CDLL(str(p/'zoom.dylib'));lib.m10v_zoom_capture_caption.restype=ctypes.c_uint32
   for bits in [0x3f800000,0x3fa00000,0x3fe49249]:
    self.assertEqual(lib.m10v_zoom_capture_custom(bits),0)
    self.assertEqual(lib.m10v_zoom_capture_caption(bits),0xffffffff)
   self.assertEqual(lib.m10v_zoom_capture_caption(0x3fc00000),1063)
