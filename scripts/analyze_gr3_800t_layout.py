"""Throwaway read-only CPU probe; executes original ARM bytes, writes no firmware."""
from pathlib import Path
import argparse,subprocess
parser=argparse.ArgumentParser(description='Execute exact GR III descriptor functions; no firmware writes')
parser.add_argument('firmware',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
import struct,json,hashlib
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
rtos=subprocess.check_output(['node','--input-type=module','-e',
 f"import {{readFileSync}} from 'node:fs'; import {{readOfficialSection}} from '{(root/'node/firmware.mjs').as_uri()}'; process.stdout.write(readOfficialSection(readFileSync(process.argv[1]),'RTOS'));", str(args.firmware)])
base=0x53000000
u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(base,(len(rtos)+4095)&~4095);u.mem_write(base,rtos)
u.mem_map(0x55000000,0x20000)
stop=0x5501f000
assertions=[]
def hook(uc,addr,size,data):
 if addr in (0x536b93d0,0x536b9f1c):
  if uc.reg_read(UC_ARM_REG_R0)!=1:raise AssertionError(f'original assertion failed at {addr:x}')
  assertions.append(addr);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,hook)
def run(addr,args):
 u.reg_write(UC_ARM_REG_SP,0x5501e000);u.reg_write(UC_ARM_REG_LR,stop)
 for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(r,v)
 u.emu_start(addr,stop,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 return u.reg_read(UC_ARM_REG_R0)
results=[]
for fmt,descriptor_fmt in ((3,1),(4,2)):
 assert run(0x534a276c,[fmt])==descriptor_fmt
 assert run(0x534a27d8,[descriptor_fmt])==fmt
 for width,height in ((6000,4000),(4000,2664),(2992,2000),(720,480),(1920,1080),(6016,4000)):
  stride=(width+15)&~15
  u.mem_write(0x55000100,struct.pack('<II',stride,height))
  run(0x534a2ac4,[0x55000200,0x60000000,0x55000100,fmt])
  y,c,third=struct.unpack('<III',u.mem_read(0x55000200,12))
  assert (y,c,third)==(0x60000000,0x60000000+stride*height,0)
  results.append(dict(image_format=fmt,descriptor_format=descriptor_fmt,width=width,height=height,stride=stride,y=hex(y),combined_chroma=hex(c),third=third))
# Native descriptor cache routine chooses a whole-plane span for 422, half-plane for 420.
cache=[]
def cache_hook(uc,addr,size,data):
 if addr==0x536bbc30:
  uc.reg_write(UC_ARM_REG_R0,0x5536d1b4);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 elif addr==0x536bbc3c:
  cache.append(dict(address=hex(uc.reg_read(UC_ARM_REG_R1)),bytes=uc.reg_read(UC_ARM_REG_R2)))
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
u.hook_add(UC_HOOK_CODE,cache_hook)
cache_cases=[]
for fmt in (1,2):
 desc=bytearray(32);desc[0]=fmt
 struct.pack_into('<III',desc,4,0x60000000,0x616e3600,0)
 struct.pack_into('<HHHH',desc,0x10,6000,4000,6000,4000)
 u.mem_write(0x55000300,bytes(desc));cache.clear();run(0x534ab1a4,[0,0x55000300])
 assert cache==[dict(address='0x60000000',bytes=24000000),dict(address='0x616e3600',bytes=24000000 if fmt==1 else 12000000)]
 cache_cases.append(dict(format=fmt,calls=list(cache)))
print(json.dumps(dict(schema='m10v-gr3-descriptor-cpu-probe/v1',rtos_sha256=hashlib.sha256(rtos).hexdigest(),address_cases=results,cache_cases=cache_cases,passed=len(results)+len(cache_cases),limits=['Synthetic inputs; no camera memory observed','Cache manager calls were intercepted; CP15/hardware not emulated','Combined chroma byte order and signedness are not proved']),indent=2))
