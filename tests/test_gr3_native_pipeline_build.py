import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.build_gr3_m10v_library import build
class NativePipelineBuildTests(unittest.TestCase):
 def test_native_grain_and_view_recovery_are_installed_as_one_owned_pipeline(self):
  original=Path.read_bytes
  def read(path):
   if str(path).endswith('builds/gr3-extension-validation/official-rtos.bin'):raise AssertionError('production must not depend on a developer RTOS cache')
   return original(path)
  with tempfile.TemporaryDirectory() as d,patch.object(Path,'read_bytes',read):
   m=build(d,debug_mode=True,profile_mode=True,lifecycle_trace=True,save_chain_trace=True,recipe_snapshot=True,native_color=True,native_grain=True,view_deferred=True)
   self.assertFalse(m['hdf_enabled']);self.assertIsNone(m['digital_hdf']);self.assertIsNone(m['hdf_menu'])
   self.assertTrue(m['experimental_capture']['native_color']);self.assertTrue(m['experimental_capture']['native_grain'])
   p={r['address']for r in m['capture_lifecycle']['patches']}
   self.assertTrue({0x53513620,0x535033d8,0x53503aa0,0x53503ab4,0x5367ae14,0x531cc1cc,0x53239bc0}<=p)
   self.assertNotIn(0x534e87a4,p)
 def test_partial_configuration_cannot_arm_grain_without_recipe_ownership(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):build(d,native_grain=True)
   with self.assertRaises(ValueError):build(d,view_deferred=True)
   with self.assertRaisesRegex(ValueError,'Shared HDF requires native color/grain snapshot owners'):build(d,debug_mode=True,lifecycle_trace=True,hdf_enabled=True)
   with self.assertRaises(ValueError):build(d,hdf_enabled=False,hdf_default=1)
