"""Execute exact official SD read/seek/tell wrappers; replace only FS/RTOS leaves.
The real FAT read adapter converts any nonnegative low-level read to boolean 1.
This is why clients must check tell deltas, not treat that boolean as byte count.
"""
import hashlib,json,struct,argparse
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
BASE=0x53000000;STOP=0x550ff000

def analyze(code):
 assert hashlib.sha256(code).hexdigest()=='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
 assert struct.unpack_from('<7I',code,0xd252d0+7*4)==(0x53593e90,0x53593cec,0x5359279c,0x53592888,0x53592974,0x535948c4,0x53592a60)
 results=[]
 for actual in [4096,1024,0,-1]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(BASE,(len(code)+4095)&~4095);u.mem_write(BASE,code);u.mem_map(0x55000000,0x100000)
  def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
  fs=0x55001000;handle=0x55002000;driver=0x55005004;arr=0x55003000
  w(fs,0x53d252d0);w(fs+0x18,arr);w(arr,driver);w(driver,0x53d2201c);w(handle,7);w(handle+4,0)
  position=[0];calls=[]
  def hook(uc,pc,size,data):
   args=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   ret=None
   if pc==0x53592738:ret=0x55007000
   elif pc in [0x536ae71c,0x536ae870]:ret=1
   elif pc==0x5389e624:
    if actual>0:uc.mem_write(args[1],b'Z'*min(actual,args[2]));position[0]+=min(actual,args[2])
    ret=actual
   elif pc==0x5389e7c4:
    offset=struct.unpack('<I',uc.mem_read(args[2],4))[0]
    position[0]=offset if args[3]==0 else position[0]+offset
    w(args[1],0);w(args[2],position[0]);ret=0
   elif pc==0x538a0794:ret=0
   elif pc==0x53589694:
    if args[1]:w(args[1],0 if args[2]==0 else 5)
    ret=0
   if ret is not None:
    calls.append(hex(pc));uc.reg_write(UC_ARM_REG_R0,ret&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  def call(pc,args):
   sp=0x550fe000;u.reg_write(UC_ARM_REG_SP,sp)
   for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):u.reg_write(r,v)
   for i,v in enumerate(args[4:]):w(sp+i*4,v)
   u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(pc,STOP,count=10000)
   assert u.reg_read(UC_ARM_REG_PC)==STOP
   return u.reg_read(UC_ARM_REG_R0)
  assert call(0x53592974,[fs,handle,0,0,0x55008000])==1
  result=call(0x5359279c,[fs,handle,0x55010000,4096,0x55008000]);error=struct.unpack('<I',u.mem_read(0x55008000,4))[0]
  assert call(0x53592a60,[fs,handle,0x55008004,0x55008008])==1
  pos=struct.unpack('<I',u.mem_read(0x55008004,4))[0]
  assert result==(actual>=0) and pos==max(0,actual)
  results.append(dict(low_level_read=actual,wrapper_result=result,error=error,tell=pos,exact_read_accepted=bool(result and not error and pos==4096)))
 return {'official_rtos_sha256':hashlib.sha256(code).hexdigest(),'vtable':'0x53d252d0','read':'0x5359279c','seek':'0x53592974','tell':'0x53592a60','size_by_open_handle':'0x535948c4','cases':results,'boundary':'Real manager read/seek/tell and FAT adapters; mocked mutex, low-level media syscalls and error translation. No physical card/thread timing claim.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('rtos',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();result=json.dumps(analyze(a.rtos.read_bytes()),indent=2)+'\n'
 if a.out:a.out.write_text(result)
 else:print(result)
