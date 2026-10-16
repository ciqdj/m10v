"""Unintegrated view: execute actual GR III 2.10 constructors/setters/destructors.
Allocator/free leaves are replaced; initialized firmware singleton state is seeded.
No framebuffer, controller routing or hardware validation is implied.
"""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from scripts.build_gr3_m10v_library import FLAGS, link_object
from scripts.analyze_gr3_settings import read_firmware
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ROOT = Path(__file__).resolve().parents[1]
BASE=0x540c0000
class SettingsViewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  path=Path(os.environ.get('M10V_GR3_ORIGINAL_RTOS','/tmp/m10v-sd-research/rtos.bin'))
  if not path.exists():raise unittest.SkipTest('official GR III 2.10 RTOS required')
  cls.firmware=read_firmware(path)
  cc=os.environ.get('M10V_LLVM_CLANG') or '/opt/homebrew/opt/llvm/bin/clang'
  if not Path(cc).exists():cc=shutil.which('clang')
  with tempfile.TemporaryDirectory() as d:
   obj=Path(d)/'view.o'
   subprocess.run([cc,*FLAGS,'-c',str(ROOT/'native/gr3/m10v_settings_view.c'),'-o',str(obj)],check=True,capture_output=True)
   cls.code,cls.symbols=link_object(obj.read_bytes(),BASE,{'m10v_library_name':0x540b0000},prefix='m10v_settings_view_')
 def machine(self,fail_object=0):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr,size in [(0x53000000,0x2000000),(0x55000000,0x1000000),(0x10000000,0x200000)]:u.mem_map(addr,size)
  u.mem_write(0x53000000,self.firmware);u.mem_write(BASE,self.code)
  u.mem_write(0x55000000,self.firmware[0x107b540:0x107b540+0x3a080])
  u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  for address in (0x5536d074,0x55063d80,0x55063ed0):u.mem_write(address,struct.pack('<I',1))
  u.mem_write(0x5536d078,self.firmware[0x6b7058:0x6b705c])
  u.mem_write(0x55063f34,struct.pack('<I',0x55100000));u.mem_write(0x551009ba,b'\x14')
  self.heap=0x10100000;self.live={};self.object_count=0;self.executed=set()
  # Catalog-name provider stub only; stock view APIs execute unchanged.
  u.mem_write(0x10000800,b'PORTRA\0')
  def hook(uc,a,n,_):
   self.executed.add(a)
   if a in (0x536af2a8,0x536af31c):
    size=uc.reg_read(UC_ARM_REG_R0)
    if size in (0xf0,0xf8,0x110):self.object_count+=1
    if fail_object and self.object_count==fail_object and size in (0xf0,0xf8,0x110):p=0
    else:
     p=self.heap;self.heap+=(size+15)&~15;self.live[p]=size
    uc.reg_write(UC_ARM_REG_R0,p)
   elif a in (0x536af2e4,0x536af358):
    p=uc.reg_read(UC_ARM_REG_R0)
    if p:self.assertIn(p,self.live);del self.live[p]
   elif a==0x540b0000:uc.reg_write(UC_ARM_REG_R0,0x10000800)
   elif a==0x540b0010:
    index=uc.reg_read(UC_ARM_REG_R1);uc.reg_write(UC_ARM_REG_R0,33+index if index<7 else 0)
   elif a in (0x536b93d0,0x53820074):self.fail('original assertion '+hex(a))
   else:return
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);return u
 def call(self,u,name,*args):
  for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,value)
  u.reg_write(UC_ARM_REG_SP,0x100f0000);u.reg_write(UC_ARM_REG_LR,0x10000000)
  u.emu_start(self.symbols['m10v_settings_view_'+name],0x10000000,count=1000000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x10000000);self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x100f0000)
  return u.reg_read(UC_ARM_REG_R0)
 def state(self,u,screen=1,focus=2):
  s=bytearray(96)
  for i in range(5):struct.pack_into('<H',s,12+8*i,33+i)
  s[52:56]=bytes([1,2,3,0]);struct.pack_into('<8I',s,64,screen,focus,0,0,0,1,0,0)
  u.mem_write(0x10002000,bytes(s))
 def widgets(self,u):return struct.unpack('<40I',u.mem_read(0x10001000,160))
 def test_original_tree_film_selection_and_teardown(self):
  u=self.machine();self.assertEqual(self.call(u,'create',0x10001000),0)
  w=self.widgets(u);self.assertEqual(struct.unpack('<I',u.mem_read(0x100010a0,4))[0],37)
  for p in w[1:37]:self.assertEqual(struct.unpack('<I',u.mem_read(p+4,4))[0],w[0])
  self.state(u);self.call(u,'draw',0x10001000,0x10002000,0)
  self.assertEqual([u.mem_read(w[6+i]+0xea,1)[0] for i in range(5)],[1,1,6,1,1])
  self.assertEqual([struct.unpack('<H',u.mem_read(w[16+i]+0xea,2))[0] for i in range(5)],[703,704,705,706,707])
  p=struct.unpack('<I',u.mem_read(w[3]+0xf0,4))[0];self.assertEqual(bytes(u.mem_read(p,28)),'3 / 5  PORTRA\0'.encode('utf-16le'))
  self.assertEqual(struct.unpack('<H',u.mem_read(w[2]+0xea,2))[0],915)
  self.call(u,'destroy',0x10001000);self.assertFalse(self.live)
  for a in (0x5339199c,0x53393d84,0x5339a908,0x53396944,0x53390ca0,0x53390ef8,0x5339a9a0,0x53396f80,0x5316cde8):self.assertIn(a,self.executed)
 def test_original_stamp_rows_and_value_preview(self):
  u=self.machine();self.call(u,'create',0x10001000);w=self.widgets(u)
  self.state(u,3,2);self.call(u,'draw',0x10001000,0x10002000,0)
  self.assertEqual([u.mem_read(w[29+i]+0xee,1)[0] for i in range(4)],[31,31,10,31])
  self.assertEqual([u.mem_read(w[16+i]+0x9e,1)[0] for i in range(5)],[0]*5)
  self.assertEqual([struct.unpack('<H',u.mem_read(w[33+i]+0xea,2))[0] for i in range(4)],[929,933,938,939])
  self.assertEqual([u.mem_read(w[21+i]+0x9e,1)[0] for i in range(4)],[0,0,1,0])
  self.assertEqual([u.mem_read(w[25+i]+0x9e,1)[0] for i in range(4)],[0,0,1,0])
  self.state(u,4,2);self.call(u,'draw',0x10001000,0x10002000,0)
  self.assertEqual(struct.unpack('<H',u.mem_read(w[35]+0xea,2))[0],936)
  self.assertEqual(struct.unpack('<H',u.mem_read(w[2]+0xea,2))[0],945)
  self.assertEqual([u.mem_read(w[29+i]+0xee,1)[0] for i in range(4)],[31]*4)
  self.assertEqual([u.mem_read(w[33+i]+0xee,1)[0] for i in range(4)],[31,31,10,31])
  self.call(u,'destroy',0x10001000);self.assertFalse(self.live)
 def test_each_top_level_allocation_failure_cleans_partial_tree(self):
  for failure in range(1,38):
   with self.subTest(failure=failure):
    u=self.machine(failure);self.assertEqual(self.call(u,'create',0x10001000),0xffffffff)
    self.assertFalse(self.live);self.assertEqual(bytes(u.mem_read(0x10001000,164)),bytes(164))
 def test_actual_glyph_palette_branch_distinguishes_yellow_from_white(self):
  u=self.machine();descriptor=0x10003000
  for style,table,pixel in [(6,0x53b4dbec,0xffffffff),(31,0x53b4dbec,0xffffffff),(10,0x53b4dc6c,0xff00e1ff)]:
   u.mem_write(descriptor+0x25,bytes([style]));u.reg_write(UC_ARM_REG_R7,descriptor)
   u.emu_start(0x53208fec,0x53209018,count=32)
   self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x53209018)
   self.assertEqual(u.reg_read(UC_ARM_REG_R10),table)
   self.assertEqual(struct.unpack('<I',u.mem_read(table+60,4))[0],pixel)
 def test_every_stamp_row_has_one_visible_frame_and_films_clear_all_rows(self):
  u=self.machine();self.call(u,'create',0x10001000);w=self.widgets(u)
  for focus in range(4):
   self.state(u,3,focus);self.call(u,'draw',0x10001000,0x10002000,0)
   self.assertEqual([u.mem_read(w[21+i]+0x9e,1)[0] for i in range(4)],[int(i==focus) for i in range(4)])
   self.assertEqual([u.mem_read(w[21+i]+0xea,1)[0] for i in range(4)],[6]*4)
   self.assertEqual([u.mem_read(w[6+i]+0x9e,1)[0] for i in range(5)],[0]*5)
  self.state(u,1,4);self.call(u,'draw',0x10001000,0x10002000,0)
  self.assertEqual([u.mem_read(w[21+i]+0x9e,1)[0] for i in range(4)],[0]*4)
  self.assertEqual([u.mem_read(w[6+i]+0xea,1)[0] for i in range(5)],[1,1,1,1,6])
  outer=struct.unpack('<4I',u.mem_read(w[6]+0x20,16));inner=struct.unpack('<4I',u.mem_read(w[11]+0x20,16))
  self.assertEqual(outer,(24,150,128,128));self.assertEqual(inner,(32,158,112,112))
  self.assertEqual(struct.unpack('<4I',u.mem_read(w[16]+0x20,16)),inner)
 def test_catalog_highlights_actual_index_and_hides_empty_last_page_entries(self):
  u=self.machine();self.call(u,'create',0x10001000);w=self.widgets(u);self.state(u,2,4)
  u.mem_write(0x10002000+76,struct.pack('<I',6))
  u.mem_write(0x10003000,struct.pack('<5I',0,0,0x540b0010,0,0))
  self.call(u,'draw',0x10001000,0x10002000,0x10003000)
  self.assertEqual([u.mem_read(w[6+i]+0xea,1)[0] for i in range(5)],[1,6,1,1,1])
  self.assertEqual([u.mem_read(w[16+i]+0x9e,1)[0] for i in range(5)],[1,1,0,0,0])
  self.assertEqual(struct.unpack('<H',u.mem_read(w[2]+0xea,2))[0],947)
  p=struct.unpack('<I',u.mem_read(w[3]+0xf0,4))[0]
  self.assertEqual(bytes(u.mem_read(p,20)),'7  PORTRA\0'.encode('utf-16le'))

if __name__=='__main__':unittest.main()
