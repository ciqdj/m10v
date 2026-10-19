"""CCD native defaults, artifact-free fast path and colour-fit quality bounds."""
import ctypes as C
import json
import unittest
from tests import test_gr3_m10v_library as host

class CcdFilmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  host.NativeFilmLibraryTests.setUpClass()
  cls.addClassCleanup(host.NativeFilmLibraryTests.doClassCleanups)
  cls.lib=host.NativeFilmLibraryTests.lib
 def test_ccd_defaults_and_both_resets_preserve_clean_digital_texture(self):
  lib=self.lib;s=host.State();lib.m10v_library_init(C.byref(s));ok=host.STORE(lambda _,v:0)
  self.assertEqual(lib.m10v_library_select(C.byref(s),0,72,ok,None),0)
  expected=bytes(s.slots[0]);effects=bytes(s.effects[0])
  self.assertEqual([s.slots[0].grain,s.slots[0].soft,s.slots[0].halo_gain],[0,0,0])
  self.assertEqual(effects,bytes([0,0,0,4,0,0,0,0]))
  lib.m10v_library_reset.argtypes=[C.POINTER(host.State),C.c_uint32,host.STORE,C.c_void_p]
  lib.m10v_library_effects.argtypes=[C.POINTER(host.State),C.c_uint32,C.c_uint32,C.c_uint32,host.STORE,C.c_void_p]
  for reset in (False,True):
   self.assertEqual(lib.m10v_library_texture(C.byref(s),0,3,0,ok,None),0)
   if reset:self.assertEqual(lib.m10v_library_reset(C.byref(s),0,ok,None),0)
   else:self.assertEqual(lib.m10v_library_effects(C.byref(s),0,5,0,ok,None),0)
   self.assertEqual(bytes(s.slots[0]),expected);self.assertEqual(bytes(s.effects[0]),effects)
 def test_native_color_completed_leaves_padded_pixels_and_buffers_untouched_without_scratch(self):
  lib=self.lib;s=host.State();lib.m10v_library_init(C.byref(s));ok=host.STORE(lambda _,v:0)
  self.assertEqual(lib.m10v_library_select(C.byref(s),0,72,ok,None),0)
  y=(C.c_uint8*96)(*range(96));uv=(C.c_uint8*96)(*reversed(range(96)))
  image=host.Image(y,uv,96,96,10,8,12);before=(bytes(y),bytes(uv))
  lib.m10v_library_render_native.argtypes=[C.POINTER(host.Image),C.POINTER(host.State),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32]
  self.assertEqual(lib.m10v_library_render_native(C.byref(image),C.byref(s),0,None,42,None,0,1),0)
  self.assertEqual((bytes(y),bytes(uv)),before)
 def test_ccd_interpolation_and_isp_holdout_stay_below_visible_fit_budget(self):
  ref=json.loads((host.ROOT/'native/gr3/curated-reference.json').read_text())
  stock=next(s for s in ref['stocks'] if s['id']==72)
  self.assertLess(stock['interpolation']['delta_e00_p95'],.5)
  score=next(q['holdout'] for q in ref['native_profiles_full'] if q['film_id']==72)
  self.assertLess(score['de00_median'],.5);self.assertLess(score['de00_p95'],1.)
