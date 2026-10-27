"""Current ten-slot state ABI with actual native widget setters/lifetime."""
import struct, unittest
from tests import test_gr3_settings_view as view_fixture
class WatermarkViewTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):view_fixture.SettingsViewTests.setUpClass()
 def test_group_has_two_children_and_hides_timestamp_values_without_card_heap(self):
  v=view_fixture.SettingsViewTests();u=v.machine();v.call(u,'create',0x10001000)
  widgets=struct.unpack('<56I',u.mem_read(0x10001000,224))
  for screen,focus in ((9,0),(9,1),(3,0),(5,0),(9,1)):
   state=bytearray(216);struct.pack_into('<8I',state,184,screen,focus,0,0,0,0,0,0)
   u.mem_write(0x10002000,bytes(state));v.call(u,'draw',0x10001000,0x10002000,0)
   self.assertEqual(widgets[55],0)
   if screen==9:
    self.assertEqual(struct.unpack('<H',u.mem_read(widgets[2]+0xea,2))[0],938)
    self.assertEqual([u.mem_read(widgets[44+i]+0x9e,1)[0] for i in range(4)],[1,1,0,0])
    self.assertEqual([u.mem_read(widgets[48+i]+0x9e,1)[0] for i in range(4)],[0]*4)
    self.assertEqual([struct.unpack('<H',u.mem_read(widgets[44+i]+0xea,2))[0] for i in range(2)],[1138,1139])
    self.assertEqual([u.mem_read(widgets[36+i]+0x9e,1)[0] for i in range(4)],[int(i==focus) for i in range(4)])
   if screen==3:self.assertEqual(struct.unpack('<H',u.mem_read(widgets[2]+0xea,2))[0],1138)
  v.call(u,'destroy',0x10001000);self.assertFalse(v.live)
