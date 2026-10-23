"""Retired controls cannot enter any camera detail list."""
import unittest
from scripts.build_gr3_native_detail import DETAIL_IDS, FIELDS
class NativeGrainMenuTests(unittest.TestCase):
 def test_supported_rows_keep_stable_identifiers(self):
  self.assertEqual(DETAIL_IDS,{'halo':[18,19,20,21],'common':[21],'red':[21,28],'charmera':[29],'phoenix':[18,19,20,21,28],'pixel':[]})
 def test_retired_captions_are_not_feature_descriptors(self):
  self.assertFalse(any('Leak' in field or 'Grain Size' in field for field in FIELDS))
 def test_gr4_has_no_software_grain_or_retired_effect_rows(self):
  from scripts.build_gr4_native_detail import DETAIL_IDS, FIELDS
  self.assertEqual(DETAIL_IDS,{'halo':[19,20,21],'common':[],'red':[29],'phoenix':[19,20,21,29]})
  self.assertFalse(any('Leak' in field or 'Grain' in field for field in FIELDS))
