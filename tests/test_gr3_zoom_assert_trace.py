"""Diagnostic assertion logging preserves native failure semantics and ABI."""
import struct,unittest
from scripts.build_gr3_zoom import build
from scripts.build_gr3_m10v_library import capture_stock_rtos
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
class AssertTrace(unittest.TestCase):
 def test_diagnostic_hook_logs_failure_and_always_delegates_original(self):
  stock=capture_stock_rtos();code,m=build(0x54180000,stock,debug_log=0x541f0000)
  for condition in (0,1):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x2000000);u.mem_write(0x53000000,stock);u.mem_write(m['base'],code);u.mem_map(0x60000000,0x100000)
   for p in m['patches']:u.mem_write(p['address'],struct.pack('<I',p['replacement']))
   u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
   sp=0x600e0000;stop=0x600ff000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop)
   regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3];args=[condition,0x53b00000,0x53b00010,1234]
   for r,v in zip(regs,args):u.reg_write(r,v)
   u.mem_write(sp,struct.pack('<I',0x53b00020));events=[];delegated=[]
   def hook(uc,a,n,d):
    if a==0x541f0000:
     events.append([uc.reg_read(r) for r in regs]+[struct.unpack('<I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0]])
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif a==0x536b93d4:
     delegated.append([uc.reg_read(r) for r in regs]);self.assertEqual(uc.reg_read(UC_ARM_REG_SP),sp);uc.reg_write(UC_ARM_REG_PC,stop)
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x536b93d0,stop,count=10000)
   self.assertEqual(delegated,[args]);self.assertEqual(events,[[212,*args[1:],stop]] if condition==0 else [])
