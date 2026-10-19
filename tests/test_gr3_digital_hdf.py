"""HDF correctness/performance contracts, including the real ARM hooks."""
import ctypes as C
import struct,subprocess,tempfile,unittest,zlib
from pathlib import Path
from tests import test_gr3_m10v_library as host
State,Image,Date,STORE=host.State,host.Image,host.Date,host.STORE

ROOT=Path(__file__).resolve().parents[1]

class HdfStateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  host.NativeFilmLibraryTests.setUpClass.__func__(cls)
 def test_legacy_soft_is_ignored_even_with_no_scratch(self):
  for film in [1,33,34,66,67,68]:
   images=[]
   for soft in [0,3]:
    s=State();self.lib.m10v_library_init(C.byref(s));s.slots[0].film=film;s.slots[0].grain=0;s.slots[0].halo_gain=0;s.slots[0].soft=soft
    s.crc=zlib.crc32(bytes(s)[:100]);y=(C.c_uint8*128)(*[240 if i==60 else 100 for i in range(128)]);uv=(C.c_uint8*128)(*([128]*128))
    im=Image(y,uv,128,128,16,8,16)
    self.assertEqual(self.lib.m10v_library_render(C.byref(im),C.byref(s),0,None,1,None,0),0)
    images.append((bytes(y),bytes(uv)))
   self.assertEqual(*images)

class HdfArmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from scripts.build_gr3_m10v_library import build
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  cls.manifest=build(cls.tmp.name);cls.runtime=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
 def test_official_preimage_and_native_hdf_are_installed_together(self):
  h=self.manifest.get('digital_hdf')
  self.assertIsNotNone(h,'HDF native chain is missing')
  self.assertEqual(h['recipe_extra_bytes'],16)
  self.assertEqual(h['isp_filesystem_calls'],0)
  self.assertEqual(h['pixel_loops'],0)
  self.assertEqual(h['native_parameter_values'],[5,6,7])
  self.assertEqual(len(h['patches']),8)

