"""Release and debug use native ownership; release SD sinks are audited no-ops."""
import unittest
from tests import test_gr3_delivered_native_pipeline as delivered
class ProductionNativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  delivered.delivered(cls)
 def test_logging_off_keeps_native_color_and_live_and_has_no_sd_sink(self):
  m=self.manifest
  if m['debug_mode']:self.skipTest('select release BIN with M10V_SHARED_CANDIDATE')
  self.assertIsNone(m['debug_log'])
  self.assertTrue(m['capture_lifecycle']['snapshot']['native_color'])
  self.assertTrue(m['capture_lifecycle']['snapshot']['live_color'])
  self.assertIsNotNone(m['capture_lifecycle']['view_deferred'])
  for name in ('m10v_debug_log','m10v_debug_batch'):
   at=m['symbols'][name]-m['base']
   self.assertEqual(self.code[at:at+8],bytes.fromhex('0000a0e31eff2fe1'))
  for filename in (b'M10VMN0.BIN',b'M10VCP0.BIN',b'M10VIO0.BIN'):
   self.assertNotIn(filename,self.code)
