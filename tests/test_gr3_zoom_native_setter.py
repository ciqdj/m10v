"""Original GR III crop setter + actual property handler ARM execution.

Only scheduler dispatch, mutexes, memcpy and UI notification are boundary
adapters. The full native setters, validation, normalization, quality update,
buffer swap, and getter run from the hash-checked official RTOS fixture.
"""
import hashlib,os,pathlib,struct,unittest
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
BASE=0x53000000;RAM=0x60000000;STOP=RAM+0xff000;BRIDGE=STOP+4
FRONT=RAM+0x1000;FSTATE=RAM+0x2000;BACK=RAM+0x3000;MODEL=RAM+0x4000;CURRENT=RAM+0x5000;DRAFT=RAM+0x7000;EVENTS=RAM+0x9000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def bits(mm):return struct.unpack('<I',struct.pack('<f',mm/28))[0]
class NativeZoomSetter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=pathlib.Path(os.environ.get('M10V_GR3_ORIGINAL_RTOS','/tmp/m10v-sd-research/rtos.bin'))
  if not p.exists():raise unittest.SkipTest('official GR III RTOS fixture required')
  cls.firmware=p.read_bytes()
  if hashlib.sha256(cls.firmware).hexdigest()!='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67':raise ValueError('unexpected RTOS hash')
 def machine(self,old=50,mode=0):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(BASE,0x2000000);u.mem_write(BASE,self.firmware);u.mem_map(0x55000000,0x1000000);u.mem_map(RAM,0x100000)
  u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000);u.reg_write(UC_ARM_REG_SP,RAM+0xe0000)
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  word(FRONT+4,FSTATE);word(FSTATE+0x4c4,bits(old));word(RAM+0x100,BACK);word(BACK+0x518,MODEL)
  word(MODEL,CURRENT);word(MODEL+4,DRAFT);word(MODEL+8,EVENTS)
  for state in [CURRENT,DRAFT]:word(state+0x7b8,bits(old));word(state+0xfd8,bits(old));u.mem_write(state+0x6c0,bytes([mode]));u.mem_write(state+0x7bc,b'\x02')
  self.trace=[];self.assertions=[];self.messages=[];pending=[]
  def hook(uc,a,size,data):
   self.trace.append(a);r=[uc.reg_read(reg) for reg in REGS];ret=0
   if a==0x53525d5c:ret=RAM+0x100
   elif a in [0x536ae71c,0x536ae870,0x536a9dd4,0x536a9e8c]:ret=1
   elif a==0x5313fd80:uc.mem_write(r[0],bytes(uc.mem_read(r[1],r[2])));ret=r[0]
   elif a==0x536abd28:
    self.assertEqual(r[2],0xd5);self.assertIn(r[1],[1,2])
    out=struct.unpack('<I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0]
    pending.append((uc.reg_read(UC_ARM_REG_LR),r[1],out))
    uc.reg_write(UC_ARM_REG_R1,r[3]);uc.reg_write(UC_ARM_REG_R2,0);uc.reg_write(UC_ARM_REG_LR,BRIDGE)
    uc.reg_write(UC_ARM_REG_PC,0x53542410 if r[1]==1 else 0x53542404);return
   elif a==BRIDGE:
    lr,command,out=pending.pop()
    if command==2:uc.mem_write(out,bytes([r[0]&255]))
    uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,lr);return
   elif a==0x5320ad88:ret=RAM+0x200
   elif a==0x5320aefc:ret=RAM+0x300
   elif a==0x532288b0:self.messages.append(r[1:]);ret=1
   elif a in [0x536b93d0,0x53820074]:self.assertions.append((a,r));raise AssertionError(f'native assertion {a:x}: {r}')
   else:return
   uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);return u
 def set(self,u,mm):
  u.reg_write(UC_ARM_REG_R0,FRONT);u.reg_write(UC_ARM_REG_S0,bits(mm));u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(0x53252684,STOP,count=100000)
 def back(self,u):
  u.reg_write(UC_ARM_REG_R0,BACK);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(0x5354a7bc,STOP,count=10000);return u.reg_read(UC_ARM_REG_S0)
 def test_native_fifty_to_eighty_runs_validation_setter_swap_and_getter(self):
  u=self.machine();self.set(u,80);self.assertEqual(self.back(u),bits(80));self.assertFalse(self.assertions)
  for a in [0x53252614,0x5354e4c8,0x5354c918,0x53542410,0x5355dd9c,0x535544ac,0x5355dbbc,0x5355dae4,0x5355da14,0x5355198c,0x535516f8]:self.assertIn(a,self.trace)
  self.assertEqual(self.messages,[[0x184,0,0]])
  self.assertEqual(struct.unpack('<H',u.mem_read(EVENTS+2,2))[0],0xd5)
 def test_stock_and_custom_transitions_preserve_actual_native_float(self):
  for old,new in [(28,50),(50,80),(80,50),(80,28),(50,100),(100,80),(50,50)]:
   with self.subTest(old=old,new=new):
    u=self.machine(old);self.set(u,new);self.assertEqual(self.back(u),bits(new));self.assertFalse(self.assertions)
if __name__=='__main__':unittest.main()
