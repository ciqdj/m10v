"""Capture CPU work is conditional on verified upstream completion, never film name alone."""
import struct,tempfile,unittest,zlib
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn import arm_const as A
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_capture as prior
class NativeFastCaptureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  prior.M10VCaptureTests.setUpClass();cls.addClassCleanup(prior.M10VCaptureTests.doClassCleanups)
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  cls.manifest=build(cls.tmp.name,debug_mode=True,lifecycle_trace=True,save_chain_trace=True,recipe_snapshot=True,native_color=True,native_grain=True)
  cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
 def fixture(self,film,mask=3,halo=0,leak=0,stamp=0):
  case=prior.M10VCaptureTests();case.manifest=self.manifest;case.code=self.code
  h,u,c,y,uv,cache,frees,*_=case.fixture(film=film,raw=1,stamp=stamp)
  # Real native completion identity is independently tested in native_recipe_handoff.
  # Substitute only that upstream boundary here to isolate downstream pixel ownership.
  complete=self.manifest['capture_lifecycle']['snapshot']['exports']['m10v_isp_frame_recipe_completed']
  def upstream(uc,at,size,data):
   if at==complete:uc.reg_write(A.UC_ARM_REG_R0,mask);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,upstream)
  h.call(u,'m10v_camera_library_halation',0x55001000,1,halo,3,5,2)
  h.call(u,'m10v_camera_library_effects',0x55001000,1,1,leak)
  h.allocations.clear();cache.clear();frees.clear();reads=[0];writes=[0]
  def access(uc,access,at,size,value,data):
   (writes if access==17 else reads)[0]+=1
  for addr in (0x55010000,0x55020000):u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,access,begin=addr,end=addr+136*96-1)
  return h,u,c,y,uv,cache,frees,reads,writes
 def test_native_only_does_not_touch_planes_allocate_or_flush_for_all_native_films(self):
  for film in range(33,79):
   with self.subTest(film=film):
    h,u,c,y,uv,cache,frees,reads,writes=self.fixture(film)
    self.assertEqual(h.call(u,'m10v_capture_library',c),0)
    self.assertEqual((h.allocations,cache,frees,reads,writes),([],[],[],[0],[0]))
    self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(y));self.assertEqual(bytes(u.mem_read(0x55020000,len(uv))),bytes(uv))
 def test_halo_keeps_required_scratch_but_never_allocates_cpu_color_cache(self):
  for film in (33,67):
   h,u,c,*rest=self.fixture(film,halo=3)
   self.assertEqual(h.call(u,'m10v_capture_library',c),0)
   self.assertEqual(h.allocations,[6*128*96]);self.assertEqual(rest[3],[0x550b0000])
 def test_no_native_completion_keeps_fallback_and_requested_effects(self):
  for film in (33,35,66,67,68):
   h,u,c,y,uv,cache,frees,reads,writes=self.fixture(film,mask=0)
   self.assertEqual(h.call(u,'m10v_capture_library',c),0)
   self.assertTrue(cache);self.assertGreater(writes[0],0)
 def test_leak_remains_active_with_native_color_and_grain(self):
  h,u,c,y,uv,cache,frees,reads,writes=self.fixture(66,leak=8)
  self.assertEqual(h.call(u,'m10v_capture_library',c),0)
  self.assertEqual(h.allocations,[]);self.assertTrue(cache);self.assertGreater(writes[0],0)

 def test_full_resolution_native_only_does_not_even_require_cpu_mapped_planes(self):
  h,u,c,y,uv,cache,frees,reads,writes=self.fixture(67)
  recipe=c-0x9b8
  u.mem_write(recipe+0xb0,struct.pack('<4I8H',1,0x64000000,0x66000000,0,6000,4000,6000,4000,0,0,2,0))
  self.assertEqual(h.call(u,'m10v_capture_library',c),0)
  self.assertEqual((h.allocations,cache,frees),([],[],[]))
