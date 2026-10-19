import struct,unittest
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn import arm_const as A
from scripts.build_gr3_capture_lifecycle import build_hooks

class CaptureLifecycleHooksTests(unittest.TestCase):
 def test_real_callsite_stubs_preserve_flags_registers_stack_and_native_call(self):
  base=0x54160000;callback=base+0xf000
  code,manifest=build_hooks(base,callback)
  for patch in manifest['patches']:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_map(0x55000000,0x100000)
   u.mem_write(base,code);seen=[]
   regs=[getattr(A,f'UC_ARM_REG_R{i}')for i in range(13)]+[A.UC_ARM_REG_SP,A.UC_ARM_REG_LR,A.UC_ARM_REG_CPSR]
   for i,r in enumerate(regs[:13]):u.reg_write(r,0x10101010+i)
   sp=0x550f0000;u.reg_write(A.UC_ARM_REG_SP,sp);u.reg_write(A.UC_ARM_REG_R11,sp-0x100)
   u.mem_write(sp-0x160,struct.pack('<I',0x12345678))
   u.mem_write(sp,bytes(range(32)));u.reg_write(A.UC_ARM_REG_CPSR,0xa80f0013)
   u.reg_write(A.UC_ARM_REG_LR,patch['address']+4)
   before=[u.reg_read(r)for r in regs]
   def service(machine,pc,size,data):
    if pc==callback:
     seen.append(tuple(machine.reg_read(getattr(A,f'UC_ARM_REG_R{i}'))for i in range(3)))
     self.assertEqual(machine.reg_read(A.UC_ARM_REG_SP)&7,0)
     for i in range(4):machine.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),0xffff)
     machine.reg_write(A.UC_ARM_REG_CPSR,0x13);machine.reg_write(A.UC_ARM_REG_PC,machine.reg_read(A.UC_ARM_REG_LR))
    elif pc==0x536bbc30:
     self.assertEqual([machine.reg_read(r)for r in regs],before)
     machine.reg_write(A.UC_ARM_REG_PC,machine.reg_read(A.UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,service)
   u.emu_start(patch['entry'],patch['address']+4,count=10000)
   expected=before.copy()
   if patch['event']==191:expected[5]=0x12345678
   self.assertEqual([u.reg_read(r)for r in regs],expected)
   self.assertEqual(seen,[(before[4],patch['event'],before[0])]);self.assertEqual(bytes(u.mem_read(sp,32)),bytes(range(32)))
