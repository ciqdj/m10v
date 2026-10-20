"""Real Live Make + original packer. No ISP pixels or real LCD is emulated."""
import json,struct,tempfile,unittest,zlib
from unicorn import UC_HOOK_CODE
from pathlib import Path
from unicorn import arm_const as A
from scripts.build_gr3_m10v_library import build
from scripts.build_gr3_menu_patches import branch
from tests.test_gr3_isp_base import StockISP,BASE,ROOT
from tests.test_gr3_isp_recipe_color import state
from tests import test_gr3_m10v_capture as capture
class LiveColorPreviewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  cls.manifest=build(cls.tmp.name,debug_mode=True,sd_library=True,lifecycle_trace=True,save_chain_trace=True,recipe_snapshot=True,native_color=True,native_grain=True,view_deferred=True,live_color=True)
  cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes();cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
  candidate=bytearray(cls.rom);at=cls.manifest['base']-BASE;candidate.extend(bytes(max(0,at+len(cls.code)-len(candidate))));candidate[at:at+len(cls.code)]=cls.code
  for p in cls.manifest['isp_base']['patches']:struct.pack_into('<I',candidate,p['address']-BASE,branch(p['address'],p['entry']))
  cls.candidate=bytes(candidate);cls.snapshot=cls.manifest['capture_lifecycle']['snapshot'];cls.entry=cls.snapshot['patches'][3]['entry']
 def cache(self,e,film,ready=True,version=2):
  e.w32(0x55063910,1);e.w32(0x55063988,0x550d0000)
  e.w32(0x550d193c,0x3856504d if ready else 0);e.w32(0x550d1940,version);e.u.mem_write(0x550d1944,state((film,)*5))
 def fixture(self,film=35):
  e=StockISP(self.candidate);self.cache(e,film)
  e.make(12,1,True,actual_live=True);return e,0x60000000,0x60001400
 def test_installed_wrapper_matches_native_target_and_never_accumulates(self):
  for film in (33,35,58,66,67,68):
   e,obj,f=self.fixture(film);base=bytes(e.u.mem_read(f,0x9000));s=e.alloc(1600);gamma=struct.unpack('<I',e.u.mem_read(obj+0x17c,4))[0]
   e.call(self.snapshot['exports']['m10v_isp_native_look_prepare'],s,film,0,8)
   e.call(self.snapshot['exports']['m10v_isp_native_look_apply'],s,gamma,f,0);expected=bytes(e.u.mem_read(f,0x9000))
   e.u.mem_write(f,base)
   for repeat in range(3):
    e.call(self.entry,obj,f);self.assertEqual(bytes(e.u.mem_read(f,0x9000)),expected,(film,repeat))
   self.assertFalse(e.assertions)
 def test_phoenix_ei120_reaches_installed_live_native_profile(self):
  e,obj,f=self.fixture(67);data=bytearray(state((67,)*5));data[61]=1
  struct.pack_into('<I',data,100,zlib.crc32(data[:100]));e.u.mem_write(0x550d1944,bytes(data))
  observed=[];prepare=self.snapshot['exports']['m10v_isp_native_look_prepare']
  e.u.hook_add(UC_HOOK_CODE,lambda u,a,n,d:observed.append((u.reg_read(A.UC_ARM_REG_R1),u.reg_read(A.UC_ARM_REG_R2))) if a==prepare else None)
  e.call(self.entry,obj,f)
  self.assertEqual(observed,[(67,1)])
 def test_empty_busy_or_destroyed_cache_keeps_stock_liveview(self):
  for ready,version in ((False,2),(True,1),(True,0)):
   e,obj,f=self.fixture();before=bytes(e.u.mem_read(f,0x9000));self.cache(e,35,ready,version)
   e.call(self.entry,obj,f);self.assertEqual(bytes(e.u.mem_read(f,0x9000)),before)
 def test_cache_switch_updates_color_without_touching_shooting_info(self):
  e,obj,f=self.fixture(35);e.call(self.entry,obj,f);a=bytes(e.u.mem_read(f,0x9000));si=struct.unpack('<I',e.u.mem_read(f+0x82d0,4))[0];before=bytes(e.u.mem_read(si,0x80000))
  self.cache(e,66,version=4);e.call(self.entry,obj,f);self.assertNotEqual(bytes(e.u.mem_read(f,0x9000)),a);self.assertEqual(bytes(e.u.mem_read(si,0x80000)),before)
 def test_owned_cache_initialization_publication_and_clear_need_no_preview_io(self):
  capture.M10VCaptureTests.setUpClass();self.addCleanup(capture.M10VCaptureTests.doClassCleanups)
  c=capture.M10VCaptureTests();c.manifest=self.manifest;c.code=self.code
  h,u,*_=c.fixture(film=35,raw=1,stamp=0);owner=0x550d0000
  h.file_calls.clear();h.call(u,'m10v_camera_library_preview_init',owner);self.assertEqual(h.file_calls,[]);u.mem_write(0x55063910,struct.pack('<I',1));u.mem_write(0x55063988,struct.pack('<I',owner));h.file_calls.clear()
  self.assertEqual(h.call(u,'m10v_camera_library_preview',0x55002000),0)
  self.assertGreaterEqual(h.call(u,'m10v_camera_library_load',0x55001000),0);h.file_calls.clear()
  self.assertEqual(h.call(u,'m10v_camera_library_preview',0x55002000),1);self.assertEqual(h.file_calls,[])
  self.assertEqual(struct.unpack('<H',u.mem_read(0x55002000+20,2))[0],35)
  self.assertEqual(h.call(u,'m10v_camera_library_select',0x55001000,1,66),0);h.file_calls.clear()
  self.assertEqual(h.call(u,'m10v_camera_library_preview',0x55002000),1);self.assertEqual(h.file_calls,[])
  self.assertEqual(struct.unpack('<H',u.mem_read(0x55002000+20,2))[0],66)
  h.store_result=-1;self.assertEqual(h.call(u,'m10v_camera_library_select',0x55001000,1,68),-2)
  self.assertEqual(h.call(u,'m10v_camera_library_preview',0x55002000),1);self.assertEqual(struct.unpack('<H',u.mem_read(0x55002000+20,2))[0],66)
  h.call(u,'m10v_camera_library_preview_clear',owner);self.assertEqual(h.call(u,'m10v_camera_library_preview',0x55002000),0)

 def test_wrapper_preserves_original_outputs_and_fp_environment(self):
  results=[]
  for wrapped in (False,True):
   e,obj,f=self.fixture(66)
   e.call(self.snapshot['exports']['m10v_isp_frame_live_prepare'],obj,f)
   for i in range(32):e.u.reg_write(getattr(A,'UC_ARM_REG_D'+str(i)),0x1234567800000000+i)
   e.u.reg_write(A.UC_ARM_REG_FPSCR,0x01000000)
   e.call(self.entry if wrapped else 0x536ddecc,obj,f)
   regs=[e.u.reg_read(getattr(A,'UC_ARM_REG_R'+str(i)))for i in range(13)]
   results.append((regs,e.u.reg_read(A.UC_ARM_REG_SP),e.u.reg_read(A.UC_ARM_REG_CPSR)&0xf0000000,[e.u.reg_read(getattr(A,'UC_ARM_REG_D'+str(i)))for i in range(32)],e.u.reg_read(A.UC_ARM_REG_FPSCR)))
  self.assertEqual(*results)
 def test_noncarrier_liveview_is_unchanged(self):
  for tone in (11,13,17,22):
   e=StockISP(self.candidate);self.cache(e,66);base,_,_=e.make(tone,1,True,actual_live=True)
   e.call(self.entry,0x60000000,0x60001400)
   self.assertEqual(bytes(e.u.mem_read(0x60001400,0x9000)),base,tone)

 def test_producer_freezes_validated_preview_without_per_shot_storage_reads(self):
  capture.M10VCaptureTests.setUpClass();self.addCleanup(capture.M10VCaptureTests.doClassCleanups)
  c=capture.M10VCaptureTests();c.manifest=self.manifest;c.code=self.code
  h,u,context,*_=c.fixture(film=66,raw=1,stamp=0)
  u.mem_map(0x55345000,4096) # Uninitialized committed-tone backend guard.
  owner=0x550d0000;recipe=context-0x9b8
  h.call(u,'m10v_camera_library_preview_init',owner)
  u.mem_write(0x55063910,struct.pack('<I',1));u.mem_write(0x55063988,struct.pack('<I',owner))
  h.call(u,'m10v_camera_library_load',0x55001000)
  u.mem_write(recipe,struct.pack('<I',0x53d0fc90));u.mem_write(recipe+0x4778,struct.pack('<I',0x31545653))
  h.manifest={**h.manifest,'symbols':{**h.manifest['symbols'],**self.snapshot['exports']}}
  h.file_calls.clear()
  self.assertEqual(h.call(u,'m10v_isp_frame_recipe_producer',recipe),1)
  self.assertEqual(h.file_calls,[])
  self.assertEqual(h.call(u,'m10v_isp_frame_recipe_state',recipe,0x55002000),1)
  self.assertEqual(struct.unpack('<H',u.mem_read(0x55002000+20,2))[0],66)
