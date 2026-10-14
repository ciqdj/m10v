from unicorn import *
from unicorn.arm_const import *
import json,struct,hashlib,argparse
from pathlib import Path
p=argparse.ArgumentParser(description="Execute exact GR III 2.10 recipe planner ARM bytes; hardware is not emulated.")
p.add_argument("--rtos",required=True,type=Path)
p.add_argument("--output",required=True,type=Path)
a=p.parse_args()
b=a.rtos.read_bytes();out=[]
sha=hashlib.sha256(b).hexdigest()
assert sha=="8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67", "Exact baseline required"
allowed=[0,1,5,6,7,8,12]
for mode in range(15):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x53000000,b);u.mem_map(0x60000000,0x100000);u.mem_map(0x61000000,0x10000)
 u.reg_write(UC_ARM_REG_SP,0x6100f000);u.reg_write(UC_ARM_REG_LR,0x600f0000);u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_R1,mode);steps=[];finished=[False]
 def h(u,a,s,x):
  if a==0x600f0000:finished[0]=True;u.emu_stop()
  if a==0x535112c4:
   steps.append({'index':u.reg_read(UC_ARM_REG_R1),'kind':u.reg_read(UC_ARM_REG_R2),'module':u.reg_read(UC_ARM_REG_R3),'extra':struct.unpack('<I',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0],'caller':hex(u.reg_read(UC_ARM_REG_LR)-4)})
  if a==0x536b93d0:u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,h)
 try:
  u.emu_start(0x53511418,0x600f0004,count=30000)
  assert finished[0], 'Planner instruction limit exhausted'
  out.append({'mode':mode,'steps':steps,'completed':True})
 except UcError as e:out.append({'mode':mode,'error':str(e),'pc':hex(u.reg_read(UC_ARM_REG_PC)),'steps':steps})
checks=[]
for mode in allowed:
 m=out[mode];assert 'error' not in m,m
 steps=m['steps']; prod=next(i for i,x in enumerate(steps) if x['kind']==1 and x['module']==5)
 jpeg=next(i for i,x in enumerate(steps) if x['kind']==1 and x['module']==6)
 assert prod<jpeg and steps[prod+1]['kind']==10 and steps[jpeg+1]['kind']==10
 assert any(x['kind']==3 and x['module']==5 for x in steps[jpeg+2:])
 assert any(x['kind']==3 and x['module']==6 for x in steps[jpeg+2:])
 checks.append({'mode':mode,'producerIndex':steps[prod]['index'],'jpegIndex':steps[jpeg]['index'],'passed':True})
report={'sha256':sha,'allowedRecipeModes':allowed,'checks':checks,'recipes':out,'limitations':['Only recipe planner ARM executed; assertion logging intercepted','Hardware and scheduler event delivery not emulated','Mode names are not asserted']}
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'sha256':sha,'allowedRecipeModes':allowed,'checks':checks,'output':str(a.output)},indent=2))
