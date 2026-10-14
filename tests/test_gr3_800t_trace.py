import struct,unittest
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from scripts.build_gr3_800t_trace import build_trace
class TraceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.code=dict(build_trace())['logger']
 def run_trace(self,stage=6,context=0x550029b8,open_ok=True,write_ok=True,manager_ok=True,stats=None):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,n in [(0x540bc000,4096),(0x540be000,4096),(0x53584000,4096),(0x53100000,4096),(0x53cd1000,4096),(0x55000000,0x10000),(0x58000000,0x10000)]:u.mem_map(a,n)
  u.mem_write(0x540bc000,self.code);u.mem_write(0x55000014,struct.pack('<I',0x55000100));u.mem_write(0x55000100,struct.pack('<I',0x53cd1000))
  for off,a in [(28,0x53100100),(32,0x53100200),(40,0x53100300)]:u.mem_write(0x53cd1000+off,struct.pack('<I',a))
  ctx=bytearray(96)
  for off,v in [(0,0x53d0fbe0),(0x34,0x55007000),(0x38,0x55008000),(0x3c,0x55004000),(0x48,0x55005000),(0x4c,0x55006000)]:struct.pack_into('<I',ctx,off,v)
  u.mem_write(0x550029b8,bytes(ctx));u.mem_write(0x5500777c,b'\x12');u.mem_write(0x5500800c,b'\x01\x01')
  for off,value in ((0x77d,6),(0x77e,2),(0x77f,7),(0x781,4),(0x784,3)):
   u.mem_write(0x55007000+off,bytes((value,)))
  if stats is not None:u.mem_write(0x55009000,struct.pack('<8I',*stats))
  before=bytes(u.mem_read(0x55000000,0x10000));calls=[];records=[]
  def call(uc,a,size,data):
   args=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];sp=uc.reg_read(UC_ARM_REG_SP)
   if a==0x540be000:result=0x80043726
   elif a==0x535847d8:result=0x55000000 if manager_ok else 0
   elif a==0x53100100:
    path=bytes(uc.mem_read(args[1],16)).split(b'\0')[0];calls.append(('open',path,args[2]));uc.mem_write(args[3],struct.pack('<I',7 if open_ok else 0));result=int(open_ok)
   elif a==0x53100300:calls.append(('write',args[1],args[3]));records.append(bytes(uc.mem_read(args[2],args[3])));result=int(write_ok)
   elif a==0x53100200:calls.append(('close',args[1]));result=1
   else:return
   uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def guard(uc,access,a,n,v,data):
   # File-system doubles may set the caller's stack out-parameters; no
   # pixel/CFA/config writes are permitted by the actual ARM logger.
   self.assertTrue(0x58000000<=a and a+n<=0x5800fff0,(hex(a),n))
  u.hook_add(UC_HOOK_CODE,call);u.hook_add(UC_HOOK_MEM_WRITE,guard)
  u.reg_write(UC_ARM_REG_R0,stage);u.reg_write(UC_ARM_REG_R1,context);u.reg_write(UC_ARM_REG_R2,0x55009000 if stats is not None else 0);u.reg_write(UC_ARM_REG_SP,0x5800fff0);u.reg_write(UC_ARM_REG_LR,0x53100ffc)
  u.emu_start(0x540bc000,0x53100ffc,count=100000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x53100ffc);self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x5800fff0)
  self.assertEqual(bytes(u.mem_read(0x55000000,0x10000)),before)
  return calls,records
 def test_writes_bounded_snapshot_and_closes(self):
  calls,records=self.run_trace();self.assertEqual(calls,[('open',b'C:\\M10V8.BIN',0),('write',7,256),('close',7)])
  r=struct.unpack('<64I',records[0]);self.assertEqual(r[:5],(0x5630314d,0x54303038,3,6,0x550029b8));self.assertEqual(r[44],18);self.assertEqual(r[45],257)
  self.assertEqual(r[47],0x80043726)
 def test_invalid_context_records_reason_without_dereference(self):
  calls,records=self.run_trace(stage=1,context=0x40000000);r=struct.unpack('<64I',records[0]);self.assertEqual(r[3:5],(1,0x40000000));self.assertEqual(r[8:],(0,)*56)
 def test_open_failure_and_missing_manager_do_not_write(self):
  self.assertEqual(self.run_trace(open_ok=False)[0],[('open',b'C:\\M10V8.BIN',0)])
  self.assertEqual(self.run_trace(manager_ok=False),([],[]))
 def test_write_failure_still_closes(self):
  self.assertEqual(self.run_trace(write_ok=False)[0][-1],('close',7))
 def test_preserves_and_serializes_core_statistics(self):
  stats=(0,255,18,4096,123456,125678,400000,402000)
  _,records=self.run_trace(stage=100,stats=stats)
  self.assertEqual(struct.unpack('<64I',records[0])[56:],stats)
