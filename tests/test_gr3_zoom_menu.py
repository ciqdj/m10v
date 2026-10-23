"""Portable editor state behavior with durable journal callbacks."""
import ctypes as C,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class State(C.Structure):_fields_=[('sequence',C.c_uint32),('mm',C.c_uint16*2)]
class Editor(C.Structure):_fields_=[('sequence',C.c_uint32),('slot',C.c_uint32),('value',C.c_uint32)]
class Menu(C.Structure):_fields_=[('saved',State),('editor',Editor),('focus',C.c_uint32),('editing',C.c_uint32),('closed',C.c_uint32),('error',C.c_uint32)]
LOAD=C.CFUNCTYPE(C.c_int,C.POINTER(State));SAVE=C.CFUNCTYPE(C.c_int,C.POINTER(State),C.POINTER(Editor))
class Ops(C.Structure):_fields_=[('load',LOAD),('save',SAVE)]
class ZoomMenu(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();p=pathlib.Path(cls.tmp.name)/'menu.dylib'
  subprocess.run(['clang','-shared','-fPIC','-o',str(p),str(ROOT/'native/gr3/m10v_zoom_menu.c'),str(ROOT/'native/gr3/m10v_zoom.c')],check=True,capture_output=True);cls.lib=C.CDLL(str(p))
  cls.lib.m10v_zoom_menu_open.argtypes=[C.POINTER(Menu),C.POINTER(Ops)];cls.lib.m10v_zoom_menu_key.argtypes=[C.POINTER(Menu),C.POINTER(Ops),C.c_uint32]
 def setUp(self):
  self.fail=False;self.apply_fail=False;self.load_fail=False;self.stale=False;self.writes=[]
  def load(s):s.contents.sequence=9;s.contents.mm[:]=[35,50];return -1 if self.load_fail else 1
  def save(s,e):
   self.writes.append((e.contents.slot,e.contents.value))
   if self.stale:return -2
   if self.fail:return -1
   s.contents.mm[e.contents.slot]=e.contents.value;s.contents.sequence+=1
   return -1 if self.apply_fail else 0
  self.ops=Ops(LOAD(load),SAVE(save));self.menu=Menu();self.lib.m10v_zoom_menu_open(C.byref(self.menu),C.byref(self.ops))
 def key(self,*keys):
  for k in keys:self.lib.m10v_zoom_menu_key(C.byref(self.menu),C.byref(self.ops),k)
 def test_two_rows_edit_confirm_preserves_other_slot(self):
  self.key(3,4,0,4);self.assertEqual(list(self.menu.saved.mm),[35,49]);self.assertEqual(self.writes,[(1,49)]);self.assertFalse(self.menu.editing)
 def test_cancel_does_not_write(self):
  self.key(4,1,5);self.assertEqual(list(self.menu.saved.mm),[35,50]);self.assertFalse(self.writes);self.key(5);self.assertTrue(self.menu.closed)
 def test_failure_keeps_unsaved_draft(self):
  self.fail=True;self.key(4,1,4);self.assertEqual(self.menu.editor.value,36);self.assertEqual(self.menu.saved.mm[0],35);self.assertEqual(self.menu.error,1);self.assertTrue(self.menu.editing)
 def test_apply_failure_displays_durable_value(self):
  self.apply_fail=True;self.key(4,1,4);self.assertEqual(self.menu.saved.mm[0],36);self.assertEqual(self.menu.editor.sequence,10);self.assertEqual(self.menu.error,1)
 def test_stale_save_refreshes_editor_before_retry(self):
  self.stale=True;self.key(4,1,4);self.assertEqual(self.menu.error,1);self.assertEqual(self.menu.editor.value,35)
  self.stale=False;self.key(1,4);self.assertEqual(self.menu.saved.mm[0],36);self.assertFalse(self.menu.editing)
 def test_read_failure_only_allows_exit(self):
  self.load_fail=True;self.lib.m10v_zoom_menu_open(C.byref(self.menu),C.byref(self.ops));self.key(4,1,4);self.assertFalse(self.writes);self.assertEqual(self.menu.error,2);self.key(5);self.assertTrue(self.menu.closed)
 def test_bounds_are_one_mm_and_clamped(self):
  self.key(4);self.key(*([0]*100));self.assertEqual(self.menu.editor.value,28);self.key(*([1]*100));self.assertEqual(self.menu.editor.value,100)
if __name__=='__main__':unittest.main()
