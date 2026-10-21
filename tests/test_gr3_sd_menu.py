"""Independent settings owns SD installation. Legacy private SD groups 14..46
were retired because they overlap the main menu's advanced texture groups.
Catalog identity, failed saves and exact slot activation run in controller tests;
this contract checks the remaining main menu and settings resource integration.
"""
import tempfile,unittest
from pathlib import Path
from scripts.build_gr3_m10v_library import build
class SdMenuTests(unittest.TestCase):
 def test_independent_settings_resources_preserve_main_advanced_controls(self):
  with tempfile.TemporaryDirectory() as tmp:manifest=build(Path(tmp),sd_library=True)
  self.assertEqual(manifest['settings_menu']['private_routes'],[0x0200f100,0x0200f101,0x0200f103,0x0200f104])
  texts=manifest['resources']['texts']
  self.assertEqual(texts[937-786:939-786],['胶卷库','时间水印'])
  self.assertIn('颗粒尺寸',texts)
  self.assertIn('模拟曝光EI',texts)
if __name__=='__main__':unittest.main()
