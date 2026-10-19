import importlib.util,struct,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class PoolReleaseTests(unittest.TestCase):
 def test_actual_release_return_preserves_result_registers_flags_stack_and_displaced_store(self):
  spec=importlib.util.spec_from_file_location('pool',ROOT/'scripts/build_gr3_pool_release_trace.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  import unicorn.arm_const as a
  with tempfile.TemporaryDirectory() as d:blob,manifest=m.build(d,0x540e4000,0x540e5000,raw_pool_return=0x540e6000)
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x540e4000,blob);u.mem_map(0x55000000,0x10000)
  regs=[getattr(a,'UC_ARM_REG_R'+str(i)) for i in range(13)];values=[0x55000100+i*4 for i in range(13)];values[0]=0x12345678;values[5]=9
  for r,v in zip(regs,values):u.reg_write(r,v)
  sp=0x5500f000;u.reg_write(a.UC_ARM_REG_SP,sp);u.reg_write(a.UC_ARM_REG_LR,0x53521e18);u.reg_write(a.UC_ARM_REG_CPSR,0xa0000013);calls=[];tokens=[]
  def hook(uc,at,size,data):
   if at==0x540e6000:
    tokens.append([uc.reg_read(r) for r in regs[:4]])
    for r in regs[:4]:uc.reg_write(r,0xa5a5a5a5)
    uc.reg_write(a.UC_ARM_REG_PC,uc.reg_read(a.UC_ARM_REG_LR))
   elif at==0x540e5000:
    calls.append([uc.reg_read(r) for r in regs[:4]]+[struct.unpack('<I',uc.mem_read(uc.reg_read(a.UC_ARM_REG_SP),4))[0]])
    for r in regs[:4]+[regs[12]]:uc.reg_write(r,0xdeadbeef)
    uc.reg_write(a.UC_ARM_REG_CPSR,0x60000013);uc.reg_write(a.UC_ARM_REG_PC,uc.reg_read(a.UC_ARM_REG_LR))
   elif at==0x53521e1c:uc.emu_stop()
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x540e4000,0x53521e20,count=1000)
  self.assertEqual(tokens,[[values[4],9,values[6],values[0]]]);self.assertEqual(calls,[[values[4],184,9,values[6],values[0]]]);self.assertEqual([u.reg_read(r) for r in regs],values);self.assertEqual(u.reg_read(a.UC_ARM_REG_SP),sp);self.assertEqual(u.reg_read(a.UC_ARM_REG_LR),0x53521e18);self.assertEqual(u.reg_read(a.UC_ARM_REG_CPSR)&0xf0000000,0xa0000000);self.assertEqual(struct.unpack('<I',u.mem_read(sp+8,4))[0],9)
  self.assertEqual(manifest['patches'][0]['expected_hex'],'08508de5');self.assertEqual(manifest['filesystem_calls'],0)
if __name__=='__main__':unittest.main()
