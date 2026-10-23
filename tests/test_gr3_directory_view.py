"""Group-page regression using original GR III 2.10 constructors and setters.

No text setter is mocked: the broken group count invokes an ASCII setter on a
resource-label object and faults inside the original string routine.
"""
import struct,unittest,tempfile
from pathlib import Path
from tests import test_gr3_settings_view as support

class DirectoryViewTests(unittest.TestCase):
 setUpClass=classmethod(support.SettingsViewTests.setUpClass.__func__)
 machine=support.SettingsViewTests.machine
 call=support.SettingsViewTests.call

 def state(self,u,focus):
  s=bytearray(216) # schema5 journal184 + eight menu words
  for i,film in enumerate([38,75,79]):struct.pack_into('<H',s,12+8*i,film)
  struct.pack_into('<8I',s,184,8,focus,0,0,0,0,0,0)
  u.mem_write(0x10002000,bytes(s))

 def test_group_entry_counts_use_resource_labels_and_return_without_fault(self):
  u=self.machine();self.assertEqual(self.call(u,'create',0x10001000),0)
  w=struct.unpack('<56I',u.mem_read(0x10001000,224))
  self.state(u,0);self.call(u,'draw',0x10001000,0x10002000,0)
  caption=lambda index:struct.unpack('<H',u.mem_read(w[index]+0xea,2))[0]
  self.assertEqual([caption(i) for i in range(44,48)],[1129,1130,1131,1132])
  self.assertEqual([caption(i) for i in range(48,52)],[1143,1151,1138,1143])
  self.assertEqual([caption(2),caption(4)],[1134,1135])
  self.call(u,'destroy',0x10001000);self.assertFalse(self.live)

 def test_last_group_and_retired_count_redraw_without_corrupting_widgets(self):
  u=self.machine();self.call(u,'create',0x10001000)
  w=struct.unpack('<56I',u.mem_read(0x10001000,224))
  for focus in [0,4,5,0,4]:
   self.state(u,focus);self.call(u,'draw',0x10001000,0x10002000,0)
   caption=lambda index:struct.unpack('<H',u.mem_read(w[index]+0xea,2))[0]
   if focus>=4:
    self.assertEqual([caption(44),caption(45)],[1133,1136])
    self.assertEqual([caption(48),caption(49)],[1140,1139])
    self.assertEqual([u.mem_read(w[i]+0x9e,1)[0] for i in range(44,48)],[1,1,0,0])
  self.call(u,'destroy',0x10001000);self.assertFalse(self.live)

class LinkedDirectoryViewTests(DirectoryViewTests):
 @classmethod
 def setUpClass(cls):
  super().setUpClass()
  from scripts.build_gr3_m10v_library import build
  with tempfile.TemporaryDirectory() as tmp:
   manifest=build(Path(tmp),base=support.BASE,sd_library=True,appended_slots=True)
   cls.code=(Path(tmp)/'m10v-library-arm.bin').read_bytes()
   cls.symbols=manifest['symbols'];cls.card=b'';cls.captions=b''
   assert manifest['resources']['texts'][1137-786:1168-786]==list(map(str,range(31)))

if __name__=='__main__':unittest.main()
