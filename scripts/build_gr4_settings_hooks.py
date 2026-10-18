"""Audited GR IV 1.11 owned settings pages and ImageControl ABI.

All mutations carry official preimages. No instruction at a normalized-search
candidate is accepted without its surrounding native ownership/call contract.
"""
import hashlib
import json
import struct
from pathlib import Path
from scripts.build_gr3_menu_patches import assembly, branch, movw

BASE=0x53000000
ROOT=Path(__file__).resolve().parents[1]
PROFILE=json.loads((ROOT/'native/gr4/ui-abi.json').read_text())
BASE_VTABLE=[0x53182c50,0x53182be4,0x53182c2c,0x53182ba8,0x53182bb0,
 0x53184558,0x53182bb4,0x53182bb8,0x53182bbc,0x53182bc0,
 0x53182bc8,0x53182bd0,0x531835cc,0x53182bd4,0x53182bdc]
ORIGINAL_ENTRIES={
 0x00:0x533b70cc,0x10:0x5337f824,0x20:0x53397044,0x30:0x53380fac,0x40:0x533971cc,
 0x50:0x531c635c,0x60:0x531c6338,0x80:0x533bebdc,0x90:0x533bedb0,
 0xa0:0x531c57b8,0xb0:0x531c6228}

def build_settings_hooks(base,symbols,rtos=None):
 if rtos is None:rtos=(ROOT/'data/research/gr4/RTOS.bin').read_bytes()
 if hashlib.sha256(rtos).hexdigest()!=PROFILE['source_sha256']:raise ValueError('GR4 settings requires exact official 1.11 RTOS')
 image=bytearray();exports={};patches=[];rows=[]
 def data(raw):
  image.extend(bytes(-len(image)&3));a=base+len(image);image.extend(raw);return a
 def stub(text):
  image.extend(bytes(-len(image)&3));return data(assembly(text,base+len(image)))
 def patch(a,expected,replacement,label):
  if rtos[a-BASE:a-BASE+len(expected)]!=expected:raise ValueError('GR4 UI preimage differs: '+label)
  patches.append(dict(address=a,expected=expected.hex(),replacement=replacement.hex(),label=label))
 def word(a,old,new,label):patch(a,struct.pack('<I',old),struct.pack('<I',new),label)
 def trampoline(name,a,old):
  at=base+len(image);exports[name]=data(struct.pack('<II',old,branch(at+4,a+4)))
 trampoline('m10v_settings_factory_original',0x53185f7c,0xe300312e)
 trampoline('m10v_settings_top_dtor_original',0x531afb34,0xe1a0c00d)
 table=list(BASE_VTABLE)
 for offset,name in [(4,'destroy'),(8,'destroy'),(0x1c,'enter'),(0x24,'ready'),(0x28,'key')]:
  table[offset//4]=symbols['m10v_settings_controller_'+name]
 vt=data(struct.pack('<15I',*table))
 exports['m10v_settings_controller_vtable']=stub(f'movw r0,#{vt&65535};movt r0,#{vt>>16};bx lr')
 for address,original,name,link in [(0x53185f7c,0xe300312e,'factory',False),
   (0x531afb34,0xe1a0c00d,'top_dtor',False),(0x5318788c,0xeb00b262,'top_ctor',True),
   (0x532544c0,0xeb002153,'key_route',True)]:
  word(address,original,branch(address,symbols['m10v_settings_controller_'+name],link),'settings '+name)
 word(0x53187880,0xe30103ec,movw(0,0x196c),'TopMenu owned controller tail')
 word(0x53d9ca98,0x1f1e1c1a,0x211e1c1a,'Setup row count31 to33')
 for i in range(2):
  caption=1175+i
  render=stub('push {r4,lr};mov r4,r1;mov r0,r4;mov r1,#0;bl 0x5357a428;'+
   f'mov r0,r4;movw r1,#{caption};pop {{r4,lr}};b 0x5357a1c0')
  rows.append(render)
  patch(0x53d9ca10+0x8c+(31+i)*8,bytes(8),struct.pack('<II',render,0),'Setup independent row renderer')
  word(0x53d9ca10+0x1bc+(31+i)*4,0x10000000,0x0200f100+i,'Setup independent destination')
 return bytes(image),dict(exports=exports,vtable=vt,rows=rows,patches=patches,owner_bytes=0x196c,
   private_routes=[0x0200f100,0x0200f101],camera_tested=False)
