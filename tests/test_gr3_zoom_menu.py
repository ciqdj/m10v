"""Unified crop selection/editor; callbacks bound only at storage/native edges."""
import ctypes as C,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class State(C.Structure):_fields_=[('sequence',C.c_uint32),('mm',C.c_uint16*2)]
class Editor(C.Structure):_fields_=[('sequence',C.c_uint32),('slot',C.c_uint32),('value',C.c_uint32)]
class Menu(C.Structure):_fields_=[('saved',State),('editor',Editor),('focus',C.c_uint32),('editing',C.c_uint32),('closed',C.c_uint32),('error',C.c_uint32),('selected',C.c_uint32)]
LOAD=C.CFUNCTYPE(C.c_int,C.POINTER(State));SAVE=C.CFUNCTYPE(C.c_int,C.POINTER(State),C.POINTER(Editor));SELECT=C.CFUNCTYPE(C.c_int,C.c_uint32);CURRENT=C.CFUNCTYPE(C.c_uint32)
class Ops(C.Structure):_fields_=[('load',LOAD),('save',SAVE),('select',SELECT),('current',CURRENT)]
class ZoomMenu(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();p=pathlib.Path(cls.tmp.name)/'menu.dylib'
  subprocess.run(['clang','-shared','-fPIC','-o',str(p),str(ROOT/'native/gr3/m10v_zoom_menu.c'),str(ROOT/'native/gr3/m10v_zoom.c')],check=True,capture_output=True);cls.lib=C.CDLL(str(p))
  cls.lib.m10v_zoom_menu_open.argtypes=[C.POINTER(Menu),C.POINTER(Ops)];cls.lib.m10v_zoom_menu_key.argtypes=[C.POINTER(Menu),C.POINTER(Ops),C.c_uint32]
 def setUp(self):
  self.save_fail=False;self.apply_fail=False;self.load_fail=False;self.stale=False;self.writes=[];self.applies=[];self.current=2
  def load(s):s.contents.sequence=9;s.contents.mm[:]=[40,48];return -1 if self.load_fail else 1
  def save(s,e):
   self.writes.append((e.contents.slot,e.contents.value))
   if self.stale:return -2
   if self.save_fail:return -1
   s.contents.mm[e.contents.slot]=e.contents.value;s.contents.sequence+=1;return 0
  def select(slot):self.applies.append(slot);return -1 if self.apply_fail else 0
  self.ops=Ops(LOAD(load),SAVE(save),SELECT(select),CURRENT(lambda:self.current));self.menu=Menu();self.open()
 def open(self):self.lib.m10v_zoom_menu_open(C.byref(self.menu),C.byref(self.ops))
 def key(self,*keys):
  for k in keys:self.lib.m10v_zoom_menu_key(C.byref(self.menu),C.byref(self.ops),k)
 def test_open_focuses_current_selection_with_off_first(self):
  for current,focus in [(2,0),(0,1),(1,2),(99,0)]:
   self.current=current;self.open();self.assertEqual(self.menu.focus,focus)
 def test_browse_and_direct_adjust_do_not_write_or_apply(self):
  self.key(3,1);self.assertEqual(self.menu.editor.value,41);self.assertTrue(self.menu.editing);self.assertFalse(self.writes);self.assertFalse(self.applies)
 def test_confirm_saves_then_selects_edited_slot(self):
  self.key(3,3,0,4);self.assertEqual(list(self.menu.saved.mm),[40,47]);self.assertEqual(self.writes,[(1,47)]);self.assertEqual(self.applies,[1]);self.assertTrue(self.menu.closed)
 def test_choose_existing_slot_does_not_rewrite_journal(self):
  self.key(3,3,4);self.assertFalse(self.writes);self.assertEqual(self.applies,[1]);self.assertTrue(self.menu.closed)
 def test_off_cannot_edit_and_confirm_only_applies_off(self):
  self.key(0,1,4);self.assertFalse(self.writes);self.assertEqual(self.applies,[2]);self.assertTrue(self.menu.closed)
 def test_cancel_draft_returns_without_mutation(self):
  self.key(3,1,5);self.assertEqual(list(self.menu.saved.mm),[40,48]);self.assertFalse(self.writes);self.assertFalse(self.applies);self.assertTrue(self.menu.closed)
 def test_changing_row_discards_only_unconfirmed_draft(self):
  self.key(3,1,3,4);self.assertFalse(self.writes);self.assertEqual(self.applies,[1]);self.assertEqual(list(self.menu.saved.mm),[40,48])
 def test_failure_keeps_draft_and_blocks_select(self):
  self.save_fail=True;self.key(3,1,4);self.assertEqual(self.menu.editor.value,41);self.assertEqual(self.menu.saved.mm[0],40);self.assertEqual(self.menu.error,1);self.assertFalse(self.applies);self.assertFalse(self.menu.closed)
  self.save_fail=False;self.key(4);self.assertEqual(self.menu.saved.mm[0],41);self.assertTrue(self.menu.closed)
 def test_apply_failure_retries_without_rewriting_committed_value(self):
  self.apply_fail=True;self.key(3,1,4);self.assertEqual(self.menu.saved.mm[0],41);self.assertEqual(self.menu.error,1);self.assertFalse(self.menu.closed)
  self.apply_fail=False;self.key(4);self.assertEqual(self.writes,[(0,41)]);self.assertEqual(self.applies,[0,0]);self.assertTrue(self.menu.closed)
 def test_stale_save_reloads_before_accepting_another_edit(self):
  self.stale=True;self.key(3,1,4);self.assertEqual(self.menu.error,1);self.assertEqual(self.menu.editor.value,40);self.assertFalse(self.applies)
  self.stale=False;self.key(1,4);self.assertEqual(self.menu.saved.mm[0],41);self.assertTrue(self.menu.closed)
 def test_read_failure_only_allows_exit(self):
  self.load_fail=True;self.open();self.key(3,1,4);self.assertFalse(self.writes);self.assertFalse(self.applies);self.assertEqual(self.menu.error,2);self.key(5);self.assertTrue(self.menu.closed)
 def test_bounds_are_one_mm_and_clamped(self):
  self.key(3);self.key(*([0]*100));self.assertEqual(self.menu.editor.value,28);self.key(*([1]*100));self.assertEqual(self.menu.editor.value,50)
if __name__=='__main__':unittest.main()
