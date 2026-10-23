"""Capture CPU work is conditional on verified upstream completion, never film name alone."""
import struct,tempfile,unittest,zlib,os,json,subprocess,hashlib
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn import arm_const as A
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_capture as prior
class NativeFastCaptureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  prior.M10VCaptureTests.setUpClass();cls.addClassCleanup(prior.M10VCaptureTests.doClassCleanups)
  candidate=os.environ.get('M10V_PLAYBACK_CANDIDATE')
  if candidate:
   folder=Path(candidate);cls.manifest=json.loads((folder/'gr3/manifest.json').read_text())
   binary=folder/'gr3/fwdc239b.bin';receipt=json.loads((folder/'gr3/receipt.json').read_text())
   assert hashlib.sha256(binary.read_bytes()).hexdigest()==receipt['candidate_sha256']
   js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
   rtos=subprocess.check_output(['node','--input-type=module','-e',js,str(binary)],cwd=Path(__file__).resolve().parents[1])
   at=cls.manifest['base']-0x53000000;cls.code=rtos[at:at+cls.manifest['code_bytes']]
   assert hashlib.sha256(cls.code).hexdigest()==cls.manifest['code_sha256']
  else:
   cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
   cls.manifest=build(cls.tmp.name,debug_mode=True,lifecycle_trace=True,save_chain_trace=True,recipe_snapshot=True,native_color=True,native_grain=True)
   cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
 def fixture(self,film,mask=3,halo=0,leak=0,stamp=0):
  case=prior.M10VCaptureTests();case.manifest=self.manifest;case.code=self.code
  h,u,c,y,uv,cache,frees,*_=case.fixture(film=film,raw=1,stamp=stamp,tone=(self.manifest.get('appended_slots') or {}).get('tones',[12,18,19,20,21])[1])
  # Delivered exports include NEON renderers. Model the Cortex-A9 boot FP
  # enable, as StockISP does; a reset Unicorn CPU traps at the first VPUSH.
  u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
  # Real native completion identity is independently tested in native_recipe_handoff.
  # Substitute only that upstream boundary here to isolate downstream pixel ownership.
  complete=self.manifest['capture_lifecycle']['snapshot']['exports']['m10v_isp_frame_recipe_completed']
  def upstream(uc,at,size,data):
   if at==complete:uc.reg_write(A.UC_ARM_REG_R0,mask);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,upstream)
  h.call(u,'m10v_camera_library_halation',0x55001000,1,halo,3,5,2)
  if leak:
   # Old checksummed journals remain readable, but do not schedule CPU texture.
   for filename,data in list(h.files.items()):
    if len(data)==104:
     legacy=bytearray(data);legacy[65]=leak;struct.pack_into('<I',legacy,100,zlib.crc32(legacy[:100]));h.files[filename]=bytes(legacy)
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
 def test_style_filters_keep_cpu_lut_even_with_a_native_completion_mask(self):
  for film,mask in ((291,3),(296,3),(297,0)):
   h,u,c,y,uv,cache,frees,reads,writes=self.fixture(film,mask=mask)
   self.assertEqual(h.call(u,'m10v_capture_library',c),0)
   self.assertGreater(writes[0],0)
   self.assertNotEqual((bytes(u.mem_read(0x55010000,len(y))),bytes(u.mem_read(0x55020000,len(uv)))),(bytes(y),bytes(uv)))
 def test_imported_leak_does_not_touch_native_completed_planes(self):
  h,u,c,y,uv,cache,frees,reads,writes=self.fixture(66,leak=8)
  self.assertEqual(h.call(u,'m10v_capture_library',c),0)
  self.assertEqual((h.allocations,cache,frees,reads,writes),([],[],[],[0],[0]))

 def test_cpu_color_fallback_also_reaches_both_independent_playback_thumbnails(self):
  for fmt in (1,2):
   h,u,c,y,uv,*_=self.fixture(35,mask=0);recipe=c-0x9b8
   h.call(u,'m10v_camera_library_texture',0x55001000,1,0,0)
   def stripe_allocator(uc,at,size,data):
    if at==0x536af2a8 and uc.reg_read(A.UC_ARM_REG_R0)==0x550b0000 and h.allocations[-1]==144:
     # The OS allocator returns a distinct live allocation for the 2-row stripe.
     uc.reg_write(A.UC_ARM_REG_R0,0x55080000)
   u.hook_add(UC_HOOK_CODE,stripe_allocator)
   for index in range(2):
    desc=recipe+0xd0+index*0x20;yp=0x55030000+index*0x20000;cp=yp+0x10000
    u.mem_write(c+0x40+index*4,struct.pack('<I',desc))
    u.mem_write(desc,struct.pack('<4I8H',fmt,yp,cp,0,64,48,72,48,0,0,2,0))
    u.mem_write(yp,bytes([64])*72*48+bytes([197])*32)
    u.mem_write(cp,bytes([128])*(72*48//fmt)+bytes([198])*32)
   self.assertEqual(h.call(u,'m10v_capture_library',c),0)
   expected_y=bytes(u.mem_read(0x55010000,2));expected_uv=bytes(u.mem_read(0x55020000,2))
   self.assertNotEqual(expected_y+expected_uv,bytes([64,64,128,128]))
   for index in range(2):
    yp=0x55030000+index*0x20000;cp=yp+0x10000
    self.assertEqual(bytes(u.mem_read(yp,2)),expected_y,(fmt,index))
    self.assertEqual(bytes(u.mem_read(cp,2)),expected_uv,(fmt,index))
    for row in range(48):self.assertEqual(bytes(u.mem_read(yp+row*72+64,8)),bytes([64])*8)
    for row in range(48//fmt):self.assertEqual(bytes(u.mem_read(cp+row*72+64,8)),bytes([128])*8)
    self.assertEqual(bytes(u.mem_read(yp+72*48,32)),bytes([197])*32)
    self.assertEqual(bytes(u.mem_read(cp+72*48//fmt,32)),bytes([198])*32)

 def test_thumbnail_raw_metadata_partial_alias_and_invalid_format_fail_closed(self):
  for bad in ('raw','recipe','shooting','partial_alias','odd_420','bad_stride'):
   h,u,c,y,uv,cache,*_=self.fixture(35,mask=0);recipe=c-0x9b8
   h.call(u,'m10v_camera_library_texture',0x55001000,1,0,0)
   yp,cp=0x55030000,0x55040000
   if bad=='raw':yp=0x60000000
   elif bad=='recipe':yp=recipe+0x2000
   elif bad=='shooting':yp=0x55078000
   elif bad=='partial_alias':yp=0x55010004
   fmt=2 if bad=='odd_420' else 1;height=47 if bad=='odd_420' else 48;stride=60 if bad=='bad_stride' else 72
   u.mem_write(c+0x40,struct.pack('<I',recipe+0xd0))
   u.mem_write(c+0x44,struct.pack('<I',recipe+0xf0))
   u.mem_write(recipe+0xd0,struct.pack('<4I8H',fmt,yp,cp,0,64,height,stride,48,0,0,2,0))
   u.mem_write(cp,bytes([128])*72*48);cache.clear()
   self.assertEqual(h.call(u,'m10v_capture_library',c),0,bad)
   self.assertEqual(bytes(u.mem_read(cp,72*48)),bytes([128])*72*48,bad)
   self.assertFalse(any(p in (yp,cp) for p,n in cache if p not in (0x55010000,0x55020000)),bad)

 def test_identical_thumbnail_alias_is_colored_once_and_main_alias_is_skipped(self):
  for alias in ('main','secondary'):
   h,u,c,y,uv,cache,*_=self.fixture(35,mask=0);recipe=c-0x9b8
   h.call(u,'m10v_camera_library_texture',0x55001000,1,0,0)
   for index in range(2):
    desc=recipe+0xd0+index*0x20;u.mem_write(c+0x40+index*4,struct.pack('<I',desc))
    if alias=='main':u.mem_write(desc,bytes(u.mem_read(recipe+0xb0,32)))
    else:
     u.mem_write(desc,struct.pack('<4I8H',1,0x55030000,0x55040000,0,64,48,72,48,0,0,2,0))
   u.mem_write(0x55030000,bytes([64])*72*48);u.mem_write(0x55040000,bytes([128])*72*48);cache.clear()
   self.assertEqual(h.call(u,'m10v_capture_library',c),0)
   if alias=='main':self.assertEqual(len(cache),4)
   else:
    self.assertEqual(bytes(u.mem_read(0x55030000,2)),bytes(u.mem_read(0x55010000,2)))
    self.assertEqual(bytes(u.mem_read(0x55040000,2)),bytes(u.mem_read(0x55020000,2)))
    self.assertEqual(sum(p==0x55030000 for p,n in cache),2)

 def test_thumbnail_cannot_overwrite_extended_raw_lifetime_metadata(self):
  h,u,c,y,uv,cache,*_=self.fixture(35,mask=0);recipe=c-0x9b8;yp=recipe+0x50c0;cp=0x55040000
  u.mem_write(c+0x40,struct.pack('<I',recipe+0xd0));u.mem_write(c+0x44,struct.pack('<I',recipe+0xf0))
  u.mem_write(recipe+0xd0,struct.pack('<4I8H',1,yp,cp,0,2,2,4,2,0,0,2,0))
  u.mem_write(yp,bytes([64])*8);u.mem_write(cp,bytes([128])*8)
  self.assertEqual(h.call(u,'m10v_capture_library',c),0)
  self.assertEqual(bytes(u.mem_read(yp,8)),bytes([64])*8)

 def test_temporary_420_stripe_cannot_alias_original_preview_planes(self):
  for pointer in (0x55090000,0x550a0000):
   h,u,c,y,uv,cache,*_=self.fixture(35,mask=0);recipe=c-0x9b8
   u.mem_write(c+0x40,struct.pack('<I',recipe+0xd0));u.mem_write(c+0x44,struct.pack('<I',recipe+0xf0))
   u.mem_write(recipe+0xd0,struct.pack('<4I8H',2,0x55030000,0x55040000,0,64,48,72,48,0,0,2,0))
   u.mem_write(0x55030000,bytes([64])*72*48);u.mem_write(0x55040000,bytes([128])*72*24)
   u.mem_write(pointer,bytes([199])*144)
   def alias_allocator(uc,at,size,data):
    if at==0x536af2a8 and h.allocations[-1]==144:uc.reg_write(A.UC_ARM_REG_R0,pointer)
   u.hook_add(UC_HOOK_CODE,alias_allocator)
   self.assertEqual(h.call(u,'m10v_capture_library',c),0)
   self.assertEqual(bytes(u.mem_read(pointer,144)),bytes([199])*144)

 def test_full_resolution_native_only_does_not_even_require_cpu_mapped_planes(self):
  h,u,c,y,uv,cache,frees,reads,writes=self.fixture(67)
  recipe=c-0x9b8
  u.mem_write(recipe+0xb0,struct.pack('<4I8H',1,0x64000000,0x66000000,0,6000,4000,6000,4000,0,0,2,0))
  self.assertEqual(h.call(u,'m10v_capture_library',c),0)
  self.assertEqual((h.allocations,cache,frees),([],[],[]))
