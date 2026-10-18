#!/usr/bin/env python3
"""Offline research probe of the Ricoh-GRMod bridge strategy on public GR III.

No update BIN is emitted. Current-version getters are substituted, but the
version comparisons and CPU validation execute real ARM instructions.
Run from any directory with the project's Unicorn-enabled Python environment.
"""
import sys,struct,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
from tests.test_gr3_updater_version_gate import UpdaterVersionGateTests
T=UpdaterVersionGateTests;T.setUpClass();t=T();results=[]
for patched in (False,True):
 for kind in (0,1,2,3,4,6):
  for dsp,cpu in ((0x020b151b,0x020b151b),(0x020a151b,0x020b151b),(0x020b151b,0x020a151b)):
   u,_=t.machine(current_dsp=dsp,current_cpu=cpu)
   assert bytes(u.mem_read(0x536285dc,4))==bytes.fromhex('042803e3')
   if patched:u.mem_write(0x536285dc,bytes.fromhex('e6ffffea'))
   obj=0x55001000;buffer=0x55010000;parser=0x55002000
   for at,value in ((obj+8,0x55003000),(obj+0x1c,parser),(obj+0x20,parser),(obj+0x24,parser),(parser+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buffer)):
    u.mem_write(at,struct.pack('<I',value))
   for off in (0x38,0x50,0x90):u.mem_write(buffer+off,bytes.fromhex('020a151b'))
   got=t.call(u,0x536284e0,obj)
   want=1 if patched else int((dsp<=0x020a151b if kind in (0,1) else cpu<=0x020a151b if kind==6 else dsp<=0x020a151b and cpu<=0x020a151b))
   assert got==want,(patched,kind,dsp,cpu,got,want)
   results.append({'patched':patched,'type':kind,'current_dsp':hex(dsp),'current_cpu':hex(cpu),'accepted':bool(got)})
 for mode,want in (('official',1),('bad_sum',0),('wrong_project',0)):
  u,_=t.machine()
  if patched:u.mem_write(0x536285dc,bytes.fromhex('e6ffffea'))
  data=bytearray(t.cpu)
  if mode=='bad_sum':data[0x93]^=1
  if mode=='wrong_project':struct.pack_into('<I',data,0x80,609)
  obj=0x55001000;buffer=0x55010000;u.mem_write(buffer,bytes(data))
  u.mem_write(obj+0xc,struct.pack('<I',buffer));u.mem_write(obj+0x14,struct.pack('<I',588))
  got=t.call(u,0x536290c8,obj);assert got==want
  results.append({'patched':patched,'cpu_validation':mode,'accepted':bool(got)})
 u,_=t.machine()
 if patched:u.mem_write(0x536285dc,bytes.fromhex('e6ffffea'))
 assert t.call(u,0x536284e0,0x55001000)==0
 results.append({'patched':patched,'null_candidate_rejected':True})
# Stage one: next minor is above the entire 2.10 hidden-version range.
for kind in (0,1,2,3,4,6):
 u,_=t.machine(current_dsp=0x020affff,current_cpu=0x020affff)
 obj=0x55001000;buffer=0x55010000;parser=0x55002000
 for at,value in ((obj+8,0x55003000),(obj+0x1c,parser),(obj+0x20,parser),(obj+0x24,parser),(parser+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buffer)):
  u.mem_write(at,struct.pack('<I',value))
 for off in (0x38,0x50,0x90):u.mem_write(buffer+off,bytes.fromhex('020b151b'))
 assert t.call(u,0x536284e0,obj)==1
 results.append({'patched':False,'stage':'first_package_next_minor','type':kind,'current_components':'2.10.255.255','candidate_components':'2.11.21.27','accepted':True})
out={'scope':'GR III public firmware local gate only; no flash writes; current-version getters substituted','cases':results,'count':len(results),'camera_verified':False}
Path('builds/gr3-bridge-research').mkdir(parents=True,exist_ok=True)
Path('builds/gr3-bridge-research/gr3-gate-probe.json').write_text(json.dumps(out,indent=2))
print('PASS',len(results),'stock/patched ARM cases; no camera validation')
