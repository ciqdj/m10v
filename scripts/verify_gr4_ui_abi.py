"""Execute the official GR4 factory to verify custom-page owner selection.

Requires Unicorn; this verifies instructions and ABI ownership, not hardware UI.
"""
import json
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC
from scripts.build_gr4_settings_hooks import ROOT, PROFILE

def verify_factory_owner():
 binary=(ROOT/'data/research/gr4/RTOS.bin').read_bytes()
 emulator=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 emulator.mem_map(0x53000000,(len(binary)+0xfff)&~0xfff)
 emulator.mem_write(0x53000000,binary)
 emulator.mem_map(0x56000000,0x10000)
 emulator.mem_map(0x60000000,0x10000)
 evidence=[]
 def hook(cpu,address,size,context):
  if address==0x538e09b0:
   requested=cpu.reg_read(UC_ARM_REG_R0)
   evidence.append({'allocate':requested})
   if requested!=0x13ec:raise AssertionError('route selected another native owner')
   cpu.reg_write(UC_ARM_REG_R0,0x56001000)
   cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
  if address==0x531b421c:
   evidence.append({'constructor':address,'owner':cpu.reg_read(UC_ARM_REG_R0)})
   cpu.emu_stop()
 emulator.hook_add(UC_HOOK_CODE,hook)
 for route in [0x02000060,0x02000061,0x02000062,0x02000063]:
  evidence.clear()
  emulator.mem_write(0x56000000,bytes(0x1000))
  for reg,value in [(UC_ARM_REG_R0,0x56000000),(UC_ARM_REG_R1,route),(UC_ARM_REG_SP,0x6000fff0),(UC_ARM_REG_LR,0x5600fffc)]:emulator.reg_write(reg,value)
  emulator.emu_start(0x53185f7c,0x5600fffc,count=10000)
  assert evidence==[{'allocate':0x13ec},{'constructor':0x531b421c,'owner':0x56001000}],evidence
 return {'schema':'m10v-gr4-ui-executed-abi/v1','factory':0x53185f7c,'routes':[0x02000060,0x02000061,0x02000062,0x02000063],'owner_size':0x13ec,'owner_constructor':0x531b421c,'camera_tested':False}

if __name__=='__main__':print(json.dumps(verify_factory_owner(),indent=2))
