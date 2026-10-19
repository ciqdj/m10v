"""Exercise actual BE file boundary at original SP, with explicit context cookie."""
import importlib.util,struct,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class BEFileTraceTests(unittest.TestCase):
 def test_stock_call_sp_descriptor_status_and_optional_failure(self):
  builder=module('be',ROOT/'scripts/build_gr3_be_file_trace.py')
  save=module('save',ROOT/'scripts/build_gr3_save_trace.py')
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  import unicorn.arm_const as a
  for allocation_failure in (False,True):
   for status in (0,2,4,6):
    with tempfile.TemporaryDirectory() as d:
     saveblob,sm=save.build(Path(d)/'save',0x540e0000);blob,m=builder.build(Path(d)/'be',0x540e4000,sm['exports'],0x540e6000)
    stock=(ROOT/'builds/gr3-extension-validation/official-rtos.bin').read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x53000000,stock);u.mem_write(sm['base'],saveblob);u.mem_write(m['base'],blob);u.mem_map(0x55000000,0x300000)
    fp=0x552000fc;sp=fp-0x54;heap=0x55010000;stop=0x552f0000;regs=[getattr(a,'UC_ARM_REG_R'+str(i)) for i in range(13)];values=[0x12340000+i for i in range(13)];values[1]=fp-0x4c;values[5]=0x55020000;values[11]=fp
    u.mem_write(fp-0x4c,bytes(0x24));u.mem_write(fp-0x4c,b'\x02');u.mem_write(values[5],struct.pack('<I',0x53d0fb00));u.mem_write(values[5]+0x30,struct.pack('<II',0x550301a8,0x55040000));flushed=[];freed=[];calls=[];clocks=[]
    def ret(v):u.reg_write(a.UC_ARM_REG_R0,v);u.reg_write(a.UC_ARM_REG_PC,u.reg_read(a.UC_ARM_REG_LR))
    def hook(uc,at,size,data):
     if at==0x536af2a8:ret(0 if allocation_failure else heap)
     elif at==0x53050b7c:
      clocks.append(1);uc.mem_write(uc.reg_read(a.UC_ARM_REG_R0),struct.pack('<II',7,12345+len(clocks)*1000));ret(0)
     elif at==0x53697658:
      calls.append(1);self.assertEqual(uc.reg_read(a.UC_ARM_REG_SP),sp);self.assertEqual([uc.reg_read(r) for r in regs],values);self.assertEqual(uc.reg_read(a.UC_ARM_REG_CPSR)&0xf0000000,0xa0000000);self.assertEqual(uc.reg_read(a.UC_ARM_REG_LR),0x5350b384)
      uc.mem_write(sp-0x200,b'\xa5'*0x200);uc.mem_write(fp-0x3c,bytes([status]));ret(0x40+status)
     elif at==0x540e6000:
      self.assertEqual(struct.unpack('<I',uc.mem_read(sp,4))[0],0);flushed.append(bytes(uc.mem_read(uc.reg_read(a.UC_ARM_REG_R0),656)));ret(0)
     elif at==0x536af2e4:freed.append(uc.reg_read(a.UC_ARM_REG_R0));ret(0)
     elif at==0x5350b388:uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    for r,v in zip(regs,values):u.reg_write(r,v)
    u.reg_write(a.UC_ARM_REG_SP,sp);u.reg_write(a.UC_ARM_REG_LR,0x5350b384);u.reg_write(a.UC_ARM_REG_CPSR,0xa0000013)
    u.mem_write(0x5350b384,bytes.fromhex(m['patches'][1]['replacement_hex']));u.emu_start(m['exports']['m10v_be_file_pre'],stop,count=100000)
    expected=values.copy();expected[0]=0x40+status;expected[3]=status
    self.assertEqual([u.reg_read(r) for r in regs],expected);self.assertEqual(u.reg_read(a.UC_ARM_REG_SP),sp);self.assertEqual(u.reg_read(a.UC_ARM_REG_LR),0x5350b384);self.assertEqual(u.reg_read(a.UC_ARM_REG_CPSR)&0xf0000000,0xa0000000);self.assertEqual(len(calls),1);self.assertEqual(freed,[] if allocation_failure else [heap])
    if not allocation_failure:
     words=struct.unpack('<164I',flushed[0]);self.assertEqual(words[1],4);self.assertEqual(words[4:9],(200,values[5],13345,7,0));self.assertEqual(words[9:14],(203,values[5],0x53d0fb00,0x550301a8,0x55040000));self.assertEqual(words[14:19],(201,values[5],14345,7,0x40+status));self.assertEqual(words[19:24],(202,values[5],status,2,0x40+status))
if __name__=='__main__':unittest.main()
