"""GR4 slider ARM proof, including draw-command equality with the GR3 template.
Native callback/gfx services are explicit mocks; no LCD/hardware claim.
"""
import json,struct,unittest,hashlib
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from scripts.build_gr4_level import ROOT,compile_level,apply_level,BASE,FRAME_VTABLE,CALLBACK_POINTER
CODE=0x54e00000
OWNER=0x60001000
VIEW=0x60003000
FRAMES=(0x60004000,0x60005000)
SOURCE=0x60006000
OLD_BASE=0x540b99c8
class LevelTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.firmware=(ROOT/'data/research/gr4/RTOS.bin').read_bytes()
  cls.code,cls.report=compile_level(CODE)
  cls.template=json.loads((ROOT/'.runtime/grlife/reconstruction/firmware_store/templates/urban160-level-slider.json').read_text())
 def machine(self):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(BASE,0x2000000);u.mem_write(BASE,self.firmware);u.mem_write(CODE,self.code);u.mem_write(OLD_BASE,bytes.fromhex(self.template['code_hex']));u.mem_map(0x60000000,0x20000)
  self.fills=[];self.calls=[];self.ready=1;self.context=0x60008000;self.native_geometry=True
  def hook(m,a,n,c):
   r=[m.reg_read(z) for z in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
   if a in [0x5323bbb8,0x5320804c]:m.reg_write(UC_ARM_REG_R0,self.ready)
   elif a in [0x5323bd30,0x532081ec]:m.reg_write(UC_ARM_REG_R0,self.context)
   elif a in [0x5323c588,0x53208a2c]:self.fills.append((r[0],bytes(m.mem_read(r[1],24))))
   elif a in [0x535880b0,0x533ab9bc]:self.calls.append(('base_draw',r[0],r[1]))
   elif a==0x5357cbe8:self.calls.append(('native_normalize',r[0]))
   elif a in [0x5318d8f0,0x53175da8]:self.calls.append(('native_callback',*r))
   elif a in [0x535899fc,0x533ad308]:self.calls.append(('invalidate',r[0]))
   elif a in [0x53589ab4,0x533ad3c0]:m.mem_write(r[0]+0x9e,bytes([r[1]]));self.calls.append(('visible',r[0],r[1]))
   elif a==0x53587c3c and self.native_geometry:return
   elif a in [0x53587c3c,0x533ab548]:m.mem_write(r[0]+0x30,bytes(m.mem_read(r[1],16)))
   else:return
   m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);return u
 def call(self,u,name,*args):
  for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2],args):u.reg_write(r,v&0xffffffff)
  u.reg_write(UC_ARM_REG_SP,0x6001f000);u.reg_write(UC_ARM_REG_LR,0x6001fffc)
  u.emu_start(name if isinstance(name,int) else self.report['symbols']['m10v_level_'+name],0x6001fffc,count=100000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x6001fffc);self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x6001f000)
  return u.reg_read(UC_ARM_REG_R0)
 def setup(self,u,roll=0,pitch=0,rotation=0):
  u.mem_write(OWNER+0x15c,struct.pack('<I',VIEW));u.mem_write(OWNER+0x4ec,struct.pack('<I',SOURCE));u.mem_write(OWNER+0x2cc,struct.pack('<II',*FRAMES))
  u.mem_write(VIEW+0x108,struct.pack('<f',roll));u.mem_write(VIEW+0x110,struct.pack('<f',pitch));u.mem_write(VIEW+0x120,struct.pack('<i',rotation))
  for offset,v in [(0x9e,1),(0x11f,2),(0x118,1),(0x119,0),(0x11d,1)]:u.mem_write(VIEW+offset,bytes([v]))
  for f in FRAMES:u.mem_write(f,struct.pack('<I',FRAME_VTABLE))
 def test_ieee_conversion_matches_quarter_units_and_rejects_nonfinite(self):
  u=self.machine()
  for value in [-360,-180,-90,-24.25,-.25,0,.25,24.25,90,180,360]:
   bits=struct.unpack('<I',struct.pack('<f',value))[0];actual=self.call(u,'quarter',bits);actual=actual-(1<<32) if actual&(1<<31) else actual
   self.assertEqual(actual,int(value*4))
  for bits in [0x7f800000,0xff800000,0x7fc00000,1]:self.assertEqual(self.call(u,'quarter',bits),0)
 def test_draw_commands_match_existing_gr3_template_exactly(self):
  for rect in [(218,388,284,44),(654,98,44,284)]:
   for position in [-96,-25,0,25,96]:
    for color in [2,27]:
     for clip in [(0,0,720,480),(300,300,100,120),(0,0,0,0)]:
      u=self.machine();f=FRAMES[0];u.mem_write(f+0x30,struct.pack('<4i',*rect));u.mem_write(f+0x64,struct.pack('<4i',*clip));u.mem_write(f+0x9e,b'\1');u.mem_write(f+0xf6,bytes([position&255,color]))
      self.call(u,0x540b9c2c,f,0x60009000);expected=list(self.fills);self.fills=[]
      self.call(u,'draw',f,0x60009000);self.assertEqual(self.fills,expected,(rect,position,color,clip))
      self.assertEqual(self.calls[-1],('base_draw',f,0x60009000))
 def test_hidden_unavailable_or_null_target_falls_through_without_fill(self):
  for visible,ready,context,target in [(0,1,1,1),(1,0,1,1),(1,1,0,1),(1,1,1,0)]:
   u=self.machine();u.mem_write(FRAMES[0]+0x9e,bytes([visible]));self.ready=ready;self.context=context
   self.call(u,'draw',FRAMES[0],target);self.assertFalse(self.fills);self.assertEqual(len(self.calls),1)
 def test_callback_four_rotations_colors_visibility_and_original_first(self):
  for rotation,roll,pitch,expected in [(0,5,3,(20,12)),(180,175,3,(20,-12)),(90,-85,3,(12,-20)),(-90,85,3,(-12,-20))]:
   u=self.machine();self.setup(u,roll,pitch,rotation);u.mem_write(VIEW+0x11d,b'\0');self.call(u,'callback',OWNER,0,1)
   self.assertEqual(self.calls[0],('native_callback',OWNER,0,1))
   self.assertEqual(tuple(struct.unpack('<b',u.mem_read(f+0xf6,1))[0] for f in FRAMES),expected)
   self.assertEqual([u.mem_read(f+0xf7,1)[0] for f in FRAMES],[2,27] if abs(rotation)==90 else [27,2])
   self.assertEqual([u.mem_read(f+0x9e,1)[0] for f in FRAMES],[0,1] if abs(rotation)==90 else [1,0])
   self.assertEqual(u.mem_read(VIEW+0x9e,1),b'\0')
 def test_callback_matches_gr3_template_for_angles_and_rotations(self):
  for rotation in [0,90,-90,180]:
   for roll in [-180,-90,-24,-5,0,5,24,90,180]:
    for pitch in [-30,0,30]:
     new=self.machine();self.setup(new,roll,pitch,rotation);self.call(new,'callback',OWNER,0,1)
     expected=[bytes(new.mem_read(f+0xf6,2))+bytes(new.mem_read(f+0x9e,1)) for f in FRAMES]
     old=self.machine();old.mem_write(OWNER+0x15c,struct.pack('<I',VIEW));old.mem_write(OWNER+0x4e8,struct.pack('<I',SOURCE));old.mem_write(OWNER+0x2c8,struct.pack('<II',*FRAMES))
     old.mem_write(SOURCE+0x100,struct.pack('<hh',int(roll*4)-360,int(pitch*4)))
     for off,value in [(0x9e,1),(0x11b,2),(0x114,0),(0x115,1),(0x119,1)]:old.mem_write(VIEW+off,bytes([value]))
     old.mem_write(VIEW+0x11c,struct.pack('<i',rotation))
     for f in FRAMES:old.mem_write(f,struct.pack('<I',0x53c0a720))
     self.call(old,OLD_BASE,OWNER,0,1)
     self.assertEqual([bytes(old.mem_read(f+0xf6,2))+bytes(old.mem_read(f+0x9e,1)) for f in FRAMES],expected,(rotation,roll,pitch))
 def test_other_styles_owner_modes_and_hidden_state_restore_stock_vtable(self):
  for field,value in [(0x11f,0),(0x11f,1),(0x9e,0),(0x2d4,2),(0x2d4,3)]:
   u=self.machine();self.setup(u);self.call(u,'callback',OWNER,0,1)
   for f in FRAMES:self.assertEqual(struct.unpack('<I',u.mem_read(f,4))[0],self.report['private_vtable'])
   u.mem_write(VIEW+0x9e,b'\1');u.mem_write((OWNER if field==0x2d4 else VIEW)+field,bytes([value]));self.call(u,'callback',OWNER,0,1)
   for f in FRAMES:self.assertEqual(struct.unpack('<I',u.mem_read(f,4))[0],FRAME_VTABLE)
 def test_executes_native_frame_geometry_setter(self):
  u=self.machine();self.setup(u);self.native_geometry=True
  self.call(u,'callback',OWNER,0,1)
  self.assertEqual(struct.unpack('<4i',u.mem_read(FRAMES[0]+0x20,16)),(218,388,284,44))
  self.assertEqual(struct.unpack('<4i',u.mem_read(FRAMES[1]+0x20,16)),(654,98,44,284))
 def test_original_level_setter_proves_float_and_style_offsets(self):
  u=self.machine();u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  u.reg_write(UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',5.75))[0]);u.reg_write(UC_ARM_REG_S1,struct.unpack('<I',struct.pack('<f',3.25))[0])
  # The original callback supplies these stack arguments: sensitivity, camera rotation, style.
  u.mem_write(0x6001f000,struct.pack('<III',1,3,2));u.reg_write(UC_ARM_REG_R3,0)
  self.call(u,0x5357ce18,VIEW,1,1)
  self.assertEqual(struct.unpack('<f',u.mem_read(VIEW+0x108,4))[0],5.75)
  self.assertEqual(struct.unpack('<f',u.mem_read(VIEW+0x110,4))[0],3.25)
  self.assertEqual(u.mem_read(VIEW+0x11f,1),b'\2')
  self.assertEqual(u.mem_read(VIEW+0x11d,1),b'\1')
 def test_apply_is_preimage_guarded_and_changes_one_official_word(self):
  class Patch:
   def __init__(self,raw):self.image=bytearray(raw);self.changes=[]
   def word(self,a):return struct.unpack_from('<I',self.image,a-BASE)[0]
   def set_word(self,a,v,label):struct.pack_into('<I',self.image,a-BASE,v);self.changes.append((a,label))
   def append(self,data,alignment):
    self.image.extend(bytes(-len(self.image)&(alignment-1)));a=BASE+len(self.image);self.image.extend(data);return a
  p=Patch(self.firmware);r=apply_level(p)
  self.assertEqual([a for a,label in p.changes],[CALLBACK_POINTER])
  before=bytearray(self.firmware);struct.pack_into('<I',before,CALLBACK_POINTER-BASE,r['hook']['replacement']);self.assertEqual(p.image[:len(before)],before)
  self.assertEqual(hashlib.sha256(p.image[r['base']-BASE:r['base']-BASE+r['bytes']]).hexdigest(),r['sha256'])
  for bad in [CALLBACK_POINTER,FRAME_VTABLE]:
   p=Patch(self.firmware);p.image[bad-BASE]^=1;before=bytes(p.image)
   with self.assertRaisesRegex(ValueError,'preimage'):apply_level(p)
   self.assertEqual(bytes(p.image),before)
 def test_unknown_frame_type_remains_untouched(self):
  u=self.machine();self.setup(u);u.mem_write(FRAMES[0],struct.pack('<I',0x12345678));before=bytes(u.mem_read(FRAMES[0],0x100));self.call(u,'callback',OWNER,0,1);self.assertEqual(bytes(u.mem_read(FRAMES[0],0x100)),before);self.assertEqual(len(self.calls),1)
 def test_only_draw_vtable_slot_changes_and_hook_preimage_is_exact(self):
  vt=self.report['private_vtable']-CODE;actual=self.code[vt:vt+88];original=self.firmware[FRAME_VTABLE-BASE:FRAME_VTABLE-BASE+88]
  self.assertEqual(actual[:19*4],original[:19*4]);self.assertEqual(actual[20*4:],original[20*4:]);self.assertEqual(struct.unpack_from('<I',actual,19*4)[0],self.report['symbols']['m10v_level_draw'])
  self.assertEqual(struct.unpack_from('<I',self.firmware,CALLBACK_POINTER-BASE)[0],0x5318d8f0)
  self.assertEqual(hashlib.sha256(self.code).hexdigest(),self.report['sha256'])
 def test_production_apply_needs_no_extracted_research_file(self):
  from unittest.mock import patch as mock_patch
  import sys
  sys.path.insert(0,str(ROOT/'vendor/gr4'))
  from gr4_editor.slots import _Patch
  read=Path.read_bytes
  def without_research(path):
   if 'data/research/' in str(path):raise FileNotFoundError('research data is not deployed')
   return read(path)
  candidate=_Patch(self.firmware)
  with mock_patch.object(Path,'read_bytes',without_research):
   report=apply_level(candidate)
  self.assertEqual(candidate.word(CALLBACK_POINTER),report['symbols']['m10v_level_callback'])
if __name__=='__main__':unittest.main()
