"""Official GR IV instructions with synthetic RAM; no hardware claims."""
import hashlib
import struct
import unittest
from pathlib import Path
from scripts.build_gr4_extensions import apply_extensions,normalize_extensions,PROFILE
ROOT=Path(__file__).resolve().parents[1]
class Patch:
 def __init__(self):self.image=bytearray((ROOT/'data/research/gr4/RTOS.bin').read_bytes());self.changes=[]
 def word(self,a):return struct.unpack_from('<I',self.image,a-0x53000000)[0]
 def set_word(self,a,w,reason):self.changes.append([a,self.word(a),w,reason]);struct.pack_into('<I',self.image,a-0x53000000,w)
class Extensions(unittest.TestCase):
 def test_raw_off_exact_sites_and_no_other_bytes(self):
  p=Patch();original=bytes(p.image);report=apply_extensions(p,{'rawNr':{'mode':'off'}})
  self.assertEqual(report['raw_nr']['patch_count'],3)
  self.assertEqual(p.word(0x5362988c),0xe3a07000);self.assertEqual(p.word(0x536298ac),0xe3a08000);self.assertEqual(p.word(0x538511e8),0xe1a00000)
  sites={0x62988c,0x6298ac,0x8511e8}
  self.assertTrue(all(a//4*4 in sites for a,(x,y) in enumerate(zip(original,p.image)) if x!=y))
 def test_threshold_clears_only_mode_zero_enable_bytes(self):
  p=Patch();before=bytes(p.image);r=apply_extensions(p,{'rawNr':{'mode':'threshold','iso':6400}})
  self.assertEqual(r['raw_nr']['first_enabled_index'],80)
  expected={a-0x53000000+i*20 for a in [0x541d4e48,0x541d1760] for i in range(36,80)}
  self.assertEqual({i for i,(x,y) in enumerate(zip(before,p.image)) if x!=y},expected)
  self.assertTrue(all(p.image[i]==0 for i in expected))
 def test_strict_iso_and_preimage_guard(self):
  for config in [{'rawNr':{'mode':'threshold','iso':6300}},{'rawNr':{'mode':'off','iso':400}},{'level':'true'}]:
   with self.assertRaises(ValueError):normalize_extensions(config)
  p=Patch();p.image[0x62988c]^=1
  with self.assertRaises(ValueError):apply_extensions(p,{'rawNr':{'mode':'off'}})
 def test_stock_makes_no_edits(self):
  p=Patch();before=bytes(p.image);apply_extensions(p,{});self.assertEqual(p.image,before)
 def test_official_nr_table_getter_selects_exact_mode_zero_variants(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR
  p=Patch();apply_extensions(p,{'rawNr':{'mode':'threshold','iso':6400}})
  for variant in (0,1):
   for index in (35,36,79,80,143):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,(len(p.image)+4095)&~4095);u.mem_write(0x53000000,bytes(p.image));u.mem_map(0x55000000,0x60000);u.mem_write(0x55000000,bytes(p.image[0x137b640:0x137b640+0x57480]));u.mem_map(0x60000000,0x20000)
    u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_R1,index);u.reg_write(UC_ARM_REG_R2,variant);u.reg_write(UC_ARM_REG_SP,0x60010000);u.reg_write(UC_ARM_REG_LR,0x6001f000)
    def hook(uc,a,size,data):
     if a==0x53925cac:uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x53926640,0x6001f000,count=100)
    expected=[0x541d4e48,0x541d1760][variant]+index*20
    self.assertEqual(u.reg_read(UC_ARM_REG_R0),expected);self.assertEqual(bytes(u.mem_read(expected,1)),bytes([int(index>=80)]))
 def test_real_still_setup_and_ppu_mask_execute_with_nr_off(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn import arm_const as r
  for patched in (False,True):
   p=Patch()
   if patched:apply_extensions(p,{'rawNr':{'mode':'off'}})
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,(len(p.image)+4095)&~4095);u.mem_write(0x53000000,bytes(p.image));u.mem_map(0x60000000,0x20000)
   u.reg_write(r.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(r.UC_ARM_REG_FPEXC,0x40000000)
   obj=0x60000000;out=obj+0x4000;si=obj+0x8000;flags=obj+0xc000
   u.mem_write(obj+8,struct.pack('<II',obj+0xd000,flags));u.reg_write(r.UC_ARM_REG_R0,obj);u.reg_write(r.UC_ARM_REG_R1,out);u.reg_write(r.UC_ARM_REG_R2,si);u.reg_write(r.UC_ARM_REG_SP,obj+0x18000);u.reg_write(r.UC_ARM_REG_LR,obj+0x1f000)
   def hook(uc,a,size,data):
    if a in (0x5386a608,0x536297ac):uc.reg_write(r.UC_ARM_REG_R0,0);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x53629848,obj+0x1f000,count=1000)
   self.assertEqual(bytes(u.mem_read(out+0x58,1)),bytes([0 if patched else 1]));self.assertEqual(bytes(u.mem_read(out+0x5d,1)),bytes([0 if patched else 1]))
   u.mem_write(out+0x14,bytes([1]));u.reg_write(r.UC_ARM_REG_R5,out);u.reg_write(r.UC_ARM_REG_R9,si);u.emu_start(0x538511c0,0x538511f8,count=100)
   self.assertEqual(u.reg_read(r.UC_ARM_REG_R6)&8,0 if patched else 8)
 def test_negative_film_grain_is_already_admitted_by_official_code(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn import arm_const as r
  p=Patch();before=bytes(p.image);report=apply_extensions(p,{'negativeGrain':True});self.assertEqual(p.image,before);self.assertEqual(report['negative_grain']['patch_count'],0)
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,(len(p.image)+4095)&~4095);u.mem_write(0x53000000,bytes(p.image));u.mem_map(0x60000000,0x20000)
  u.reg_write(r.UC_ARM_REG_R0,0x60000000);u.reg_write(r.UC_ARM_REG_R1,24);u.reg_write(r.UC_ARM_REG_SP,0x60010000);u.reg_write(r.UC_ARM_REG_LR,0x6001f000)
  def hook(uc,a,size,data):
   if a in (0x5323ea84,0x5323f928,0x533cc754,0x538ed930):uc.reg_write(r.UC_ARM_REG_R0,1);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x531c6b1c,0x6001f000,count=200);kind=u.reg_read(r.UC_ARM_REG_R0);self.assertEqual(kind,6)
  u.reg_write(r.UC_ARM_REG_R0,0x60000000);u.reg_write(r.UC_ARM_REG_R1,0);u.reg_write(r.UC_ARM_REG_R2,kind);u.reg_write(r.UC_ARM_REG_R3,9);u.reg_write(r.UC_ARM_REG_LR,0x6001f000)
  u.emu_start(0x531c9e50,0x6001f000,count=100);self.assertEqual(u.reg_read(r.UC_ARM_REG_R0),1)
 def test_aspect_plan_adds_xpan_using_independent_native_geometry(self):
  from scripts.build_gr4_extensions import prepare_gr4_crops
  p=Patch();args=prepare_gr4_crops(bytes(p.image),True)
  self.assertEqual([x['requested_ratio'] for x in args['crops']],['3:2','4:3','1:1','16:9','65:24'])
  self.assertEqual(args['crops'][-1]['identity']['public_id'],7)
  self.assertEqual(prepare_gr4_crops(bytes(p.image),False),{})
 def test_aspect_compiles_and_reads_back_through_the_real_registry(self):
  from scripts.build_gr4_extensions import prepare_gr4_crops
  from types import SimpleNamespace
  p=Patch();rtos=bytes(p.image);args=prepare_gr4_crops(rtos,True)
  from gr4_editor.filter_reader import read_filters
  from gr4_editor.slots import apply_filter_registry
  from gr4_editor.demo_build import _Patch
  icons=(ROOT/'data/research/gr4/ICONBIN.bin').read_bytes();source=SimpleNamespace(rtos=rtos,icon_bytes=icons,editable=True);filters=read_filters(source)
  compiled,icons,receipt=apply_filter_registry(rtos,icons,filters,filters,**args)
  length=struct.unpack_from('<I',compiled,len(compiled)-8)[0];patch=_Patch(compiled[:-16-length])
  result=apply_extensions(patch,{'aspect':True,'negativeGrain':True,'rawNr':{'mode':'threshold','iso':6400}})
  self.assertTrue(result['aspect']['verified']);self.assertTrue(result['aspect']['raw_recut_complete']);self.assertIn('65:24',result['aspect']['ratios'])
if __name__=='__main__'  :unittest.main()
