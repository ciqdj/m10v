"""Actual linked ARM caller-frame hooks; stock services are bounded fixtures."""
import hashlib,importlib.util,struct,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class FileTraceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.stock=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes()
  save=module('save',ROOT/'scripts/build_gr3_save_trace.py');cls.save_blob,cls.save=save.build(Path(cls.temp.name)/'save',0x540e0000)
  file=module('file',ROOT/'scripts/build_gr3_file_trace.py');cls.blob,cls.manifest=file.build(Path(cls.temp.name)/'file',0x540e2000,cls.save['exports'],0x540e3000)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_manifest_checked_patch_and_frame_geometry(self):
  self.assertEqual(len(self.manifest['patches']),4);self.assertEqual(self.manifest['mutable_global_bytes'],0)
  for patch in self.manifest['patches']:
   at=patch['address']-0x53000000;self.assertEqual(self.stock[at:at+4].hex(),patch['expected_hex'])
  self.assertLess(-0x54,-0x50);self.assertLess(-0x50,-0x3c)
 def run_hooks(self,allocation_failure=False,clock_failure=False):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_CPSR
  registers=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12]
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x53000000,self.stock);u.mem_write(self.save['base'],self.save_blob);u.mem_write(self.manifest['base'],self.blob);u.mem_map(0x55000000,0x300000)
  outerfp=0x552000fc;outersp=outerfp-0x5c;heap=0x55010000;descriptor=0x55020000;stop=0x552f0000
  u.mem_write(outerfp-0x38,struct.pack('<I',descriptor));u.mem_write(outersp,struct.pack('<III',0x11112222,0x33334444,0x55556666));u.mem_write(outerfp-0x50,b'\xa5'*4)
  flushed=[];freed=[];writes=[];bridge=[];foreign=[];finished=[]
  def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def hook(uc,address,size,data):
   if address==stop:finished.append(True);uc.emu_stop()
   elif address==0x536af2a8:self.assertEqual(uc.reg_read(UC_ARM_REG_R0),656);ret(0 if allocation_failure else heap)
   elif address==0x53050b7c:
    uc.mem_write(uc.reg_read(UC_ARM_REG_R0),struct.pack('<II',7,12345));ret(1 if clock_failure else 0)
   elif address==0x534eb8b4 and uc.reg_read(UC_ARM_REG_LR)==stop:
    writes.append(True);self.assertEqual(uc.reg_read(UC_ARM_REG_SP),outersp);self.assertEqual(uc.mem_read(outersp,12),struct.pack('<III',0x11112222,0x33334444,0x55556666))
    self.assertEqual(uc.reg_read(UC_ARM_REG_LR),stop);uc.emu_stop()
   elif address==self.save['exports']['m10v_save_trace_bridge']:
    bridge.append([uc.reg_read(r) for r in registers[:4]]);ret(0x7f)
   elif address==0x534ecb3c:
    foreign.append([uc.reg_read(r) for r in registers[:2]]);ret(0x42)
   elif address==0x540e3000:
    pointer=uc.reg_read(UC_ARM_REG_R0);self.assertEqual(pointer,heap);self.assertEqual(uc.mem_read(outerfp-0x50,4),bytes(4));flushed.append(bytes(uc.mem_read(pointer,656)));ret(0)
   elif address==0x536af2e4:freed.append(uc.reg_read(UC_ARM_REG_R0));ret(0)
  u.hook_add(UC_HOOK_CODE,hook)
  values=[0x12340000+i for i in range(13)];values[11]=outerfp
  def call(symbol,sp,fp=None):
   finished.clear()
   for r,v in zip(registers,values):u.reg_write(r,v)
   if fp is not None:u.reg_write(UC_ARM_REG_R11,fp)
   u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_CPSR,0xa0000013)
   u.emu_start(self.manifest['exports'][symbol],stop+4,count=50000)
  call('m10v_file_trace_prewrite',outersp)
  self.assertEqual([u.reg_read(r) for r in registers],values);self.assertEqual(u.reg_read(UC_ARM_REG_CPSR)&0xf0000000,0xa0000000)
  self.assertEqual(len(writes),1);pointer=struct.unpack('<I',u.mem_read(outerfp-0x50,4))[0];self.assertEqual(pointer,0 if allocation_failure else heap)
  # Execute original inner prologue, not an assumed fp linkage.
  u.reg_write(UC_ARM_REG_SP,outersp);u.reg_write(UC_ARM_REG_R11,outerfp);u.reg_write(UC_ARM_REG_LR,0x534e882c)
  u.emu_start(0x534eb8b4,0x534eb8cc,count=6)
  innerfp=u.reg_read(UC_ARM_REG_R11);self.assertEqual(struct.unpack('<I',u.mem_read(innerfp-12,4))[0],outerfp)
  call('m10v_file_trace_bridge',u.reg_read(UC_ARM_REG_SP),innerfp)
  self.assertEqual(bridge,[[values[0],values[1],pointer,descriptor]])
  self.assertEqual(u.reg_read(UC_ARM_REG_R0),0x7f)
  u.mem_write(innerfp-4,struct.pack('<I',0x534e9990));u.mem_write(innerfp-12,struct.pack('<I',0x90000000))
  call('m10v_file_trace_bridge',u.reg_read(UC_ARM_REG_SP),innerfp)
  self.assertEqual(foreign,[[values[0],values[1]]]);self.assertEqual(u.reg_read(UC_ARM_REG_R0),0x42)
  call('m10v_file_trace_postcleanup',outersp)
  self.assertTrue(finished);self.assertEqual(u.reg_read(UC_ARM_REG_SP),outersp)
  self.assertEqual([u.reg_read(r) for r in registers],values);self.assertEqual(u.reg_read(UC_ARM_REG_CPSR)&0xf0000000,0xa0000000)
  self.assertEqual(freed,[] if allocation_failure else [heap]);self.assertEqual(len(flushed),0 if allocation_failure else 1)
  if flushed:
   words=struct.unpack('<164I',flushed[0]);self.assertEqual(words[1],3)
   self.assertEqual(words[4:9],(195,descriptor,12345,7,0x80000000 if clock_failure else 0))
   self.assertEqual(words[9:14],(197,descriptor,0x33334444,0x11112222,0x55556666))
   self.assertEqual(words[14:19],(196,descriptor,12345,7,values[5]|(0x80000000 if clock_failure else 0)))
 def test_owned_lifetime_original_prologue_stackargs_and_full_registers(self):self.run_hooks()
 def test_optional_allocation_failure_still_calls_original_save(self):self.run_hooks(allocation_failure=True)
 def test_clock_failure_still_calls_original_save(self):self.run_hooks(clock_failure=True)
if __name__=='__main__':unittest.main()
