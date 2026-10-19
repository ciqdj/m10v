"""Original grain settings/dispatch ARM execution; hardware boundaries stubbed."""
import struct,tempfile,unittest
from unicorn import UC_HOOK_CODE
from unicorn import arm_const as A
from tests.test_gr3_isp_base import StockISP,ROOT,BASE
from scripts.build_gr3_native_grain_hooks import build,SITES,HELPERS
from scripts.build_gr3_menu_patches import assembly

class NativeGrainHookTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rom=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes();cls.exports=dict(zip(HELPERS,(0x541b0000,0x541b0200)))
  with tempfile.TemporaryDirectory() as d:cls.code,cls.manifest=build(d,0x541a0000,cls.exports,cls.rom)
 def fixture(self,helper_result=1):
  rom=bytearray(self.rom)
  for p in self.manifest['patches']:rom[p['address']-BASE:p['address']-BASE+4]=bytes.fromhex(p['replacement_hex'])
  e=StockISP(bytes(rom));e.u.mem_map(0x541a0000,0x20000);e.u.mem_write(0x541a0000,self.code)
  # Deliberately hostile helpers clobber every GPR exceptSP/LR and everyDreg.
  # Actual recipe helper policy is verified independently by its owning module.
  for i,key in enumerate(HELPERS):
   text='movw ip,#0;movt ip,#0x63f0;'+('add ip,ip,#16;' if i else '')+'stm ip,{r0-r2};mov r0,#0x55;mov r1,#0x66;'
   text+=''.join('vmov d'+str(n)+',r0,r1;' for n in range(32))
   text+='vmsr fpscr,r0;cmp r0,#0;'+''.join('mov r'+str(n)+',#0x77;' for n in range(1,13))+'mov r0,#'+str(helper_result)+';bx lr;'
   e.u.mem_write(self.exports[key],assembly('.fpu neon\n'+text,self.exports[key]))
  return e
 def init(self,e,args,context=0x60040000):
  u=e.u
  for n in range(13):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),0x12340000+n)
  for n,v in enumerate(args):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),v)
  u.reg_write(A.UC_ARM_REG_R4,context);u.reg_write(A.UC_ARM_REG_R12,context)
  u.reg_write(A.UC_ARM_REG_SP,0x5efff000);u.reg_write(A.UC_ARM_REG_LR,0x5e000000);u.reg_write(A.UC_ARM_REG_CPSR,0xa0000013)
  for n in range(32):u.reg_write(getattr(A,'UC_ARM_REG_D'+str(n)),0x1122334455000000+n)
  u.reg_write(A.UC_ARM_REG_FPSCR,0x01000000)
 def run_at(self,e,site):
  e.u.emu_start(site,site+4,count=5000000);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_PC),site+4)
 def snapshot(self,e):
  u=e.u;return ([u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(4,12)],u.reg_read(A.UC_ARM_REG_SP),[u.reg_read(getattr(A,'UC_ARM_REG_D'+str(n))) for n in range(32)],u.reg_read(A.UC_ARM_REG_FPSCR),u.reg_read(A.UC_ARM_REG_CPSR)&0xf8000000)
 def test_gate_preserves_all_state_and_only_sets_carrier_request(self):
  for tone in (0,11,12,17,18,19,20,21,22,255):
   e=self.fixture();request=e.alloc(64);si=e.alloc(0x800);e.u.mem_write(request,bytes([0x5a])*64);e.u.mem_write(si+0x77c,bytes([tone]));self.init(e,[]);e.u.reg_write(A.UC_ARM_REG_R4,request);e.u.reg_write(A.UC_ARM_REG_R5,si)
   before=self.snapshot(e);original_lr=e.u.reg_read(A.UC_ARM_REG_LR);gpr=[e.u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(13)];self.run_at(e,0x53513620)
   self.assertEqual(self.snapshot(e),before);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_LR),original_lr)
   after=[e.u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(13)];gpr[0]=request;self.assertEqual(after,gpr)
   expected=bytearray([0x5a]*64)
   if tone in (12,18,19,20,21):expected[0x24]=1
   self.assertEqual(bytes(e.u.mem_read(request,64)),bytes(expected))
 def test_settings_execute_original_and_preserve_original_fp_results(self):
  for site,phase in ((0x535033d8,0),(0x53503aa0,1)):
   for grain in (0,1,2,3):
    e=self.fixture();p=e.alloc(64);si=e.alloc(0x800);settings=e.alloc(16);e.w32(p+0x10,settings)
    for off,v in ((0x793,0),(0x794,0),(0x795,grain),(0x796,0)):e.u.mem_write(si+off,bytes([v]))
    self.init(e,[p,si,1]);before=self.snapshot(e)
    # Real original settings executes, including grain+4 store and VFPoutput.
    seen=[];original_fp=[]
    def observe(u,at,size,data):
     if at==0x5350304c:seen.append(tuple(u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(3)))
     if at in (0x535031e0,0x5350320c,0x53503220,0x53503234,0x53503298):original_fp.append(self.snapshot(e)[2:])
    h=e.u.hook_add(UC_HOOK_CODE,observe);self.run_at(e,site);e.u.hook_del(h)
    self.assertEqual(seen,[(p,si,1)]);self.assertEqual(struct.unpack('<H',e.u.mem_read(settings+4,2))[0],grain)
    self.assertEqual(struct.unpack('<3I',e.u.mem_read(0x63f00000,12)),(0x60040000,p,phase))
    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
    after=self.snapshot(e);self.assertEqual(after[:2],before[:2]);self.assertEqual(after[2][8:],before[2][8:]);self.assertEqual(after[3],before[3])
    # Original settings writes s15=1 when scale!=0; helper may not erase it.
    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_S15),0x3f800000)
    self.assertEqual(len(original_fp),1);self.assertEqual(self.snapshot(e)[2:],original_fp[0])
 def test_helper_rejection_preserves_original_zero_enable(self):
  e=self.fixture(helper_result=0);p=e.alloc(64);si=e.alloc(0x800);t=e.alloc(16);e.w32(p+16,t)
  self.init(e,[p,si,1]);self.run_at(e,0x535033d8);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1) # valid contrast0 originally enables1
  e.u.mem_write(si+0x793,b'\x09');self.init(e,[p,si,1]);self.run_at(e,0x535033d8);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),0)
 def test_real_dispatch_executes_grain_branch_and_reports_original_success_failure(self):
  for fail in (False,True):
   e=self.fixture();p=e.alloc(64);settings=e.alloc(16);ctx=e.alloc(256);e.w32(p+0x10,settings);e.w32(p+4,e.alloc(64));e.w32(p+8,e.alloc(64));e.w32(p+0x2c,e.alloc(64));e.u.mem_write(settings,struct.pack('<4Hf',0,0,2,0,1.0))
   calls=[];original_fp=[]
   def hardware(u,at,size,data):
    if at==0x53680f14:original_fp.append(self.snapshot(e)[2:])
    if at in (0x5367b540,0x5367c158,0x5367ad3c,0x53680088):
     calls.append(at);u.reg_write(A.UC_ARM_REG_R0,0 if fail and at==0x5367ad3c and calls.count(at)>1 else 1);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
   h=e.u.hook_add(UC_HOOK_CODE,hardware);self.init(e,[ctx,p,0]);before=self.snapshot(e);self.run_at(e,0x53503ab4);e.u.hook_del(h)
   expected=0 if fail else 1;self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),expected)
   self.assertEqual(struct.unpack('<3I',e.u.mem_read(0x63f00010,12)),(0x60040000,p,expected))
   self.assertEqual(calls.count(0x5367ad3c),2);self.assertEqual(self.snapshot(e)[:2],before[:2])
   self.assertEqual(self.snapshot(e)[2][8:],before[2][8:]);self.assertFalse(e.assertions)
   self.assertEqual(len(original_fp),1);self.assertEqual(self.snapshot(e)[2:],original_fp[0])
 def test_zero_grain_original_sizing_stays_zero_without_allocation(self):
  e=self.fixture(helper_result=0);p=e.alloc(64);settings=e.alloc(16);si=e.alloc(0x800);ctx=e.alloc(256);size=e.alloc(4);e.w32(p+16,settings)
  self.init(e,[p,si,1]);self.run_at(e,0x535033d8)
  self.assertEqual(struct.unpack('<H',e.u.mem_read(settings+4,2))[0],0)
  visited=[]
  def hardware(u,at,n,data):
   if at in (0x5367b540,0x5367c158,0x5367ad3c,0x53680088):visited.append(at);u.reg_write(A.UC_ARM_REG_R0,1);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
  h=e.u.hook_add(UC_HOOK_CODE,hardware);cursor=e.cursor;e.call(0x53680dbc,ctx,p,size);e.u.hook_del(h)
  self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1);self.assertEqual(struct.unpack('<I',e.u.mem_read(size,4))[0],0);self.assertEqual(e.cursor,cursor);self.assertNotIn(0x5367ad3c,visited)
 def test_builder_fails_closed_and_budget_no_global_services(self):
  self.assertLessEqual(len(self.code),700);self.assertEqual(len(self.manifest['patches']),4)
  self.assertEqual(self.manifest['filesystem_calls'],0);self.assertEqual(self.manifest['allocator_calls'],0)
  with tempfile.TemporaryDirectory() as d:
   for site in SITES:
    bad=bytearray(self.rom);bad[site-BASE]^=1
    with self.assertRaisesRegex(ValueError,'preimage'):build(d,0x541a0000,self.exports,bad)
   with self.assertRaises(ValueError):build(d,0x541a0000,{})
