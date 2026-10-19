import json,tempfile,unittest
from pathlib import Path
from scripts.build_gr3_m10v_library import build

class TextureBuildTests(unittest.TestCase):
 def test_texture_block_is_linked_into_actual_runtime_with_original_effect_tables(self):
  with tempfile.TemporaryDirectory() as folder:
   manifest=build(folder,debug_mode=True,candidate_color=True,spatial_neon=True,texture_neon=True)
   self.assertIn('m10v_texture_block8',manifest['symbols'])
   self.assertIn('m10v_harman_texture_table',manifest['symbols'])
   self.assertTrue(manifest['experimental_capture']['texture_neon'])
   self.assertFalse(manifest['experimental_capture']['full_isp_effects'])
 def test_texture_block_requires_validated_neon_grain_and_debug_ownership(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaises(ValueError):build(folder,texture_neon=True,debug_mode=True)
   with self.assertRaises(ValueError):build(folder,texture_neon=True,spatial_neon=True)
 def test_actual_save_and_pool_probes_are_installed_with_explicit_ownership(self):
  with tempfile.TemporaryDirectory() as folder:
   manifest=build(folder,debug_mode=True,lifecycle_trace=True,save_chain_trace=True)
   lifecycle=manifest['capture_lifecycle']
   addresses={p['address'] for p in lifecycle['patches']}
   self.assertTrue({0x53505d78,0x53505d7c,0x53505dbc,0x53521e18}<=addresses)
   self.assertTrue(lifecycle['raw_lifetime_attestation'])
   self.assertEqual(lifecycle['owner']['storage']['extended_recipe_bytes'],0x50f0)
   self.assertTrue(any('M10V_RAW_LIFETIME=1' in flag for flag in manifest['debug_compile_flags']))
   self.assertNotIn(0x5350b380,addresses)
   self.assertFalse(lifecycle['buffer_policy_changed'])
