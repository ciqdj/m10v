"""Native-host A/B acceptance contracts. Actual ARM state/adapter and original
Base input filtering; native widgets, storage and model setter are boundaries."""
from tests.test_gr3_native_ab_host import NativeHostTests
import struct

class NativeSwitchTests(NativeHostTests):
 def open(self,u):self.call(u,'ab_setup',self.controller,self.event(u,0x37),self.route)
 def key(self,u,key):return self.call(u,'ab_adj_event',self.controller,self.event(u,key))
 def choose_a(self,u,index):
  current=12 if self.appended_slots else 1
  for _ in range((index-current)%(17 if self.appended_slots else 12)):self.key(u,0xd1)
  self.key(u,0xd8)
 def start(self,u):
  self.key(u,0xd8)
 def test_disp_opens_choices_directly_and_two_ok_actions_start_pair(self):
  u=self.begin();self.open(u)
  self.assertTrue(any(e[0]==0x53396f80 and e[2]==992 for e in self.ui))
  self.assertFalse(any(e[0]==0x53396f80 and e[2]==991 for e in self.ui))
  self.key(u,0xd8)
  self.assertTrue(any(e[0]==0x53396f80 and e[2]==993 for e in self.ui))
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.ab_files)
  self.key(u,0xd8)
  self.assertEqual(self.word(u,self.page+0x284+8),1)
  self.assertEqual(self.count('activate_tone'),1)
 def test_disp_in_picker_exits_only_after_entry_release(self):
  u=self.begin();self.open(u);self.key(u,0x37)
  self.assertFalse(self.count('dispatch'))
  self.key(u,0x36);self.key(u,0x37)
  self.assertTrue(any(e[0]=='dispatch' and e[2]==0x08000000 for e in self.events))
  draws=len(self.ui);self.key(u,0x37) # duplicate press before queued navigation commits
  self.assertEqual(len(self.ui),draws)
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.ab_files)
 def test_cancel_active_picker_does_not_treat_menu_followup_as_native_ok(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.start(u)
  self.key(u,0x36);self.open(u);self.key(u,5);self.key(u,0xd8)
  self.assertEqual(self.word(u,self.page+0x284+8),1)
 def test_browse_choose_cancel_never_sets_tone_or_saves_pair(self):
  u=self.begin();self.open(u)
  for _ in range(8):self.key(u,0xd1)
  self.key(u,5);self.key(u,0xd8) # duplicate MENU confirm must be swallowed
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.ab_files)
  self.assertTrue(any(e[0]==0x53396f80 and e[2]==992 for e in self.ui))
 def test_start_bw_color_pair_then_live_disp_and_fn(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.start(u)
  self.assertEqual(self.ab_tone,11)
  self.assertTrue(any(e[0]=='dispatch' and e[2]==0x08000000 for e in self.events))
  self.assertTrue(self.ab_files)
  self.route=0x08000000
  self.assertEqual(self.call(u,'ab_selector',0,0x37),1)
  self.assertEqual(self.ab_tone,16,'B must use stock Hi-Contrast B&W')
  self.call(u,'ab_selector',0,0x37);self.call(u,'ab_selector',0,0x38)
  self.assertEqual(self.ab_tone,16)
  self.call(u,'ab_selector',0,0x36);self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.ab_tone,11)
  before=self.count('m10v_ab_mapper_original');self.call(u,'ab_mapper',0,0x1b)
  self.assertEqual(self.count('m10v_ab_mapper_original'),before+1)
 def test_live_event_consumption_does_not_fall_back_to_native_disp(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.start(u);self.route=0x08000000
  before=self.count('m10v_ab_selector_original')
  self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('m10v_ab_selector_original'),before)
  self.assertEqual(self.call(u,'ab_live_event',0x55051000,self.event(u,0x37)),1)
 def test_normal_adj_ok_exits_ab_before_stock_confirmation(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.start(u)
  # A/B host has restored the stock ADJ list. A later ordinary ImageControl
  # OK must end the session before native OK queues its return to LiveView,
  # even when the user confirms the same tone. No setter may be substituted.
  before=self.count('activate_tone');native=self.count('m10v_ab_adj_event_original')
  self.key(u,0xd8)
  self.assertEqual(self.word(u,self.page+0x284+8),0)
  self.assertEqual(self.count('m10v_ab_adj_event_original'),native+1)
  self.assertEqual(self.count('activate_tone'),before)
 def test_other_adj_slot_ok_does_not_end_ab(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.start(u);self.adj_type=8
  self.key(u,0xd8);self.assertEqual(self.word(u,self.page+0x284+8),1)
 def test_native_event_can_replace_owner_without_old_tail_access(self):
  from unicorn import UC_PROT_ALL
  u=self.begin();old=self.owner;new=0x55045000;tail=new+0x13bc
  self.call(u,'top_ctor',new)
  u.mem_write(self.page+0x284,struct.pack('<7I',0,7,1,0,0,0,0))
  u.mem_write(tail+0x284,struct.pack('<7I',0,7,1,0,7,0,0));self.ab_tone=17
  def replace(m):
   m.mem_write(0x55063988,struct.pack('<I',new));m.mem_protect(old,0x2000,0)
  self.native_event_callback=replace
  self.call(u,'ab_live_event',self.controller,self.event(u,0xb8))
  self.assertEqual(self.word(u,tail+0x284+8),1)
  u.mem_protect(old,0x2000,UC_PROT_ALL)
  self.assertEqual(self.word(u,self.page+0x284+8),1)
 def test_save_failure_and_equal_choices_do_not_activate(self):
  u=self.begin();self.open(u);self.choose_a(u,5);self.start(u)
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.ab_files)
  self.assertFalse(self.count('dispatch'))
  # On a fresh session, a rejected write must not apply A.
  u=self.begin();self.open(u);self.choose_a(u,0);self.ab_storage_fail=True;self.start(u)
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.count('dispatch'))
 def test_setter_failure_stays_on_settings_and_reboot_disables_session(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.ab_set_fail=True;self.start(u)
  self.assertEqual(self.ab_tone,12);self.assertFalse(self.count('dispatch'))
  self.ab_set_fail=False;self.key(u,0xd8);self.route=0x08000000
  self.call(u,'top_ctor',self.owner)
  before=self.count('m10v_ab_selector_original');self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('m10v_ab_selector_original'),before+1)
 def test_exit_keeps_current_style_and_restores_disp(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.start(u)
  self.call(u,'ab_setup',self.controller,self.event(u,0x36),self.route)
  self.open(u)
  self.key(u,0x36);self.key(u,0x37);self.assertEqual(self.ab_tone,11)
  self.route=0x08000000;before=self.count('m10v_ab_selector_original')
  self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('m10v_ab_selector_original'),before+1)

 def test_replacing_paired_film_in_same_slot_exits_without_overriding_it(self):
  u=self.begin();self.open(u);self.key(u,0xd8);self.start(u);self.route=0x08000000
  self.fresh_films=[38,34,35,36,37]
  before=self.count('activate_tone');stock=self.count('m10v_ab_selector_original')
  self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.count('activate_tone'),before)
  self.assertEqual(self.count('m10v_ab_selector_original'),stock+1)

 def test_small_native_row_capacity_and_selection_callback_keep_drafts(self):
  u=self.begin();u.mem_write(self.list+0xf8,struct.pack('<I',0x55074000+3*4));self.open(u)
  self.assertTrue(any(e[0]==0x53394e8c and e[2]==3 for e in self.ui))
  self.list_cursor=1;self.call(u,'ab_adj_changed',self.controller);self.key(u,0xd8)
  self.assertTrue(any(e[0]==0x53396f80 and e[2]==993 for e in self.ui))
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.ab_files)
 def test_read_and_live_setter_failures_preserve_tone(self):
  u=self.begin();self.open(u);self.choose_a(u,0);self.load_fail=True;self.start(u)
  self.assertFalse(self.count('activate_tone'));self.assertFalse(self.count('dispatch'))
  self.load_fail=False;self.key(u,0xd8);self.route=0x08000000
  self.ab_set_fail=True;self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.ab_tone,11)
  self.ab_set_fail=False;self.call(u,'ab_selector',0,0x36);self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.ab_tone,16)
  self.ab_tone=17;before=self.count('m10v_ab_selector_original')
  self.call(u,'ab_selector',0,0x36);self.call(u,'ab_selector',0,0x37)
  self.assertEqual(self.ab_tone,17)
  self.assertGreater(self.count('m10v_ab_selector_original'),before)

 def test_physical_menu_press_release_only_cancels_one_picker_level(self):
  u=self.begin();self.open(u);self.key(u,0xd8)
  for phase,repeats in ((1,1),(2,0)):
   e=self.physical(u,phase,repeats);u.mem_write(e,struct.pack('<H',5));self.call(u,'ab_adj_event',self.controller,e)
  self.key(u,0xd8) # queued native confirm after MENU, not a new OK
  self.assertEqual(self.count('m10v_ab_adj_event_original'),0)
  self.assertFalse(any(e[0]==0x53395224 for e in self.ui))
  self.assertFalse(self.count('dispatch'));self.assertFalse(self.count('activate_tone'))

class AppendedNativeSwitchTests(NativeSwitchTests):
 appended_slots=True
 def test_all_stock_and_five_appended_choices_remain_available(self):
  u=self.begin();self.open(u);self.key(u,0xd8)
  for _ in range(17):self.key(u,0xd1)
  rows=[e[2] for e in self.ui if e[0]==0x533a1808]
  self.assertIn(272,rows) # Hi-Contrast BW native resource
  self.assertIn(278,rows) # restored Cross Processing
  self.assertFalse(self.count('activate_tone'))
