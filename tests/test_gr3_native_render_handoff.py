"""Only stages completed by the upstream owner may leave the CPU plan."""
import ctypes as C,struct,unittest,zlib
from tests import test_gr3_m10v_library as host
class NativeRenderHandoffTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  host.NativeFilmLibraryTests.setUpClass();cls.addClassCleanup(host.NativeFilmLibraryTests.doClassCleanups);cls.lib=host.NativeFilmLibraryTests.lib
 def fixture(self,film=67,grain=2,soft=0,halo=0,leak=0):
  case=host.NativeFilmLibraryTests();state=case.state();ok=host.STORE(lambda _,s:0)
  self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,film,ok,None),0)
  state.slots[0].grain=grain;state.slots[0].soft=soft;state.slots[0].halo_gain=halo;state.effects[0][1]=leak
  state.crc=zlib.crc32(bytes(state)[:-4]);im,y,uv,scratch=case.image()
  return state,im,y,uv,scratch
 def native(self,state,im,scratch,mask):
  fn=getattr(self.lib,'m10v_library_render_native',None)
  self.assertIsNotNone(fn,'missing explicit upstream completion handoff')
  fn.argtypes=[C.POINTER(host.Image),C.POINTER(host.State),C.c_uint32,C.POINTER(host.Date),C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32]
  return fn(C.byref(im),C.byref(state),0,None,42,scratch,len(scratch) if scratch is not None else 0,mask)
 def test_all_completed_leaves_photo_and_source_configuration_unchanged_without_scratch(self):
  for film in (33,35,66,67,68):
   state,im,y,uv,scratch=self.fixture(film,soft=2,halo=4,leak=6);before=(bytes(y),bytes(uv),bytes(state))
   self.assertEqual(self.native(state,im,None,31),0);self.assertEqual((bytes(y),bytes(uv),bytes(state)),before)
 def test_color_completion_preserves_requested_grain_and_leak(self):
  for film in (66,67,68):
   state,im,y,uv,scratch=self.fixture(film,grain=2,leak=6);before=(bytes(y),bytes(uv),bytes(state))
   self.assertEqual(self.native(state,im,scratch,1),0);self.assertNotEqual((bytes(y),bytes(uv)),before[:2]);self.assertEqual(bytes(state),before[2])
 def test_remaining_soft_and_halo_are_not_erased_by_color_and_grain_completion(self):
  for effect,mask in (('soft',1|2|8|16),('halo',1|2|4|16)):
   state,im,y,uv,scratch=self.fixture(67,grain=0,soft=2 if effect=='soft' else 0,halo=4 if effect=='halo' else 0)
   # Give spatial operators a point source and a broad tonal gradient.
   for row in range(im.height):
    for x in range(im.width):y[row*im.stride+x]=(row*3+x*5)&255
   y[20*im.stride+20]=255;y[20*im.stride+21]=255;before=(bytes(y),bytes(uv))
   self.assertEqual(self.native(state,im,scratch,mask),0);self.assertNotEqual((bytes(y),bytes(uv)),before,effect)
 def test_unknown_completion_bits_reject_before_writes(self):
  state,im,y,uv,scratch=self.fixture();before=(bytes(y),bytes(uv))
  self.assertLess(self.native(state,im,scratch,32),0);self.assertEqual((bytes(y),bytes(uv)),before)
 def test_no_completion_preserves_existing_full_renderer(self):
  for film in (33,35,66,67,68):
   state,im,y,uv,scratch=self.fixture(film);other,i2,y2,u2,s2=self.fixture(film)
   self.assertEqual(self.native(state,im,scratch,0),0)
   self.assertEqual(self.lib.m10v_library_render(C.byref(i2),C.byref(other),0,None,42,s2,len(s2)),0)
   self.assertEqual((bytes(y),bytes(uv)),(bytes(y2),bytes(u2)))
