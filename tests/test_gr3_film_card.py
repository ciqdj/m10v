"""Bounds checks for the native cartridge rasterizer used by the camera view."""
import ctypes as C
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class FilmCardTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  library=Path(cls.tmp.name)/'cards.so'
  subprocess.run(['clang','-shared','-fPIC','-O2','-Wall','-Wextra','-Werror',str(ROOT/'native/gr3/m10v_film_card.c'),'-o',str(library)],check=True,capture_output=True)
  cls.lib=C.CDLL(str(library));cls.draw=cls.lib.m10v_film_card_render
  cls.draw.argtypes=[C.POINTER(C.c_uint32),C.c_uint32,C.c_uint32,C.c_uint32];cls.draw.restype=C.c_int
 def test_all_films_fit_the_owned_buffer_and_emit_rgba(self):
  count=120*196;buffer=(C.c_uint32*(count+2))();pixels=C.cast(C.byref(buffer,4),C.POINTER(C.c_uint32))
  for film in range(1,79):
   for slot in range(5):
    buffer[0]=buffer[-1]=0x12345678
    self.assertEqual(self.draw(pixels,film,slot,slot==2),0)
    self.assertEqual((buffer[0],buffer[-1]),(0x12345678,0x12345678))
  self.draw(pixels,34,0,0) # Red Ektar label: RGBA, not blue ARGB bytes.
  at=(50*120+45)*4
  self.assertEqual(C.string_at(pixels,count*4)[at:at+4],bytes([233,42,64,255]))
 def test_invalid_catalog_or_slot_does_not_touch_pixels(self):
  pixels=(C.c_uint32*(120*196))(*([0x12345678]*(120*196)))
  before=bytes(pixels)
  for film,slot in [(0,0),(79,0),(1,5),(0xffffffff,0)]:
   self.assertEqual(self.draw(pixels,film,slot,0),-1);self.assertEqual(bytes(pixels),before)
  self.assertEqual(self.draw(None,1,0,0),-1)

 def test_custom_names_produce_distinct_bounded_art_without_builtin_alias(self):
  draw=self.lib.m10v_film_card_custom
  draw.argtypes=[C.POINTER(C.c_uint32),C.c_char_p,C.c_uint32,C.c_uint32]
  count=120*196;b=(C.c_uint32*(count+2))();p=C.cast(C.byref(b,4),C.POINTER(C.c_uint32))
  images=[]
  for name in [b'LOMO',b'Portra 400',b'12345678901234567890123',b'!@#$%^&*()_+-=[]{}:;,.?']:
   b[0]=b[-1]=0x12345678
   self.assertEqual(draw(p,name,1,1),0)
   self.assertEqual((b[0],b[-1]),(0x12345678,0x12345678));images.append(bytes(b))
  self.assertNotEqual(images[0],images[1])
  self.draw(p,33,1,1);self.assertNotEqual(images[0],bytes(b))
  before=bytes(b)
  for name in [None,b'',b'A'*24]:
   self.assertEqual(draw(p,name,1,1),-1);self.assertEqual(bytes(b),before)
