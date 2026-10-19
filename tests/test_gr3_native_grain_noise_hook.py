"""Native RNG-hook ABI and checked stock saved-frame ownership; no ISP pixels."""
import struct,tempfile,unittest
from unicorn import UC_HOOK_CODE
from unicorn import arm_const as A
from tests.test_gr3_isp_base import StockISP,ROOT,BASE
from scripts.build_gr3_native_grain_noise_hook import build,SITE,HELPER
class NoiseHookTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
  cls.helper=0x541b0000;cls.expected=0x54190010
  with tempfile.TemporaryDirectory() as d:cls.code,cls.report=build(d,0x541a0000,{HELPER:cls.helper},cls.expected,cls.rom)
 def fixture(self,patched=True):
  rom=bytearray(self.rom)
  if patched:
   for p in self.report['patches']:rom[p['address']-BASE:p['address']-BASE+4]=bytes.fromhex(p['replacement_hex'])
  e=StockISP(bytes(rom));e.u.mem_map(0x541a0000,0x20000);e.u.mem_write(0x541a0000,self.code)
  self.gran=0x5effd000;self.dispatch=self.gran+0x60;self.owner=0x60040000;self.noise=0x60041000
  for off,val in ((-4,0x53681050),(-12,self.dispatch),(-0x64c,31),(-0x644,2),(-0x650,32)):e.w32(self.gran+off,val)
  e.w32(self.dispatch-4,self.expected);e.w32(self.dispatch-40,self.owner)
  u=e.u
  for n in range(13):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),0x12340000+n)
  u.reg_write(A.UC_ARM_REG_FP,self.gran);u.reg_write(A.UC_ARM_REG_R0,self.noise);u.reg_write(A.UC_ARM_REG_R1,64)
  u.reg_write(A.UC_ARM_REG_SP,self.gran-0x674);u.reg_write(A.UC_ARM_REG_LR,0x5e000000);u.reg_write(A.UC_ARM_REG_CPSR,0xa0000013)
  for n in range(32):u.reg_write(getattr(A,'UC_ARM_REG_D'+str(n)),0x1122334455000000+n)
  u.reg_write(A.UC_ARM_REG_FPSCR,0x01000000)
  self.calls=[]
  def boundary(uc,pc,size,data):
   if pc==0x5368a92c:
    args=tuple(uc.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(2));self.calls.append(('rng',args))
    uc.mem_write(args[0],bytes(range(args[1])))
    for n in (0,1,2,3,12):uc.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),0xaabb0000+n)
    for n in range(32):uc.reg_write(getattr(A,'UC_ARM_REG_D'+str(n)),0x9988776655440000+n)
    uc.reg_write(A.UC_ARM_REG_FPSCR,0x02000000);uc.reg_write(A.UC_ARM_REG_CPSR,0x60000013)
    uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
   elif pc==self.helper:
    args=[uc.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(4)]
    args+=list(struct.unpack('<2I',uc.mem_read(uc.reg_read(A.UC_ARM_REG_SP),8)))
    self.calls.append(('helper',tuple(args)))
    for n in range(13):uc.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),0x77770000+n)
    for n in range(32):uc.reg_write(getattr(A,'UC_ARM_REG_D'+str(n)),0xdeadbeef00000000+n)
    uc.reg_write(A.UC_ARM_REG_FPSCR,0);uc.reg_write(A.UC_ARM_REG_CPSR,0x90000013)
    uc.reg_write(A.UC_ARM_REG_R0,1);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
  e.u.hook_add(UC_HOOK_CODE,boundary);return e
 def run_hook(self,e):
  e.u.emu_start(SITE,SITE+4,count=2000);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_PC),SITE+4)
 def snapshot(self,e):
  u=e.u
  return ([u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(13)],u.reg_read(A.UC_ARM_REG_SP),u.reg_read(A.UC_ARM_REG_LR),u.reg_read(A.UC_ARM_REG_CPSR),u.reg_read(A.UC_ARM_REG_FPSCR),[u.reg_read(getattr(A,'UC_ARM_REG_D'+str(n))) for n in range(32)])
 def test_original_rng_first_and_all_postcall_cpu_state_preserved(self):
  original=self.fixture(False);self.run_hook(original);expected=self.snapshot(original)
  e=self.fixture();self.run_hook(e)
  self.assertEqual(self.snapshot(e),expected)
  self.assertEqual(self.calls,[('rng',(self.noise,64)),('helper',(self.owner,self.noise,64,31,2,32))])
  self.assertEqual(bytes(e.u.mem_read(self.noise,64)),bytes(range(64)))
 def test_actual_original_dispatcher_and_granulation_frames_reach_checked_owner(self):
  e=self.fixture();params=e.alloc(64);settings=e.alloc(16);dst=e.alloc(32);src=e.alloc(32)
  for off,val in ((4,dst),(8,src),(0x10,settings),(0x2c,self.noise),(0x30,64)):e.w32(params+off,val)
  e.u.mem_write(settings,struct.pack('<hhhhf',0,0,1,0,1.0))
  for desc in (dst,src):e.u.mem_write(desc+0x10,struct.pack('<HH',31,2))
  u=e.u;u.reg_write(A.UC_ARM_REG_R0,0x60042000);u.reg_write(A.UC_ARM_REG_R1,params);u.reg_write(A.UC_ARM_REG_R2,0)
  u.reg_write(A.UC_ARM_REG_R4,self.owner);u.reg_write(A.UC_ARM_REG_SP,0x5efff000);u.reg_write(A.UC_ARM_REG_LR,self.expected)
  frames=[]
  def stages(uc,pc,size,data):
   if pc in (0x5367b540,0x5367c158,0x53680088):
    uc.reg_write(A.UC_ARM_REG_R0,1);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
   elif pc==SITE:
    fp=uc.reg_read(A.UC_ARM_REG_FP);dp=struct.unpack('<I',uc.mem_read(fp-12,4))[0]
    frames.append((dp-fp,struct.unpack('<I',uc.mem_read(dp-40,4))[0]))
  u.hook_add(UC_HOOK_CODE,stages);u.emu_start(0x53680dbc,SITE+4,count=10000)
  self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),SITE+4)
  self.assertEqual(frames,[(0x60,self.owner)])
  self.assertEqual(self.calls,[('rng',(self.noise,64)),('helper',(self.owner,self.noise,64,31,2,32))])
 def test_corrupt_or_foreign_frame_chain_never_calls_recipe_helper(self):
  for which,val in [('gran_lr',0x53681054),('frame',0x5effd000),('frame',0x50000000),('frame',0x80000000),('frame',0x5effd063),('frame',0x60040000),('stage_lr',0x53503ab8)]:
   e=self.fixture();at={'gran_lr':self.gran-4,'frame':self.gran-12,'stage_lr':self.dispatch-4}[which];e.w32(at,val)
   self.run_hook(e);self.assertEqual(self.calls,[('rng',(self.noise,64))])
 def test_builder_requires_exact_rom_and_explicit_stage_return(self):
  with tempfile.TemporaryDirectory() as d:
   for ret in (0,0x54190011,0x80000000):
    with self.assertRaises(ValueError):build(d,0x541a0000,{HELPER:self.helper},ret,self.rom)
   bad=bytearray(self.rom);bad[SITE-BASE]^=1
   with self.assertRaises(ValueError):build(d,0x541a0000,{HELPER:self.helper},self.expected,bad)
  self.assertLessEqual(self.report['bytes'],350)
if __name__=='__main__':unittest.main()
