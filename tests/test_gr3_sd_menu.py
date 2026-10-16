"""Actual ARM menu transitions; SD adapter is tested independently."""
import struct,tempfile,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_library_arm as arm_tests
class SdMenuTests(unittest.TestCase):
 call=arm_tests.FilmLibraryArmTests.call
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.manifest=build(Path(cls.tmp.name),sd_library=True);cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
 def machine(self):
  self.ids=list(range(33,66));self.installs=[];self.install_result=0
  u=arm_tests.FilmLibraryArmTests.machine(self)
  def sd(uc,pc,size,data):
   a=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];v=None
   if pc==self.manifest['symbols']['m10v_sd_camera_item']:
    index=a[0]*8+a[1];v=self.ids[index] if a[1]<8 and index<len(self.ids) else 0
   if pc==self.manifest['symbols']['m10v_sd_camera_install']:self.installs.append(a);v=self.install_result
   if v is not None:uc.reg_write(UC_ARM_REG_R0,v&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,sd);return u
 def test_sd_entry_and_paging_do_not_write_private_tones(self):
  u=self.machine();u.mem_write(0x5506821d,b'\1');self.assertEqual(self.call(u,'m10v_menu_count',0x55068200),7)
  self.focus=6;self.call(u,'m10v_menu_confirm',0x55005000);self.assertEqual(u.mem_read(0x5506821d,1),b'\x0e')
  self.focus=0;self.call(u,'m10v_menu_confirm',0x55005000);self.assertEqual(u.mem_read(0x5506821d,1),b'\x0f')
  self.assertEqual(self.call(u,'m10v_menu_index',0x55068200,0),512+33)
  for _ in range(4):self.focus=9;self.call(u,'m10v_menu_confirm',0x55005000)
  self.assertEqual(self.call(u,'m10v_menu_index',0x55068200,0),512+65)
  self.assertEqual(self.call(u,'m10v_menu_index',0x55068200,1),600)
  self.focus=9;self.call(u,'m10v_menu_confirm',0x55005000);self.assertEqual(u.mem_read(0x5506821d,1),bytes([19]))
  self.assertEqual(self.native_tones,[]);self.assertFalse(any(a==0x53825fa8 for a,n in self.file_calls))
 def test_confirm_binds_focused_id_and_cancellation_does_not_install(self):
  u=self.machine();u.mem_write(0x5506821d,bytes([15,21,1]));self.focus=0
  self.call(u,'m10v_menu_focus',0x55005000,0);self.assertEqual(u.mem_read(0x5506821f,1),bytes([67]))
  self.ids[0]=34;self.call(u,'m10v_menu_confirm',0x55005000);self.assertEqual(self.installs,[])
  self.ids[0]=33;self.call(u,'m10v_menu_confirm',0x55005000);self.assertEqual(self.installs,[[0,0,33,4]])
  self.assertEqual(self.native_tones,[21]);self.assertEqual(u.mem_read(0x5506821d,1),b'\x0e')
  u.mem_write(0x5506821d,b'\x0f');self.focus=10;self.call(u,'m10v_menu_confirm',0x55005000);self.assertEqual(len(self.installs),1)
 def test_failed_install_stays_in_menu_without_tone_write(self):
  u=self.machine();u.mem_write(0x5506821d,bytes([15,12,0]));self.focus=0;self.call(u,'m10v_menu_focus',0x55005000,0)
  self.install_result=-1;self.call(u,'m10v_menu_confirm',0x55005000)
  self.assertEqual(self.native_tones,[]);self.assertEqual(u.mem_read(0x5506821d,1),b'\x0f');self.assertTrue(self.captions)

 def test_independent_settings_leave_only_stock_imagecontrol_entries(self):
  u=self.machine()
  self.assertEqual(self.call(u,'m10v_menu_count',0x55068200),12)
  self.assertEqual(self.manifest['settings_menu']['private_routes'],[0x0200f100,0x0200f101])
  self.assertEqual(self.manifest['resources']['texts'][129:131],['胶卷库','时间水印'])
 def test_sd_resources_are_chinese_and_800t_native_detail_is_present(self):
  resources=self.manifest['resources'];texts=resources['texts']
  self.assertEqual(texts[914-786],'胶卷库')
  self.assertEqual(texts[858-786:860-786],['返回','完成'])
  self.assertEqual(self.manifest['detail']['ids'],[18,19,20,21,22])
