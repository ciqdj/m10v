"""Execute native width/height/draw guards from a fully exported GR III BIN."""
import os,struct,subprocess,tempfile,unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[1]
ARTIFACT=Path(os.environ.get('M10V_TEST_FIRMWARE_DIR',ROOT/'builds/gr3-2460-5213-20261024'))
@unittest.skipUnless((ARTIFACT/'fw/fwdc239b.bin').exists(),'exported current candidate required')
class IconLimitTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  with tempfile.TemporaryDirectory() as t:
   script="""import{readFileSync,writeFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;let at=0;while(d.toString('ascii',at,at+4)!=='RTOS')at+=16+d.readUInt32LE(at+12);writeFileSync(process.argv[2],d.subarray(at+16,at+16+d.readUInt32LE(at+12)));"""
   p=Path(t)/'rtos';subprocess.run(['node','--input-type=module','-e',script,str(ARTIFACT/'fw/fwdc239b.bin'),str(p)],cwd=ROOT,check=True);cls.code=p.read_bytes()
 def machine(self):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,n in [(0x53000000,0x2000000),(0x55000000,0x1000000),(0x10000000,0x200000)]:u.mem_map(a,n)
  u.mem_write(0x53000000,self.code);u.reg_write(UC_ARM_REG_SP,0x100f0000);u.reg_write(UC_ARM_REG_LR,0x10000000)
  return u
 def test_5213_reaches_original_dimension_getters_and_next_id_is_rejected(self):
  for address in [0x53209fb8,0x53209fec]:
   for icon,expected in [(774,40),*[(i,40) for i in range(775,782)],(782,0)]:
    u=self.machine();u.reg_write(UC_ARM_REG_R1,icon);u.emu_start(address,0x10000000,count=100000)
    self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x10000000)
    self.assertEqual(u.reg_read(UC_ARM_REG_R0),expected,(hex(address),icon))
 def test_5213_passes_native_draw_bound_and_next_id_is_rejected(self):
  for icon,end in [(774,0x5320a7e4),*[(i,0x5320a7e4) for i in range(775,782)],(782,0x5320a98c)]:
   u=self.machine();u.reg_write(UC_ARM_REG_R3,icon);u.reg_write(UC_ARM_REG_R4,0x55002000);u.reg_write(UC_ARM_REG_FP,0x100f0000)
   u.hook_add(UC_HOOK_CODE,lambda m,a,n,d:m.emu_stop() if a in (0x5320a7e4,0x5320a98c) else None)
   u.emu_start(0x5320a7cc,0x10000000,count=1000);self.assertEqual(u.reg_read(UC_ARM_REG_PC),end)
if __name__=='__main__':unittest.main()
