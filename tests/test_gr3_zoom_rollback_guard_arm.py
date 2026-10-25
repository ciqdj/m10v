"""Rollback native getter guards preserve28..50 and bound stale persisted data."""
import struct,unittest
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,arm_const as A
from scripts.build_gr3_zoom import build
from scripts.build_gr3_m10v_library import capture_stock_rtos
RAM=0x60000000;BASE=0x54180000;STOP=RAM+0xff000;SP=RAM+0xe0000
class Guard(unittest.TestCase):
 def test_real_original_getters_return_bounded_float_and_keep_stack(self):
  rom=capture_stock_rtos();blob,m=build(BASE,rom,aspect=True)
  for name in ('front','back'):
   for raw in [*[(struct.unpack('<I',struct.pack('<f',n/28))[0]) for n in range(28,51)],0,0x7fc00000,0x7f800000,0xbf800000,0x4036db6e]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x53000000,rom);u.mem_write(BASE,blob);u.mem_map(RAM,0x100000)
    u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
    obj,props=RAM+0x1000,RAM+0x2000
    u.mem_write(obj+4,struct.pack('<I',props));u.mem_write(obj+0x518,struct.pack('<I',props));u.mem_write(props+0x4c4,struct.pack('<I',raw))
    u.reg_write(A.UC_ARM_REG_R0,obj);u.reg_write(A.UC_ARM_REG_R4,0x12345678);u.reg_write(A.UC_ARM_REG_SP,SP);u.reg_write(A.UC_ARM_REG_LR,STOP)
    def boundary(q,addr,size,data):
     if addr==0x535516f8:q.reg_write(A.UC_ARM_REG_S0,raw)
     elif addr not in (0x536ae71c,0x536ae870):return
     q.reg_write(A.UC_ARM_REG_PC,q.reg_read(A.UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,boundary)
    u.emu_start(m['symbols']['m10v_zoom_guard_'+name],STOP,count=10000)
    expected=0x3f800000 if raw<0x3f800000 or raw>=0x7f800000 else min(raw,0x3fe49249)
    self.assertEqual(u.reg_read(A.UC_ARM_REG_S0),expected)
    self.assertEqual(u.reg_read(A.UC_ARM_REG_SP),SP);self.assertEqual(u.reg_read(A.UC_ARM_REG_R4),0x12345678)