class HdfExecutionTests(HdfArmTests):
 def machine(self,strength=0):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn import arm_const as A
  from scripts.build_gr3_digital_hdf import official_rtos
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,n in [(0x53000000,0x1500000),(0x55000000,0x200000),(0x57000000,0x100000)]:u.mem_map(a,n)
  rom=official_rtos();u.mem_write(0x53000000,rom);u.mem_write(self.manifest['base'],self.runtime)
  for p in self.manifest['digital_hdf']['patches']:u.mem_write(p['address'],struct.pack('<I',p['replacement']))
  u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
  e={'u':u,'A':A,'recipe':0x55010000,'si':0x55040000,'request':0x55050000,'params':0x57001000,'values':0x57002000,'loads':0,'allocs':[],'strength':strength,'load_fail':False,'alloc_fail':False,'phase':'setup'}
  def put(a,v):u.mem_write(a,struct.pack('<I',v))
  e['put']=put
  def services(uc,a,n,d):
   r0=uc.reg_read(A.UC_ARM_REG_R0)
   if a==0x5351091c:
    e['allocs'].append(r0);uc.reg_write(A.UC_ARM_REG_R0,0 if e['alloc_fail'] else e['recipe'])
   elif a==self.manifest['symbols']['m10v_hdf_load']:
    self.assertEqual(e['phase'],'producer','filesystem load inside a hot callback')
    e['loads']+=1;uc.mem_write(r0,struct.pack('<I',e['strength']));uc.reg_write(A.UC_ARM_REG_R0,0xffffffff if e['load_fail'] else 0)
   elif a==0x535134fc:
    # External stock request producer. Native HDF must only change its spatial
    # flag, never erase other original request fields or its return value.
    uc.mem_write(r0+0x24,b'\0');uc.reg_write(A.UC_ARM_REG_R0,0x35)
   elif a==0x536b82d4:uc.reg_write(A.UC_ARM_REG_R0,0)
   elif a in (0x53825648,0x53825fa8,0x53828014):self.fail('unexpected native filesystem callback')
   elif a in (0x536af2a8,0x536af31c):self.fail('unexpected HDF heap allocation')
   else:return
   uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,services)
  shared=self.manifest['digital_hdf'].get('shared_recipe',False)
  self.call(e,self.manifest['symbols']['m10v_save_trace_recipe_alloc' if shared else 'm10v_hdf_alloc'],0x4778)
  self.assertEqual(e['allocs'],[0x50f0 if shared else 0x4788]);put(e['recipe'],0x53d0fc90)
  ctx=e['recipe']+0x4320;put(ctx,0x53d0fc60);put(ctx+0x30,e['recipe']+0x1a8);put(ctx+0x34,e['si']);put(e['recipe']+0x5c,e['request']);put(e['params']+0x10,e['values'])
  u.mem_write(e['si']+0x793,bytes([4,4,0,0]));u.mem_write(e['si']+0x77c,b'\x0c');u.mem_write(e['request'],bytes([0x5a])*64)
  return e
 def call(self,e,entry,*args,regs=None,stop=0x570ff000,stack=()):
  u=e['u'];A=e['A'];sp=0x570fe000
  for n in range(13):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),args[n] if n<len(args) else 0x12340000+n)
  for n,v in (regs or {}).items():u.reg_write(getattr(A,'UC_ARM_REG_'+n),v)
  u.reg_write(A.UC_ARM_REG_CPSR,0xa0000013);u.reg_write(A.UC_ARM_REG_SP,sp);u.reg_write(A.UC_ARM_REG_LR,stop)
  if stack:u.mem_write(sp,struct.pack('<'+'I'*len(stack),*stack))
  preserved=[u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(4,12)]
  u.emu_start(entry,stop,count=200000)
  self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),stop,'ARM hook exhausted instruction budget')
  self.assertEqual(u.reg_read(A.UC_ARM_REG_SP),sp)
  self.assertEqual([u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(4,12)],preserved)
  return u.reg_read(A.UC_ARM_REG_R0)
 def produce(self,e):
  e['phase']='producer';self.call(e,self.manifest['symbols']['m10v_hdf_producer'],e['recipe']);e['phase']='hot'
 def gate(self,e):
  return self.call(e,self.manifest['digital_hdf']['entries']['request'],e['request'],e['si'],1,regs={'R4':e['recipe']})
 def settings(self,e,execution):
  ctx=e['recipe']+0x4320
  if self.manifest['digital_hdf'].get('shared_recipe'):
   site=0x53503aa0 if execution else 0x535033d8
   entry=next(p['entry'] for p in self.manifest['capture_lifecycle']['native_grain']['patches'] if p['address']==site)
  else:entry=self.manifest['digital_hdf']['entries']['settings_'+('0x53503aa0' if execution else '0x535033d8')]
  self.call(e,entry,e['params'],e['si'],1,regs={'R4':ctx,'R12':ctx})
  return struct.unpack('<4hf',e['u'].mem_read(e['values'],12))
 def test_each_grade_uses_identical_planning_and_execution_and_no_hot_fs(self):
  for strength in range(4):
   e=self.machine(strength);self.produce(e);self.assertEqual(self.gate(e),0x35)
   before=bytes(e['u'].mem_read(e['request'],64));self.assertEqual(before[0x24],bool(strength));self.assertEqual(before[:0x24]+before[0x25:],bytes([0x5a])*63)
   plan=self.settings(e,False);execution=self.settings(e,True)
   self.assertEqual(plan,execution);self.assertEqual(plan,(0,0 if not strength else strength+4,0,0,1.0));self.assertEqual(e['loads'],1)
 def test_five_carriers_and_plain_standard_enable_hdf_but_hdr_is_untouched(self):
  for tone in (11,12,18,19,20,21,14,0,255):
   e=self.machine(2);e['u'].mem_write(e['si']+0x77c,bytes([tone]));self.produce(e);self.gate(e)
   self.assertEqual(e['u'].mem_read(e['request']+0x24,1),b'\x01' if tone in (11,12,18,19,20,21) else b'\x00')
 def test_settings_are_immutable_after_menu_change_and_failure_clears_reuse(self):
  e=self.machine(1);self.produce(e);self.gate(e);e['strength']=3
  self.assertEqual(self.settings(e,False)[1],5);self.assertEqual(self.settings(e,True)[1],5)
  e['load_fail']=True;self.produce(e);self.gate(e)
  self.assertEqual(self.settings(e,False)[1],0);self.assertEqual(e['u'].mem_read(e['request']+0x24,1),b'\0')
 def test_foreign_context_or_si_never_writes_parameters(self):
  for mismatch in ('si','owner'):
   e=self.machine(3);self.produce(e);self.gate(e);ctx=e['recipe']+0x4320
   e['put'](ctx+(0x34 if mismatch=='si' else 0x30),e['si']+4 if mismatch=='si' else e['recipe']+0x1ac)
   self.assertEqual(self.settings(e,True)[1],0)
 def test_native_clarity_plans_unchanged_bounded_work_for_all_three_hdf_grades(self):
  e=self.machine();u=e['u'];desc=0x55060000;size=0x55061000
  u.mem_write(desc+0x10,struct.pack('<HH',6000,4000));sizes=[]
  for clarity in (0,-4,4,5,6,7):
   e['put'](size,0)
   self.assertEqual(self.call(e,0x5367c158,0,desc,0,clarity&0xffffffff,stack=(0,size)),1)
   sizes.append(struct.unpack('<I',u.mem_read(size,4))[0])
  self.assertEqual(sizes[0],0);self.assertGreater(sizes[1],0);self.assertEqual(sizes[1:], [sizes[1]]*5)
  self.assertEqual(e['allocs'],[0x50f0 if self.manifest['digital_hdf'].get('shared_recipe') else 0x4788]);self.assertEqual(e['loads'],0)
 def test_original_and_extended_row_addresses_and_status_flags(self):
  from unicorn import arm_const as A
  e=self.machine();u=e['u'];at=self.manifest['digital_hdf']['rows']-48
  for row in range(12):
   # This shim intentionally changes r8, so run it separately from the C ABI
   # harness and compare every other register plus NZCVQ status flags.
   for n in range(13):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),0x12340000+n)
   u.reg_write(A.UC_ARM_REG_R1,0x57003000);u.reg_write(A.UC_ARM_REG_R3,22);u.reg_write(A.UC_ARM_REG_R8,row);u.reg_write(A.UC_ARM_REG_SP,0x570fe000);u.reg_write(A.UC_ARM_REG_CPSR,0xa8000013)
   before=[u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(13)]
   u.emu_start(at,0x5367c7e8,count=100)
   actual=[u.reg_read(getattr(A,'UC_ARM_REG_R'+str(n))) for n in range(13)]
   before[8]=0x57003000+22*row if row<9 else self.manifest['digital_hdf']['rows']+22*(row-9)
   self.assertEqual(actual,before);self.assertEqual(u.reg_read(A.UC_ARM_REG_CPSR)&0xf8000000,0xa8000000);self.assertEqual(u.reg_read(A.UC_ARM_REG_SP),0x570fe000)
