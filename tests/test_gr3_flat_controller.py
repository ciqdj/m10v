"""Film-page physical exits through the original GR III BaseController gate."""
import struct,unittest
from tests import test_gr3_settings_controller as adapter
from tests import test_gr3_native_ab_host as host
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_R0

class FlatControllerTests(unittest.TestCase):
 native_host=True
 debug=False
 appended_slots=True
 setUpClass=classmethod(adapter.ControllerLifetimeTests.setUpClass.__func__)
 machine=adapter.ControllerLifetimeTests.machine
 call=adapter.ControllerLifetimeTests.call
 word=staticmethod(adapter.ControllerLifetimeTests.word)
 count=adapter.ControllerLifetimeTests.count
 event=host.NativeHostTests.event
 stock_input_gate=host.NativeHostTests.stock_input_gate
 def begin(self,virtual=True,enabled=0):
  u=host.NativeHostTests.begin(self);self.controller=self.page;self.route=0x0200f100
  self.call(u,'ready',self.page,self.route)
  u.mem_write(self.page+0x238,struct.pack('<I',53))
  u.mem_write(self.page+0x150,struct.pack('<I',0x0200004a))
  self.stock_input_gate(u,enabled)
  from scripts.build_gr3_settings_hooks import BASE_VTABLE
  vt=list(BASE_VTABLE)
  if virtual:vt[0x28//4]=self.externals['m10v_settings_controller_key']
  else:vt[0x28//4]=0x5316c760
  u.mem_write(adapter.STUB+0x800,struct.pack('<'+str(len(vt))+'I',*vt))
  return u
 def physical(self,u,key,phase=1,repeats=1):
  e=self.event(u,key);u.mem_write(e+4,struct.pack('<I',0x55000120));u.mem_write(0x55000120,struct.pack('<II',phase,repeats));return e
 def test_physical_menu_exits_to_native_parent_once(self):
  for enabled in (0,1):
   u=self.begin(enabled=enabled);self.call(u,'ab_dispatch',self.page,self.physical(u,5))
   self.assertEqual([e[1:4] for e in self.events if e[0]=='dispatch'],[(self.page,0x0200004a,0x10000000)])
   self.assertEqual(self.word(u,self.page+0x2f4),0)
 def test_physical_disp_returns_to_shooting_once_after_original_services(self):
  for enabled in (0,1):
   u=self.begin(enabled=enabled);self.call(u,'ab_dispatch',self.page,self.physical(u,4))
   self.assertIn((4,enabled),self.physical_gate)
   self.assertEqual([e[1:4] for e in self.events if e[0]=='dispatch'],[(self.page,0x08000000,0x10000000)])
   self.assertEqual(self.count('m10v_ab_dispatch_original'),1)
   self.assertFalse(self.count('activate_tone'))
 def test_release_hold_repeat_and_foreign_route_do_not_exit(self):
  u=self.begin()
  for key in (4,5):
   for phase,repeats in ((2,0),(2,1),(1,2)):
    self.call(u,'ab_dispatch',self.page,self.physical(u,key,phase,repeats))
  self.assertFalse(self.count('dispatch'))
  self.route=0x02000000
  self.call(u,'ab_dispatch',self.page,self.physical(u,4))
  self.assertFalse(self.count('dispatch'))
 def test_physical_fn_cleanup_is_explicit_and_not_dispatched_twice(self):
  self.fresh_films=[38,34,35,36,37]
  u=self.begin(enabled=1)
  remove=self.externals['m10v_camera_library_remove']
  def removed(m,a,n,_):
   if a==remove:self.fresh_films=[34,35,36,37,0]
   elif a==0x532bd6d4: # Native model bank getter boundary, not cleanup logic.
    m.reg_write(UC_ARM_REG_R0,0);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,removed)
  before=self.count('m10v_settings_view_draw')
  self.call(u,'ab_dispatch',self.page,self.physical(u,0x1b))
  self.assertEqual(self.count('m10v_camera_library_remove'),1)
  self.assertEqual(self.count('m10v_settings_view_draw'),before+1)
  self.assertFalse(self.count('dispatch'))
  self.call(u,'ab_dispatch',self.page,self.physical(u,0x1b,2,0))
  self.assertEqual(self.count('m10v_camera_library_remove'),1)
 def test_original_route_change_prevents_use_of_previous_page(self):
  u=self.begin(virtual=False);original=self.externals['m10v_ab_dispatch_original']
  def change(m,a,n,_):
   if a==original:self.route=0x08000000
  u.hook_add(UC_HOOK_CODE,change)
  self.call(u,'ab_dispatch',self.page,self.physical(u,4))
  self.assertFalse(self.count('dispatch'))
 def test_synthetic_back_alias_still_exits_without_physical_payload(self):
  u=self.begin();self.call(u,'key',self.page,self.event(u,0xda))
  self.assertEqual([e[1:4] for e in self.events if e[0]=='dispatch'],[(self.page,0x0200004a,0x10000000)])
if __name__=='__main__':unittest.main()
