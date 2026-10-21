"""Compiled ARM native-host adapter. Native UI APIs are explicit boundaries;
this validates ownership/order/route contracts, not LCD or physical power-off."""
import struct
from tests import test_gr3_settings_controller as adapter
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

class NativeHostTests(adapter.ControllerLifetimeTests):
 native_host=True
 debug=True
 def begin(self):
  u=self.machine();self.owner=0x55040000;self.page=self.owner+0x13bc;self.stock_owner=self.owner
  self.call(u,'top_ctor',self.owner)
  u.mem_write(0x55063910,struct.pack('<I',1));u.mem_write(0x55063988,struct.pack('<I',self.owner))
  u.mem_write(0x55008000+0x1b,bytes(5))
  self.controller=0x55050000;self.list=0x55060000;self.ui=[]
  u.mem_write(self.controller,struct.pack('<I',0x53b394e0))
  for off,value in [(0x124,0x02000000),(4,0x55061000),(0x15c,0x55061000),(0x160,0x55062000),(0x164,0x55063000),(0x168,0x55064000),(0x1ac,0x55065000),(0x1f0,self.list),(0x150,0x02000012)]:u.mem_write(self.controller+off,struct.pack('<I',value))
  u.mem_write(self.list,struct.pack('<I',0x55066000));u.mem_write(0x55066018,struct.pack('<I',0x55067000));u.mem_write(0x55067000,bytes.fromhex('1eff2fe1'))
  def boundary(m,a,n,_):
   r=[m.reg_read(v) for v in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
   if a==0x533947f0:m.mem_write(r[1],struct.pack('<I',7));m.mem_write(r[2],struct.pack('<I',9));v=0
   elif a==0x53394758:v=0x55070000+r[1]*0x200
   elif a==0x533948c4:v=300
   elif a in (0x53394e8c,0x533a1808,0x533a1734,0x533a18e0,0x533a19b4,0x53395430,0x53395260,0x53396f80,0x533ad3c0,0x533ad308,0x53395224):self.ui.append((a,*r));v=0
   elif a==0x531a2820:v=getattr(self,'adj_type',12)
   else:return
   m.reg_write(UC_ARM_REG_R0,v);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,boundary);self.route=0x02000000
  return u
 def event(self,u,key):
  u.mem_write(0x10000100,struct.pack('<HHI',key,0,0x10000120));u.mem_write(0x10000120,struct.pack('<II',2,0))
  return 0x10000100
 def test_adj_activates_existing_list_without_navigation_or_tone_change(self):
  u=self.begin();self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  self.assertFalse(self.count('dispatch'))
  self.assertTrue(any(e[0]==0x53394e8c and e[1:3]==(self.list,3) for e in self.ui))
  self.assertFalse(self.count('activate_tone'))
 def test_menu_uses_native_adj_route_and_original_parent(self):
  u=self.begin();self.route=0x02000012;source=0x55051000
  self.call(u,'ab_setup',source,self.event(u,0x37),self.route)
  self.assertTrue(any(e[0]=='dispatch' and e[1:4]==(source,0x02000000,0x02000012) for e in self.events))
  self.assertFalse(any(e[0]=='dispatch' and e[2]==0x0200f104 for e in self.events))
  self.route=0x02000000;self.call(u,'ab_adj_refresh',self.controller)
  self.assertTrue(any(e[0]==0x53394e8c for e in self.ui))
 def test_exit_restores_list_before_original_exit_and_destroy_does_not_refresh(self):
  u=self.begin();self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  self.call(u,'ab_adj_exit',self.controller)
  self.assertTrue(any(e[0]==0x53395224 and e[1:]==(self.list,7,9) for e in self.ui))
  self.assertEqual(self.count('m10v_ab_adj_exit_original'),1)
  self.call(u,'ab_setup',self.controller,self.event(u,0x36),self.route)
  self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  before=self.count('m10v_ab_adj_refresh_original');self.call(u,'ab_adj_destroy',self.controller)
  self.assertEqual(self.count('m10v_ab_adj_refresh_original'),before)
  self.assertEqual(self.count('m10v_ab_adj_destroy_original'),1)
 def test_power_passes_original_without_navigation_and_private_callbacks_dont_apply(self):
  u=self.begin();self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  self.call(u,'ab_adj_changed',self.controller)
  self.assertEqual(self.count('m10v_ab_adj_changed_original'),0)
  self.call(u,'ab_adj_event',self.controller,self.event(u,1))
  self.assertEqual(self.count('m10v_ab_adj_event_original'),1)
  self.assertFalse(self.count('dispatch'));self.assertFalse(self.count('activate_tone'))
 def test_foreign_callbacks_and_refresh_do_not_take_active_host(self):
  u=self.begin();self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  other=self.controller+0x1000
  self.call(u,'ab_adj_changed',other)
  self.assertEqual(self.count('m10v_ab_adj_changed_original'),1)
  before=len(self.ui);self.call(u,'ab_adj_refresh',other)
  self.assertEqual(len(self.ui),before)
  self.call(u,'ab_adj_destroy',other)
  self.call(u,'ab_adj_changed',self.controller)
  self.assertEqual(self.count('m10v_ab_adj_changed_original'),1)
 def test_menu_back_returns_native_parent_and_swallows_duplicate_confirm(self):
  u=self.begin();source=0x55051000;self.route=0x02000012
  self.call(u,'ab_setup',source,self.event(u,0x37),self.route)
  self.route=0x02000000;self.call(u,'ab_adj_refresh',self.controller)
  self.call(u,'ab_adj_event',self.controller,self.event(u,5))
  self.assertTrue(any(e[0]=='dispatch' and e[1:4]==(self.controller,0x02000012,0x10000000) for e in self.events))
  self.assertEqual(self.word(u,self.controller+0x154)&255,1)
  self.route=0x02000012
  self.assertEqual(self.call(u,'ab_setup',source,self.event(u,0xd8),self.route),1)
  self.assertEqual(self.call(u,'ab_setup',source,self.event(u,8),self.route),0)
  self.assertEqual(self.call(u,'ab_setup',source,self.event(u,0xd8),self.route),0)
  self.assertFalse(self.count('activate_tone'))
 def test_reentry_after_exit_and_fn_remains_original(self):
  u=self.begin()
  for _ in range(3):
   self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
   self.call(u,'ab_adj_event',self.controller,self.event(u,0x1b))
   self.call(u,'ab_setup',self.controller,self.event(u,0x36),self.route)
  self.assertEqual(self.count('m10v_ab_adj_event_original'),3)
  self.assertEqual(sum(e[0]==0x53395224 for e in self.ui),3)
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.count('dispatch'))
 def test_canvas_uses_owned_root_even_when_registration_slot_is_empty(self):
  u=self.begin();root=0x55068000
  u.mem_write(self.controller+4,bytes(4));u.mem_write(self.controller+0x15c,struct.pack('<I',root))
  self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  self.assertTrue(any(e[0]==0x533ad308 and e[1]==root for e in self.ui))
 def test_pending_menu_attaches_while_global_route_still_reports_source(self):
  u=self.begin();self.route=0x02000012;source=0x55051000
  u.mem_write(self.controller+0x124,struct.pack('<I',0x02000000))
  self.call(u,'ab_setup',source,self.event(u,0x37),self.route)
  self.call(u,'ab_adj_refresh',self.controller)
  self.assertTrue(any(e[0]==0x53394e8c for e in self.ui))
 def stock_input_gate(self,u,enabled=0):
  # Execute original BaseController filtering, including 5316ccf8/5323bc4c.
  # Models/other UI services are boundaries; the physical press gate is real.
  self.real_dispatch=True;keyboard=0x55078000;other=0x5507a000;vt=0x5507c000;noop=0x5507d000
  u.mem_write(noop,bytes.fromhex('0000a0e31eff2fe1'))
  u.mem_write(vt,struct.pack('<16I',*([noop]*16)))
  for at in (keyboard,other):u.mem_write(at,struct.pack('<I',vt))
  u.mem_write(keyboard+0x520,bytes([enabled]));u.mem_write(self.controller+0x124,struct.pack('<I',self.route))
  self.physical_gate=[]
  getters={0x5320b19c,0x5320b73c,0x5320b8bc,0x5320b13c,0x5320b3dc,0x5320b07c,0x5320ae3c,0x5320bcdc,0x5320c03c,0x5320c120,0x5320addc,0x5320b79c,0x5320af5c}
  callbacks={0x53229464,0x5322ae44,0x532b2618,0x5322ce9c,0x532ae708}
  def services(m,a,n,_):
   if a==0x5323bc4c:self.physical_gate.append((m.reg_read(UC_ARM_REG_R1),bytes(m.mem_read(keyboard+0x520,1))[0]));return
   if a==0x5320b1fc:v=keyboard
   elif a in getters:v=other
   elif a in callbacks:v=0
   else:return
   m.reg_write(UC_ARM_REG_R0,v);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,services)
 def physical(self,u,phase=1,repeats=1):
  e=self.event(u,4);u.mem_write(e+4,struct.pack('<I',0x55000120));u.mem_write(0x55000120,struct.pack('<II',phase,repeats));return e
 def test_physical_disp_after_original_press_gate_is_filtered(self):
  u=self.begin();self.stock_input_gate(u)
  entry=self.externals.get('m10v_settings_controller_ab_dispatch',0x5316d5dc)
  self.call(u,entry,self.controller,self.physical(u))
  self.assertIn((4,0),self.physical_gate)
  self.assertTrue(any(e[0]==0x53394e8c for e in self.ui))
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.count('dispatch'))
 def test_filtered_release_and_hold_do_not_open_and_non_ic_remains_original(self):
  u=self.begin();self.stock_input_gate(u)
  entry=self.externals.get('m10v_settings_controller_ab_dispatch',0x5316d5dc)
  self.call(u,entry,self.controller,self.physical(u,2,0))
  self.call(u,entry,self.controller,self.physical(u,2,1))
  self.assertFalse(self.ui)
  self.adj_type=8
  self.call(u,entry,self.controller,self.physical(u))
  self.assertFalse(self.ui)
 def test_failed_native_attachment_does_not_open_on_a_later_refresh(self):
  u=self.begin();self.route=0x02000012
  self.call(u,'ab_setup',0x55051000,self.event(u,0x37),self.route)
  u.mem_write(self.controller+0x15c,bytes(4));self.call(u,'ab_adj_refresh',self.controller)
  u.mem_write(self.controller+0x15c,struct.pack('<I',0x55061000));self.route=0x02000000
  self.call(u,'ab_adj_refresh',self.controller)
  self.assertFalse(self.ui)
 def test_dispatch_other_buttons_and_other_controller_keep_original(self):
  u=self.begin()
  for key in (1,0x1b,0xd0,0xd8):self.call(u,'ab_dispatch',self.controller,self.event(u,key))
  self.call(u,'ab_dispatch',self.controller+0x1000,self.physical(u))
  self.assertEqual(self.count('m10v_ab_dispatch_original'),5)
  self.assertFalse(self.ui);self.assertFalse(self.count('dispatch'))
 def test_invalid_direct_adj_attach_leaves_no_deferred_open(self):
  u=self.begin();u.mem_write(self.controller+0x15c,bytes(4))
  self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
  u.mem_write(self.controller+0x15c,struct.pack('<I',0x55061000))
  self.call(u,'ab_adj_refresh',self.controller)
  self.assertFalse(self.ui)
