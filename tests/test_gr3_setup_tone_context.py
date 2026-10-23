"""Execute the official setter: stale ImageControl context targets other banks.
OS property notification is stubbed; stock dispatch, getters and writes execute.
"""
import struct, unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn import arm_const as A

class SetupToneContextTests(unittest.TestCase):
 def test_official_setter_routes_by_context_and_active_shooting_bank(self):
  path=Path('/tmp/m10v-sd-research/rtos.bin')
  if not path.exists():self.skipTest('official RTOS required')
  rom=path.read_bytes()
  for context in (0,1):
   for bank in (0,1,2):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x2000000);u.mem_write(0x53000000,rom)
    u.mem_map(0x55000000,0x100000)
    root,prop,model,data=0x55001000,0x55002000,0x55003000,0x55004000
    u.mem_write(prop+4,struct.pack('<8I',*([data]*8)));u.mem_write(data+0x1c0,bytes([bank]))
    u.mem_write(data+0x57c,bytes([bank]));u.mem_write(model+0x1b,bytes([context,bank]))
    def services(m,at,size,unused):
     if at==0x5320ad88:m.reg_write(A.UC_ARM_REG_R0,root)
     elif at==0x5320b31c:m.reg_write(A.UC_ARM_REG_R0,prop)
     elif at==0x532750f8:m.reg_write(A.UC_ARM_REG_R0,1)
     else:return
     m.reg_write(A.UC_ARM_REG_PC,m.reg_read(A.UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,services)
    u.reg_write(A.UC_ARM_REG_SP,0x550f0000);u.reg_write(A.UC_ARM_REG_LR,0x550ff000)
    u.reg_write(A.UC_ARM_REG_R0,model);u.reg_write(A.UC_ARM_REG_R1,18)
    u.emu_start(0x532c26c0,0x550ff000,count=10000)
    self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x550ff000)
    if context==0:self.assertEqual(bytes(u.mem_read(data+0x1c2+bank*2,1)),b'\x12')
    else:self.assertEqual(bytes(u.mem_read(data+0x1c2,6)),bytes(6))
