"""Actual native RAW retirement must preserve every current YUV output byte."""
import struct,tempfile,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_READ_UNMAPPED
from unicorn import arm_const as A
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_capture as capture

class CaptureReleasedRawTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  capture.M10VCaptureTests.setUpClass();cls.addClassCleanup(capture.M10VCaptureTests.doClassCleanups)
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  cls.manifest=build(Path(cls.tmp.name),debug_mode=True,lifecycle_trace=True,save_chain_trace=True)
  cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
 def fixture(self,film=67,pool_result=1):
  case=capture.M10VCaptureTests();case.debug_manifest=self.manifest;case.debug_code=self.code
  h,u,context,y,uv,*rest=case.fixture(film=film,raw=1,raw_bank=0xa3000000,debug=True,stamp=2)
  recipe=context-0x9b8;si=0x55078000;backing=0xa2f40390;source=0xa3000000;frees=[];reads=[];watch=[False]
  def word(at,v):u.mem_write(at,struct.pack('<I',v))
  def page(at):
   at&=~4095
   if not any(lo<=at<=hi for lo,hi,_ in u.mem_regions()):u.mem_map(at,4096)
   u.mem_write(at,capture.M10VCaptureTests.official[at-0x53000000:at-0x53000000+4096])
  for at in (0x5350d000,0x53510000,0x53521000,0x536a2000,0x536ab000,0x53d0f000):page(at)
  u.mem_map(source&~4095,4096);u.mem_map(backing&~4095,4096)
  pool=0x550c0000;vt=0x550c0100;member=0x550e0100;free=0x550e0200
  word(pool,vt);word(vt+0x18,member);word(vt+0xc,free)
  def ret(v):u.reg_write(A.UC_ARM_REG_R0,v);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
  def service(uc,at,size,data):
   if at==0x5351091c:self.assertEqual(uc.reg_read(A.UC_ARM_REG_R0),0x50f0);ret(recipe)
   elif at==0x536a2424:ret(0x550c0200)
   elif at==0x536abf18:ret(pool)
   elif at==member:ret(1)
   elif at==free:frees.append(uc.reg_read(A.UC_ARM_REG_R1));ret(pool_result)
   elif at==0x536b9f1c:ret(0)
   elif at==0x5351fd54:uc.emu_stop()
  u.hook_add(UC_HOOK_CODE,service)
  h.call(u,'m10v_save_trace_recipe_alloc',0x4778);word(recipe,0x53d0fc90);word(recipe+0x2f4,backing);word(recipe+0x230,0x55077000);u.mem_write(0x55077000,struct.pack('<HH',6112,4064))
  # Install the checked actual pool observer and virtual setter, not token mocks.
  chain=self.manifest['capture_lifecycle']
  patches=list(chain['patches'])
  def collect(value):
   if isinstance(value,dict):
    if 'address'in value and 'replacement_hex'in value:return [value]
    return [p for v in value.values() for p in collect(v)]
   if isinstance(value,list):return [p for v in value for p in collect(v)]
   return []
  patches+=collect(chain)
  found=set()
  for p in patches:
   if p['address'] in (0x53521e18,0x53d0fd00):u.mem_write(p['address'],bytes.fromhex(p['replacement_hex']));found.add(p['address'])
  self.assertEqual(found,{0x53521e18,0x53d0fd00})
  def memory(uc,access,at,size,value,data):
   if watch[0] and (at<=recipe+0x44d0<at+size or at>=0x7f000000 or 0xa0000000<=at<0xe0000000):reads.append((at,size));self.fail('released RAW or sticky fallback read '+hex(at))
   if access==19:self.fail('unmapped read '+hex(at)+' PC '+hex(uc.reg_read(A.UC_ARM_REG_PC)))
   return False
  u.hook_add(UC_HOOK_MEM_READ,memory,begin=recipe+0x44d0,end=recipe+0x44d3);u.hook_add(UC_HOOK_MEM_READ,memory,begin=0xa0000000,end=0xdfffffff);u.hook_add(UC_HOOK_MEM_READ_UNMAPPED,memory)
  def release():
   u.reg_write(A.UC_ARM_REG_R0,0x550c1000);u.reg_write(A.UC_ARM_REG_R1,recipe);u.reg_write(A.UC_ARM_REG_R2,1);u.reg_write(A.UC_ARM_REG_SP,0x550fe000);u.reg_write(A.UC_ARM_REG_LR,0x5351fd54)
   u.emu_start(self.manifest['symbols']['m10v_save_trace_recipe_release'],0x5351fd54,count=100000)
   self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x5351fd54);self.assertEqual(frees,[backing]);self.assertEqual(u.mem_read(recipe+0x60,4),bytes(4));self.assertEqual(u.mem_read(recipe+0x2f4,4),bytes(4))
  def poison():word(recipe+0x230,0x7f000000);word(recipe+0x44d0,source);watch[0]=True
  return h,u,context,recipe,si,y,uv,release,poison,word,reads
 def output(self,u,y,uv):return bytes(u.mem_read(0x55010000,len(y))),bytes(u.mem_read(0x55020000,len(uv)))
 def test_native_release_matches_every_live_capture_yuv_byte_without_raw_metadata_or_fallback_reads(self):
  for film in (35,66,67,68):
   with self.subTest(film=film):
    h0,u0,c0,r0,si0,y0,uv0,*_=self.fixture(film);self.assertEqual(h0.call(u0,'m10v_capture_library',c0),0);baseline=self.output(u0,y0,uv0)
    h,u,c,r,si,y,uv,release,poison,word,reads=self.fixture(film);release();self.assertEqual(h.call(u,'m10v_save_trace_recipe_raw_status',r,si,0,0),2);poison()
    self.assertEqual(h.call(u,'m10v_capture_library',c),0);self.assertEqual(self.output(u,y,uv),baseline);self.assertNotEqual(baseline,(bytes(y),bytes(uv)));self.assertEqual(reads,[])
 def test_unproved_null_failed_pool_foreign_si_and_new_setter_reject_without_pixel_changes(self):
  for mode in ('no_release','pool_failure','foreign_si','new_setter'):
   with self.subTest(mode=mode):
    h,u,c,r,si,y,uv,release,poison,word,reads=self.fixture(pool_result=0 if mode=='pool_failure' else 1)
    if mode=='no_release':word(r+0x60,0);word(r+0x2f4,0)
    else:release()
    if mode=='foreign_si':
     other=si+0x1000;u.mem_write(other,bytes(u.mem_read(si,0x94c)));word(r+0x44c8,other);word(c+0x34,other)
    elif mode=='new_setter':h.call(u,'m10v_save_trace_recipe_set',r,1,0xa4000000);h.call(u,'m10v_save_trace_recipe_set',r,1,0)
    poison();self.assertEqual(h.call(u,'m10v_capture_library',c),-3);self.assertEqual(self.output(u,y,uv),(bytes(y),bytes(uv)));self.assertEqual(reads,[])
if __name__=='__main__':unittest.main()
