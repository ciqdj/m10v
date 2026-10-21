"""A/B interaction: independent slots, DISP debounce, cancellation and failure."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from tests import test_gr3_settings_controller as adapter
import struct
import zlib


class ABAdapterTests(adapter.ControllerLifetimeTests):
 debug=True
 def test_ab_page_leaves_physical_main_switch_to_native_power_handling(self):
  u=self.begin();self.call(u,'ready',self.page,0x0200f104)
  event=0x10000100;payload=0x10000120
  u.mem_write(event,struct.pack('<HHI',1,0,payload)) # EVT_SWITCH_MAIN
  u.mem_write(payload,struct.pack('<II',1,0))
  before=self.count('dispatch')
  self.assertEqual(self.call(u,'key',self.page,event),0)
  self.assertEqual(self.count('dispatch'),before) # no competing page navigation

 def test_ab_ready_matches_stock_imagecontrol_lifecycle_and_safe_submit_gate(self):
  from unicorn import UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR
  u=self.begin();self.call(u,'ready',self.page,0x0200f104)
  native=self.page+adapter.STRIDE
  u.mem_write(native+0x124,struct.pack('<I',0x02000012))
  self.call(u,0x531ab0f8,native,native+0x124)
  self.call(u,0x531ab160,native,native+0x124,0)
  for offset in (0x12b,0x137):
   self.assertEqual(bytes(u.mem_read(self.page+offset,1)),bytes(u.mem_read(native+offset,1)))
  u.mem_write(self.page+4,struct.pack('<I',0x55060000));submitted=[];gates=[]
  def boundary(m,a,n,_):
   r=[m.reg_read(x) for x in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
   if a in (0x5320b19c,0x5320b13c):v=0x55062000
   elif a==0x53237520:gates.append(a);v=1 # native transition is ready
   elif a==0x532334d0:v=1
   elif a in (0x53233e20,0x53233bc0):submitted.append((a,*r));v=0
   else:return
   m.reg_write(UC_ARM_REG_R0,v);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,boundary)
  self.call(u,0x5316cf18,self.page) # unchanged original display-submit routine
  self.assertEqual([e[0] for e in submitted],[0x53233e20,0x53233bc0])
  self.assertEqual(len(gates),1) # shooting mode0 checks readiness; mode2 bypasses it
  self.assertEqual(bytes(u.mem_read(self.page+0x12b,1)),b'\0')
  self.assertEqual(bytes(u.mem_read(self.page+0x137,1)),b'\0')
  # Reusing the owner for Setup retains that page's established defaults.
  self.call(u,'ready',self.page,0x0200f100)
  self.assertEqual(bytes(u.mem_read(self.page+0x12b,1)),b'\2')
  self.assertEqual(bytes(u.mem_read(self.page+0x137,1)),b'\2')

 def test_pending_setup_consumes_only_its_sources_stale_a1(self):
  u=self.begin();self.route=0x02000012;event=0x10000100;source=0x55050000
  u.mem_write(event,struct.pack('<H',0xa1))
  self.assertEqual(self.call(u,'ab_setup',source,event,self.route),0)
  u.mem_write(event,struct.pack('<H',0x37))
  self.assertEqual(self.call(u,'ab_setup',source,event,self.route),1)
  u.mem_write(event,struct.pack('<H',0xa1))
  self.assertEqual(self.call(u,'ab_setup',source+4,event,self.route),0)
  self.assertEqual(self.call(u,'ab_setup',source,event,self.route),1)
  self.assertEqual(self.call(u,'ab_setup',source,event,self.route),0)
  u.mem_write(event,struct.pack('<H',0x36));self.call(u,'ab_setup',source,event,self.route)
  u.mem_write(event,struct.pack('<H',0x37));self.call(u,'ab_setup',source,event,self.route)
  self.call(u,'ready',self.page,0x0200f104)
  u.mem_write(event,struct.pack('<H',0xa1))
  self.assertEqual(self.call(u,'ab_setup',source,event,self.route),0)

 def test_failed_ready_clears_pending_exit_protection(self):
  u=self.begin();self.route=0x02000012;event=0x10000100;source=0x55050000
  u.mem_write(event,struct.pack('<H',0x37));self.call(u,'ab_setup',source,event,self.route)
  self.load_fail=True;self.assertEqual(self.call(u,'ready',self.page,0x0200f104),0)
  u.mem_write(event,struct.pack('<H',0xa1))
  self.assertEqual(self.call(u,'ab_setup',source,event,self.route),0)

 def test_display_trace_observes_remapped_slot_and_preserves_stock_draw(self):
  from unicorn import UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
  u=self.begin();self.call(u,'ready',self.page,0x0200f104)
  root=0x55060000
  u.mem_write(self.page+3*0x30+4,struct.pack('<I',root))
  u.mem_write(root+0xa0,b'\1\0\1');u.mem_write(root+0xec,struct.pack('<I',0x55061000))
  calls=[];busy=[1]
  def service(m,a,n,_):
   if a==0x5320b13c:v=0x55062000
   elif a==0x53233574:v=busy[0]
   elif a==0x532334d0:v=1
   elif a==0x5316d0f0:calls.append(m.reg_read(UC_ARM_REG_R0));v=0xabc123
   else:return
   m.reg_write(UC_ARM_REG_R0,v);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,service)
  self.call(u,'ab_render',self.page)
  busy[0]=0;self.call(u,'ab_render',self.page)
  count=len(self.events);self.call(u,'ab_render',self.page)
  self.assertEqual(len(self.events),count) # bounded, never floods SD each frame
  self.assertEqual(calls,[self.page]*3)
  logs=[e for e in self.events if e[0]=='m10v_debug_log' and e[1]==97]
  self.assertTrue(any(e[2]==4 and e[3]==root and e[4]==0x0102 for e in logs))
  self.assertTrue(any(e[2]==8 and e[3]==1 for e in logs))
  self.assertTrue(any(e[2]==8 and e[3]==0 for e in logs))

 def begin(self):
  u=self.machine();self.owner=0x55040000;self.page=self.owner+0x13bc;self.stock_owner=self.owner
  self.call(u,'top_ctor',self.owner)
  u.mem_write(0x55063910,struct.pack('<I',1));u.mem_write(0x55063988,struct.pack('<I',self.owner))
  self.call(u,'ready',self.page,0x0200f100)
  u.mem_write(0x55008000+0x1b,bytes(5)) # initialized shooting ImageControl model
  return u

 def key(self,u,k):
  u.mem_write(0x10000100,struct.pack('<H',k));return self.call(u,'key',self.page,0x10000100)

 def test_disp_pair_setup_switch_and_stock_fn(self):
  u=self.begin();self.key(u,0xa2)
  self.assertEqual(self.word(u,self.page+adapter.SCREEN),1) # real stock event is untouched
  self.route=0x02000012
  self.call(u,'ab_selector',0,0x37)
  self.assertTrue(any(e[0]=='dispatch' and e[2]==0x0200f104 for e in self.events))
  self.call(u,'ready',self.page,0x0200f104)
  self.assertEqual(self.word(u,self.page+adapter.SCREEN),6)
  self.key(u,0xd1);self.key(u,0xd1);self.key(u,0xd8)
  self.assertEqual(self.word(u,self.page+adapter.SCREEN),0)
  record=self.ab_files['M10VAB1.BIN']
  self.assertEqual(struct.unpack('<6I',record)[:5],(0x3142414d,2,1,1281,0))
  self.assertEqual(struct.unpack_from('<I',record,20)[0],zlib.crc32(record[:20]))
  self.route=0x08000000
  self.call(u,'ab_mapper',0,0x37);self.assertEqual(self.ab_tone,16)
  self.call(u,'ab_mapper',0,0x37);self.call(u,'ab_mapper',0,0x38);self.assertEqual(self.ab_tone,16)
  self.call(u,'ab_mapper',0,0x36);self.call(u,'ab_mapper',0,0x37);self.assertEqual(self.ab_tone,12)
  # Every other logical key (including custom Fn/crop) uses the original mapper.
  before=self.count('m10v_ab_mapper_original')
  for k in range(1,65):
   if k not in (0x36,0x37,0x38):self.call(u,'ab_mapper',0,k)
  self.assertEqual(self.count('m10v_ab_mapper_original'),before+61)
  self.route=0x08000001
  before=self.count('m10v_ab_mapper_original');self.call(u,'ab_mapper',0,0x37)
  self.assertEqual(self.count('m10v_ab_mapper_original'),before+1);self.assertEqual(self.ab_tone,12)
  # Freshly constructed owner has no active session, while pair journal survives.
  self.call(u,'top_ctor',self.owner);self.call(u,'ab_mapper',0,0x37);self.assertEqual(self.ab_tone,12)

 def test_live_controller_event_switches_without_global_mapper(self):
  u=self.begin();self.call(u,'ready',self.page,0x0200f104)
  self.key(u,0xd1);self.key(u,0xd1);self.key(u,0xd8);self.route=0x08000000
  event=0x10000100
  for key,expected in [(0x37,16),(0x37,16),(0x38,16),(0x36,16),(0x37,12)]:
   u.mem_write(event,struct.pack('<H',key));self.call(u,'ab_live_event',0x55050000,event)
   self.assertEqual(self.ab_tone,expected)
  before=self.count('m10v_ab_live_event_original')
  for key in [0xa2,0x1,0x2,0x86,0x100]:
   u.mem_write(event,struct.pack('<H',key));self.call(u,'ab_live_event',0x55050000,event)
  self.assertEqual(self.count('m10v_ab_live_event_original'),before+5)

 def test_controller_raw_and_logical_disp_open_once_and_keep_parent(self):
  u=self.begin();self.route=0x02000012;event=0x10000100;payload=0x55010000
  u.mem_write(event,struct.pack('<HHI',4,0,payload));u.mem_write(payload,struct.pack('<II',1,1))
  self.assertEqual(self.call(u,'ab_setup',0x55050000,event,0x02000012),1)
  u.mem_write(event,struct.pack('<HHI',0x37,0,0))
  self.call(u,'ab_selector',0,0x37) # alternate global dispatch must share debounce
  self.call(u,'ab_setup',0x55050000,event,0x02000012)
  self.assertEqual(self.count('dispatch'),1)
  u.mem_write(event,struct.pack('<H',0x36));self.call(u,'ab_setup',0x55050000,event,0x02000012)
  u.mem_write(event,struct.pack('<H',0x37));self.call(u,'ab_setup',0x55050000,event,0x02000012)
  self.assertEqual(self.count('dispatch'),2)
  u.mem_write(0x55008000+0x1b,b'\1');self.call(u,'ab_setup',0x55050000,event,0x02000012)
  self.assertEqual(self.count('dispatch'),2)

 def test_adj_uses_actual_configured_item_getter_and_keeps_adj_parent(self):
  from unicorn import UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC,UC_ARM_REG_LR
  u=self.begin();self.route=0x02000000;controller=0x55050000;event=0x10000100
  u.mem_write(controller,struct.pack('<I',0x53b394e0));u.mem_write(controller+0x1f4,b'\x02')
  u.mem_write(0x55009004,struct.pack('<I',0x5500a000));u.mem_write(0x5500a91c,b'\x0c')
  def boundary(m,pc,n,_):
   if pc==0x5320b31c:
    m.reg_write(UC_ARM_REG_R0,0x55009000);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,boundary);u.mem_write(event,struct.pack('<H',0x37))
  self.assertEqual(self.call(u,'ab_adj_event',controller,event),1)
  self.assertIn(0x531a2820,self.executed)
  self.assertTrue(any(e[0]=='dispatch' and e[1:4]==(controller,0x0200f104,0x02000000) for e in self.events))
  u.mem_write(event,struct.pack('<H',0xa1));self.assertEqual(self.call(u,'ab_adj_event',controller,event),1)
  u.mem_write(event,struct.pack('<H',0x37))
  before=self.count('m10v_ab_adj_event_original')
  u.mem_write(0x5500a91c,b'\x0b');self.call(u,'ab_adj_event',controller,event)
  self.assertEqual(self.count('m10v_ab_adj_event_original'),before+1)
  self.assertEqual(self.count('dispatch'),1)

 def test_diagnostics_name_the_gate_that_rejects_disp(self):
  u=self.begin();event=0x10000100;u.mem_write(event,struct.pack('<H',0x37))
  u.mem_write(0x55008000+0x1b,b'\1')
  self.call(u,'ab_setup',0x55050000,event,0x02000012)
  self.assertTrue(any(e[0]=='m10v_debug_log' and e[1:4]==(89,0x37,2) for e in self.events))
  self.assertFalse(self.count('dispatch'))

 def test_physical_disp_reaches_actual_imagecontrol_factory_and_navigation(self):
  from unicorn.arm_const import UC_ARM_REG_PC
  u=self.begin();self.route=0x02000012
  # Independent stock factory evidence: its ImageControl cache is +0x94.
  self.real_factory=True
  u.mem_write(0x55063914+0x94,struct.pack('<I',self.fallback))
  # Execute physical mapper -> patched selector -> actual stock factory.
  selector=self.externals['m10v_settings_controller_ab_selector']
  from scripts.build_gr3_menu_patches import branch
  u.mem_write(0x53221a1c,struct.pack('<I',branch(0x53221a1c,selector)))
  u.mem_write(0x10000100,struct.pack('<HHI',4,0,0x10000200))
  u.mem_write(0x10000200,struct.pack('<II',1,1))
  self.call(u,0x532231e4,0,0x10000100)
  self.assertIn(0x53170788,self.executed) # original ImageControl factory branch
  self.assertTrue(any(e[0]=='dispatch' and e[1:4]==(self.fallback,0x0200f104,0x02000012) for e in self.events))
  self.assertTrue(any(e[0]=='m10v_debug_log' and e[1:4]==(85,0x37,0x02000012) for e in self.events))
  # The old assumed route resolves another controller and must stay untouched.
  self.route=0x0200004e;before=self.count('dispatch')
  self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('dispatch'),before)

 def test_pair_save_failure_keeps_setup_open_and_does_not_intercept_disp(self):
  u=self.begin();self.call(u,'ready',self.page,0x0200f104);self.key(u,0xd1);self.key(u,0xd1)
  self.ab_storage_fail=True;self.key(u,0xd8)
  self.assertEqual(self.word(u,self.page+adapter.SCREEN),6)
  self.assertEqual(self.word(u,self.page+adapter.SCREEN+24),3)
  self.assertFalse(self.ab_files)
  before=self.count('m10v_ab_mapper_original');self.call(u,'ab_mapper',0,0x37)
  self.assertEqual(self.count('m10v_ab_mapper_original'),before+1)

 def test_private_ab_route_keeps_imagecontrol_parent_and_cancel_does_not_activate(self):
  u=self.begin();self.route=0x02000012
  before=self.count('dispatch');self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('dispatch'),before+1)
  self.assertTrue(any(e[0]=='dispatch' and e[2:4]==(0x0200f104,0x02000012) for e in self.events))
  self.assertTrue(any(e[0]=='m10v_settings_factory_original' and e[2]==0x02000012 for e in self.events))
  self.assertEqual(self.call(u,'factory',0,0x0200f104),self.page)
  self.assertEqual(self.call(u,'key_route',0),0x02000012) # only private destination remaps
  self.route=0x0200f104;self.assertEqual(self.call(u,'key_route',0),0x0200004a)
  self.call(u,'ready',self.page,0x0200f104)
  # The stock navigation event binds its supplied return route to +0x150.
  u.mem_write(self.page+0x150,struct.pack('<I',0x02000012))
  self.key(u,0x89)
  self.assertTrue(any(e[0]=='dispatch' and e[2:4]==(0x02000012,0x10000000) for e in self.events))
  self.assertFalse(self.ab_files);self.assertEqual(self.ab_tone,12)

 def test_raw_development_imagecontrol_disp_is_not_intercepted(self):
  u=self.begin();self.route=0x02000012
  u.mem_write(0x55008000+0x1b,b'\1')
  before=self.count('dispatch');stock=self.count('m10v_ab_selector_original')
  self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('dispatch'),before)
  self.assertEqual(self.count('m10v_ab_selector_original'),stock+1)


class ABCompareTests(unittest.TestCase):
 def test_original_disp_physical_edges_and_menu_entry(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
  from scripts.analyze_gr3_settings import read_firmware,emulate_topmenu_key
  firmware=read_firmware(ROOT/'builds/gr3-extension-validation/official-rtos.bin')
  # Stock event-name directory independently identifies physical event4 as DISP.
  at=struct.unpack_from('<I',firmware,0x10b4554)[0]-0x53000000
  self.assertEqual(firmware[at:].split(b'\0',1)[0],b'EVT_SWITCH_DISP')
  edges=[]
  for kind,value in [(1,1),(2,1),(2,0)]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x53000000,firmware)
   u.mem_map(0x56000000,0x10000)
   u.mem_write(0x56000100,struct.pack('<HHI',4,0,0x56000200));u.mem_write(0x56000200,struct.pack('<II',kind,value))
   def hook(m,pc,n,_):
    if pc==0x53221a1c:edges.append(m.reg_read(UC_ARM_REG_R1));m.emu_stop()
   u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,0x56001000);u.reg_write(UC_ARM_REG_R1,0x56000100)
   u.reg_write(UC_ARM_REG_SP,0x5600fff0);u.reg_write(UC_ARM_REG_LR,0x56000000)
   u.emu_start(0x532231e4,0x56000000,count=10000)
  self.assertEqual(edges,[0x37,0x38,0x36])
  # Stock TopMenu ignores DISP; our scoped selector bridge must supply entry.
  self.assertEqual(emulate_topmenu_key(firmware,0x36),[])

 def test_slot_switch_debounce_and_fail_closed(self):
  self.assertTrue((ROOT/'native/gr3/m10v_ab.h').exists(), 'A/B controller is missing')
  code = r'''
#include "m10v_ab.h"
#include <assert.h>
int main(void){
 m10v_ab s={0};
 assert(m10v_ab_start(&s,0,1,0,34,72)==0);
 assert(s.enabled&&s.selected==0);
 assert(m10v_ab_key(&s,0x37,0)==2); /* destination slot1 plus1 */
 assert(m10v_ab_key(&s,0x37,0)==0); /* repeated down */
 assert(m10v_ab_key(&s,0x38,0)==0); /* hold */
 m10v_ab_commit(&s,1);
 assert(m10v_ab_key(&s,0x36,1)==0);
 assert(m10v_ab_key(&s,0x37,1)==1);
 m10v_ab_commit(&s,0);
 assert(m10v_ab_key(&s,0x36,0)==0);
 assert(m10v_ab_key(&s,0x22,0)==0&&s.enabled); /* unrelated key */
 assert(m10v_ab_key(&s,0x37,4)==0&&!s.enabled); /* manual change */
 assert(m10v_ab_start(&s,2,2,2,34,72)<0&&!s.enabled);
 assert(m10v_ab_start(&s,12,1,0,34,72)<0);
 assert(m10v_ab_start(&s,1,5,1,69,0)==0); /* Portra vs stock Hi-Contrast BW */
 assert(m10v_ab_tone(5)==16&&m10v_ab_slot(5)==5);
 assert(m10v_ab_key(&s,0x37,1)==6);
 m10v_ab_commit(&s,5);m10v_ab_key(&s,0x36,5);
 assert(m10v_ab_key(&s,0x37,5)==2);
 assert(m10v_ab_start(&s,0,1,1,34,72)==0&&s.selected==1);
 assert(m10v_ab_key(&s,0x37,1)==1);
 /* A failed setter is never committed; release allows retry of A. */
 assert(s.selected==1);
 assert(m10v_ab_key(&s,0x36,1)==0);
 assert(m10v_ab_key(&s,0x37,1)==1);
 return 0;
}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(code)
   subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(ROOT/'native/gr3'),str(p/'test.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
