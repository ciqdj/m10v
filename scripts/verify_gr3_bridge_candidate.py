#!/usr/bin/env python3
"""Execute real gate/CPU validator from final bridge bytes. No camera IO."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.test_gr3_updater_version_gate import UpdaterVersionGateTests as T
candidate=Path(sys.argv[1]).resolve();T.setUpClass();t=T()
js="""import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b).decoded;process.stdout.write(d);"""
d=subprocess.check_output(['node','--input-type=module','-e',js,str(candidate)],cwd=ROOT)
sizes=[72,556,516,44640,21816,17520064,3062784,13899776,49152,131072,37440,18354964,36,6595272]
start=lambda n:sum(x+16 for x in sizes[:n])+16
rom=d[start(5):start(5)+sizes[5]];cpu=d[start(9):start(9)+sizes[9]];outer=candidate.read_bytes()
assert outer[0x38:0x3c]==outer[0x50:0x54]==rom[0x2038:0x203c]==cpu[0x90:0x94]==bytes.fromhex('020a211b')
assert rom[0x6285dc:0x6285e0]==bytes.fromhex('e6ffffea')
rows=[]
def gate(u,kind,header,cpu_payload):
 obj=0x55001000;buf=0x55010000;p=0x55002000
 for at,v in ((obj+8,0x55003000),(obj+0x1c,p),(obj+0x20,p),(obj+0x24,p),(p+0xc,0x55004000),(obj+0x2c,kind),(obj+0x38,buf)):u.mem_write(at,struct.pack('<I',v))
 u.mem_write(buf,header[:128]);u.mem_write(buf+0x90,cpu_payload[0x90:0x94]);return t.call(u,0x536284e0,obj)
stock=(ROOT/'bin/fwdc239b-gr3-official.bin').read_bytes()
# Type 2/3/4 compare DSP and CPU; type 6 compares inner CPU only.
# Preserve the type-6 DSP-only acceptance case and add CPU-high rejection.
old=bytearray(outer);old[0x38:0x3c]=old[0x50:0x54]=bytes.fromhex('020a161b')
old_cpu=bytearray(cpu);old_cpu[0x90:0x94]=bytes.fromhex('020a161b')
for kind in (2,3,4,6):
 for current_cpu,want in ((0x020a151b,1 if kind==6 else 0),(0x020a201b,0)):
  u,_=t.machine(0x020a201b,current_cpu)
  got=gate(u,kind,bytes(old),bytes(old_cpu));assert got==want,(kind,hex(current_cpu),got,want)
  rows.append({'stage':'withdrawn','kind':kind,'observed_dsp':'2.10.32.27','synthetic_cpu':hex(current_cpu),'accepted':bool(got)})
for kind in (0,1,2,3,4,6):
 for current,want in ((0x020a21ff,0),(0x020a15ff,1),(0x020a201b,1),(0x020a20ff,1),(0x020a211b,1),(0x020a211c,0)):
  # 0x20 is observed decimal 32; 0x21 is candidate decimal 33.
  u,_=t.machine(current,current);got=gate(u,kind,outer,cpu);assert got==want
  rows.append({'stage':1,'kind':kind,'current':hex(current),'accepted':bool(got)})
 u,_=t.machine(0x020a211b,0x020a211b);u.mem_write(0x53000000,rom)
 assert gate(u,kind,stock,t.cpu)==1;rows.append({'stage':2,'kind':kind,'accepted':True})
for mode,want in (('final_cpu',1),('bad_checksum',0),('wrong_model',0)):
 u,_=t.machine();u.mem_write(0x53000000,rom);data=bytearray(cpu)
 if mode=='bad_checksum':data[0x93]^=1
 if mode=='wrong_model':struct.pack_into('<I',data,0x80,609)
 obj=0x55001000;buf=0x55010000;u.mem_write(buf,bytes(data));u.mem_write(obj+0xc,struct.pack('<I',buf));u.mem_write(obj+0x14,struct.pack('<I',588));assert t.call(u,0x536290c8,obj)==want;rows.append({'cpu':mode,'accepted':bool(want)})
u,_=t.machine();u.mem_write(0x53000000,rom);assert t.call(u,0x536284e0,0x55001000)==0;rows.append({'null_rejected':True})
t.rom=rom
t.test_dsp_package_header_does_not_raise_real_startup_model_reported_version()
rows.append({'final_dsp_runtime_model':'2.10.21.27','actual_getter_executed':True})
print(json.dumps({'candidate_sha256':hashlib.sha256(outer).hexdigest(),'cases':rows,'count':len(rows),'camera_verified':False,'scope':'final RTOS and CPU bytes; substituted current getters; no flash writes'},indent=2))
