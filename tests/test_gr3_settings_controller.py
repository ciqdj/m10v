"""Execute compiled ARM controller + state and original BaseController lifetime.

Storage, view operations, owner TopMenu construction, factory trampolines and
registration/dispatch are explicit boundary mocks. Base constructor/destructor,
unregister loop and previous-route return execute original firmware instructions.
No camera or full event-loop claim is made.
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
ROOT=Path(__file__).resolve().parents[1]
CODE=0x540c0000
STATE=0x540d0000
STUB=0x540b0000
OWNER=0x10002000
PAGE=OWNER+0x13bc
STRIDE=0x280
VIEW=0x158
SAVED_STATE=VIEW+132
SCREEN=SAVED_STATE+64

class ControllerLifetimeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  p=Path(os.environ.get('M10V_GR3_ORIGINAL_RTOS','/tmp/m10v-sd-research/rtos.bin'))
  if not p.exists():raise unittest.SkipTest('official GR III 2.10 RTOS required')
  cls.firmware=read_firmware(p)
  names=['m10v_settings_factory_original','m10v_settings_top_dtor_original',
         'm10v_settings_controller_vtable','m10v_settings_view_create',
         'm10v_settings_view_draw','m10v_settings_view_destroy',
         'm10v_camera_library_load','m10v_sd_camera_item','m10v_sd_camera_install',
         'm10v_camera_library_stamp']
  cls.externals={n:STUB+i*4 for i,n in enumerate(names)}
  cc=os.environ.get('M10V_LLVM_CLANG') or '/opt/homebrew/opt/llvm/bin/clang'
  if not Path(cc).exists():cc=shutil.which('clang')
  with tempfile.TemporaryDirectory() as d:
   blobs=[]
   for file,addr in [('m10v_settings.c',STATE),('m10v_settings_controller.c',CODE)]:
    obj=Path(d)/'module.o'
    subprocess.run([cc,*FLAGS,'-c',str(ROOT/'native/gr3'/file),'-o',str(obj)],check=True,capture_output=True)
    blob,symbols=link_object(obj.read_bytes(),addr,cls.externals,prefix='m10v_settings_controller_' if 'controller' in file else 'm10v_settings_')
    cls.externals.update(symbols);blobs.append((addr,blob))
   cls.blobs=blobs

 def machine(self):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,n in [(0x53000000,0x2000000),(0x55000000,0x1000000),(0x10000000,0x200000)]:u.mem_map(a,n)
  u.mem_write(0x53000000,self.firmware)
  u.mem_write(0x55000000,self.firmware[0x107b540:0x107b540+0x3a080])
  for a,b in self.blobs:u.mem_write(a,b)
  u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  u.mem_write(0x5536d074,struct.pack('<II',1,struct.unpack_from('<I',self.firmware,0x6b7058)[0]))
  self.events=[];self.executed=set();self.load_fail=False;self.view_fail=False
  self.route=0x0200f100;self.fallback=0x10008000
  reverse={a:n for n,a in self.externals.items() if STUB<=a<STUB+0x100}
  def hook(m,a,n,_):
   self.executed.add(a)
   r=[m.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
   name=reverse.get(a)
   if name:
    self.events.append((name,*r))
    result=0
    if name=='m10v_settings_factory_original':result=OWNER if r[1]==0x0200004a else self.fallback
    elif name=='m10v_settings_top_dtor_original':result=r[0]
    elif name=='m10v_settings_controller_vtable':result=STUB+0x800
    elif name=='m10v_settings_view_create':
     if self.view_fail:result=0xffffffff
     else:m.mem_write(r[0],struct.pack('<I',0x10009000));m.mem_write(r[0]+128,struct.pack('<I',29))
    elif name=='m10v_settings_view_destroy':m.mem_write(r[0],bytes(132))
    elif name=='m10v_camera_library_load':
     result=0xffffffff if self.load_fail else 0
     state=bytearray(64)
     for i in range(5):struct.pack_into('<H',state,12+8*i,33+i)
     m.mem_write(r[0],bytes(state))
    elif name=='m10v_sd_camera_item':result=33+r[0]*8+r[1]
    m.reg_write(UC_ARM_REG_R0,result)
   elif a==0x5319aa68:
    self.events.append(('stock_top_ctor',r[0]));m.mem_write(r[0],bytes(0x13bc))
   elif a==0x5316d354:
    self.events.append(('register',*r));self.assertEqual(self.word(m,r[0]+4),0)
    m.mem_write(r[0]+4,struct.pack('<I',r[2]))
   elif a==0x533abc5c:self.events.append(('unregister',r[0]))
   elif a==0x5316c9d8:self.events.append(('dispatch',*r))
   elif a==0x53228c4c:m.reg_write(UC_ARM_REG_R0,self.route)
   elif a in (0x536af2e4,0x536af358):self.fail('unexpected free of embedded controller/object '+hex(r[0]))
   elif a in (0x536b93d0,0x53820074):self.fail('original assertion '+hex(a))
   else:return
   m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  return u

 @staticmethod
 def word(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def call(self,u,name,*args):
  addr=self.externals['m10v_settings_controller_'+name] if isinstance(name,str) else name
  for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,v)
  u.reg_write(UC_ARM_REG_SP,0x100f0000);u.reg_write(UC_ARM_REG_LR,0x10000000)
  u.emu_start(addr,0x10000000,count=1000000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x10000000)
  self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x100f0000)
  return u.reg_read(UC_ARM_REG_R0)
 def count(self,name):return sum(e[0]==name for e in self.events)
 def setup_owner(self,u):self.call(u,'top_ctor',OWNER)

 def test_embedded_initialization_and_stable_factory_identity(self):
  u=self.machine();self.setup_owner(u)
  self.assertEqual(self.call(u,'owner_size'),0x18bc)
  self.assertIn(0x5316c8d4,self.executed)
  for i,route in enumerate((0x0200f100,0x0200f101)):
   p=PAGE+i*STRIDE
   self.assertEqual(self.word(u,p),STUB+0x800)
   self.assertEqual(self.word(u,p+0x150),0x10000000)
   for _ in range(3):self.assertEqual(self.call(u,'factory',0x55123400,route),p)
  for route in (0x0200004e,0x08000000,0x0200ffff):
   self.assertEqual(self.call(u,'factory',0x55123400,route),self.fallback)
   self.assertEqual(self.events[-1][:3],('m10v_settings_factory_original',0x55123400,route))

 def test_ready_denies_storage_and_view_failure(self):
  u=self.machine();self.setup_owner(u)
  self.load_fail=True
  self.assertEqual(self.call(u,'ready',PAGE,0x0200f100),0)
  self.assertEqual(self.count('m10v_settings_view_create'),0)
  self.load_fail=False;self.view_fail=True
  self.assertEqual(self.call(u,'ready',PAGE,0x0200f100),0)
  self.assertEqual(self.count('register'),0)
  self.view_fail=False
  self.assertEqual(self.call(u,'ready',PAGE,0x0200f100),1)

 def test_cached_view_reentry_reuses_widgets_and_unregisters(self):
  u=self.machine();self.setup_owner(u)
  for cycle in range(3):
   self.assertEqual(self.call(u,'ready',PAGE,0x0200f100),1)
   self.call(u,'enter',PAGE,0x0200f100,0)
   self.assertEqual(self.word(u,PAGE+4),0x10009000)
   self.call(u,0x5316ce8c,PAGE)
   self.assertEqual(self.word(u,PAGE+4),0)
  self.assertEqual(self.count('m10v_settings_view_create'),1)
  self.assertEqual(self.count('register'),3);self.assertEqual(self.count('unregister'),3)

 def test_return_key_preserves_previous_route_and_actual_return_routine(self):
  u=self.machine();self.setup_owner(u);self.call(u,'ready',PAGE,0x0200f100)
  u.mem_write(PAGE+0x150,struct.pack('<I',0x0200004a));u.mem_write(0x10000100,struct.pack('<H',0x86))
  self.call(u,'key',PAGE,0x10000100)
  self.assertEqual(self.word(u,PAGE+SCREEN),0)
  self.assertIn(0x5316ca28,self.executed)
  self.assertIn(('dispatch',PAGE,0x0200004a,0x10000000),[e[:4] for e in self.events])
  self.assertEqual(self.word(u,PAGE+0x150),0x0200004a)

 def test_destruction_unregisters_before_view_and_never_frees_tail(self):
  u=self.machine();self.setup_owner(u);self.call(u,'ready',PAGE,0x0200f100);self.call(u,'enter',PAGE,0,0)
  self.call(u,'top_dtor',OWNER)
  self.assertIn(0x5316c774,self.executed)
  self.assertEqual(self.count('m10v_settings_view_destroy'),2)
  names=[e[0] for e in self.events]
  self.assertLess(names.index('unregister'),names.index('m10v_settings_view_destroy'))
  self.assertEqual(names[-1],'m10v_settings_top_dtor_original')

 def test_recognized_keys_stop_base_event_propagation(self):
  u=self.machine();self.setup_owner(u);self.call(u,'ready',PAGE,0x0200f100)
  # BaseController5316d8c8 falls through to a shared model when handler returns0.
  for event in (0xd0,0xd1,0xce,0xcf,0xd4,0xd5):
   u.mem_write(0x10000100,struct.pack('<H',event))
   self.assertEqual(self.call(u,'key',PAGE,0x10000100),1,
                    'recognized key must be consumed before shared model fallback')
  u.mem_write(0x10000100,struct.pack('<H',0xffff))
  self.assertEqual(self.call(u,'key',PAGE,0x10000100),0)

 def test_actual_base_dispatch_tail_consumes_back_and_navigation(self):
  u=self.machine();self.setup_owner(u)
  u.mem_write(STUB+0x800+0x28,struct.pack('<I',self.externals['m10v_settings_controller_key']))
  u.mem_write(PAGE+0x150,struct.pack('<I',0x0200004a))
  for event in (0xd0,0xd1,0xce,0xcf,0x86):
   self.call(u,'ready',PAGE,0x0200f100)
   u.mem_write(0x10000100,struct.pack('<H',event))
   u.reg_write(UC_ARM_REG_R4,0x10000100)
   u.reg_write(UC_ARM_REG_R5,0x55012300)
   u.reg_write(UC_ARM_REG_R7,PAGE)
   u.reg_write(UC_ARM_REG_SP,0x100f0000)
   self.executed.clear()
   # Execute the original virtual+28 dispatch and consumption branch; stop at
   # its shared return label before restoring the outer (not entered) frame.
   u.emu_start(0x5316d7ec,0x5316d81c,count=100000)
   self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x5316d81c)
   self.assertIn(0x5316d8c4,self.executed)
   self.assertNotIn(0x5316d804,self.executed)
   self.assertNotIn(0x5320b79c,self.executed)

 def test_key_alias_only_translates_private_route_return_value(self):
  u=self.machine()
  for route in (0x0200f100,0x0200f101,0x0200004e,0x08000000,0x0200ffff):
   self.route=route
   self.assertEqual(self.call(u,'key_route',0x55012300),0x0200004a if route in (0x0200f100,0x0200f101) else route)
   self.assertEqual(self.route,route)

if __name__=='__main__':unittest.main()
