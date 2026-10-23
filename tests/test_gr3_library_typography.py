"""Regressions for the reported clipped captions and corner selection mark.

Real ARM view constructors and real C card pixels are exercised. The firmware
font engine and physical LCD are not simulated; card captions must therefore
be part of the bounded bitmap, independent of firmware text metrics.
"""
import ctypes as C
import hashlib
import os
from pathlib import Path
import struct
import unittest
from tests import test_gr3_settings_view as native_view
from tests import test_gr3_film_card as card_fixture

ROOT=Path(__file__).resolve().parents[1]

class LibraryTypographyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  os.environ.setdefault('M10V_GR3_ORIGINAL_RTOS',str(ROOT/'data/research/gr3/RTOS.bin'))
  native_view.SettingsViewTests.setUpClass()
  card_fixture.FilmCardTests.setUpClass()

 @classmethod
 def tearDownClass(cls):
  card_fixture.FilmCardTests.doClassCleanups()

 def test_two_rows_have_owned_caption_pixels_and_do_not_overlap_footer(self):
  f=native_view.SettingsViewTests();u=f.machine();f.call(u,'create',0x10001000)
  words=struct.unpack('<66I',u.mem_read(0x10001000,264))
  rect=lambda i:struct.unpack('<4I',u.mem_read(words[i]+0x20,16))
  first,second=rect(26),rect(31)
  self.assertGreaterEqual(first[3],148,'120px square art needs its own 28px name strip')
  self.assertLessEqual(first[1]+first[3],second[1])
  self.assertLessEqual(second[1]+second[3]+12,rect(4)[1])
  f.call(u,'destroy',0x10001000)
  self.assertFalse(f.live)

 def test_enabled_marker_is_a_solid_top_right_triangle(self):
  draw=card_fixture.FilmCardTests.draw
  off=(C.c_uint32*(120*148))();on=(C.c_uint32*(120*148))()
  self.assertEqual(draw(off,69,4,0),0);self.assertEqual(draw(on,69,4,1),0)
  changed={(i%120,i//120) for i in range(120*148) if off[i]!=on[i]}
  self.assertTrue(changed)
  self.assertTrue(all(102<=x<118 and 2<=y<18 and x-102>=y-2 for x,y in changed),
                  'enabled mark must have a diagonal edge, without a square or check')
  for y in range(2,18):
   for x in range(102+y-2,118):self.assertEqual(on[y*120+x],0xff45dce9)

 def test_every_builtin_caption_is_visible_and_buffer_is_bounded(self):
  draw=card_fixture.FilmCardTests.draw
  count=120*148
  for film in [*range(1,79),*range(289,298)]:
   with self.subTest(film=film):
    b=(C.c_uint32*(count+2))();b[0]=b[-1]=0x12345678
    p=C.cast(C.byref(b,4),C.POINTER(C.c_uint32))
    self.assertEqual(draw(p,film,9,1),0)
    self.assertEqual((b[0],b[-1]),(0x12345678,0x12345678))
    self.assertGreater(len(set(p[120*120:count])),1,'name strip must contain actual glyph pixels')

 def test_catalog_error_uses_header_and_redraw_reuses_owned_caption_buffers(self):
  f=native_view.SettingsViewTests();u=f.machine(catalog_ids={i:69+i for i in range(10)})
  f.call(u,'create',0x10001000)
  state=bytearray(212)
  for i in range(10):struct.pack_into('<H',state,12+8*i,69+i)
  struct.pack_into('<7I',state,184,2,0,0,4,0,0,0)
  u.mem_write(0x10002000,bytes(state));u.mem_write(0x10003000,struct.pack('<7I',0,0,0x540b0010,0,0,0,0))
  f.call(u,'draw',0x10001000,0x10002000,0x10003000)
  words=struct.unpack('<56I',u.mem_read(0x10001000,224));heap=words[55]
  self.assertEqual(f.live[heap],710580)
  for i in range(10):
   width,height,address=struct.unpack('<HHI',u.mem_read(heap+710400+i*8,8))
   self.assertEqual((width,height),(120,148))
   self.assertGreater(len(set(u.mem_read(address*4+120*120*4,120*28*4))),1)
  allocated=dict(f.live)
  u.mem_write(0x10002000+208,struct.pack('<I',4))
  f.call(u,'draw',0x10001000,0x10002000,0x10003000)
  self.assertEqual(f.live,allocated)
  self.assertEqual(struct.unpack('<H',u.mem_read(words[2]+0xea,2))[0],1127)
  self.assertEqual(u.mem_read(words[5]+0x9e,1),b'\0')
  f.call(u,'destroy',0x10001000);self.assertFalse(f.live)

 def test_long_custom_names_fit_inside_the_same_caption_strip(self):
  draw=card_fixture.FilmCardTests.lib.m10v_film_card_custom
  draw.argtypes=[C.POINTER(C.c_uint32),C.c_char_p,C.c_uint32,C.c_uint32]
  count=120*148
  for name in [b'LOMO',b'Portra 400',b'ABCDEFGHIJKLMNOPQRSTUVW',b'!@#$%^&*()_+-=[]{}:;,.?']:
   b=(C.c_uint32*(count+2))();b[0]=b[-1]=0x12345678
   p=C.cast(C.byref(b,4),C.POINTER(C.c_uint32))
   self.assertEqual(draw(p,name,9,1),0)
   self.assertEqual((b[0],b[-1]),(0x12345678,0x12345678))
   self.assertGreater(len(set(p[120*120:count])),1)

 def test_lossless_glyph_storage_preserves_all_original_square_artwork_pixels(self):
  digest=hashlib.sha256()
  for film in [*range(1,79),*range(289,298)]:
   pixels=(C.c_uint32*(120*148))()
   self.assertEqual(card_fixture.FilmCardTests.draw(pixels,film,0,0),0)
   digest.update(bytes(pixels)[:120*120*4])
  # Independently measured from deployed 197a6f1 before this repair.
  self.assertEqual(digest.hexdigest(),'f5f9b281122cdf8974fcc97341358c79034fc13a5595aa2a49ac5dbf7cb6def0')

 def test_card_heap_failure_keeps_original_icons_and_cleans_up(self):
  f=native_view.SettingsViewTests();u=f.machine(fail_cards=True)
  f.call(u,'create',0x10001000)
  state=bytearray(212)
  for i in range(10):struct.pack_into('<H',state,12+8*i,33+i)
  struct.pack_into('<7I',state,184,1,0,0,0,0,0,0)
  u.mem_write(0x10002000,bytes(state));f.call(u,'draw',0x10001000,0x10002000,0)
  words=struct.unpack('<56I',u.mem_read(0x10001000,224))
  self.assertEqual(words[55],0)
  self.assertEqual([struct.unpack('<H',u.mem_read(words[26+i]+0xea,2))[0] for i in range(10)],list(range(703,713)))
  f.call(u,'destroy',0x10001000);self.assertFalse(f.live)

if __name__=='__main__':unittest.main()
