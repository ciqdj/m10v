"""Regression for generic repacker policy edits losing GR4 registry recovery.
Uses the actual official gate and recovery footer; no full frame compression.
"""
import hashlib,struct,unittest
from pathlib import Path
from scripts.build_gr4_m10v_firmware import prepare_package_policy
from gr4_editor.slots import _finish,_metadata,_canonical_restore,canonical_base,OFFICIAL7_SHA
from gr4_editor.demo_build import prepare_update_policy as repacker_policy
from gr4_editor.firmware import _patch_rtos_version
from gr4_editor.update_policy import inspect_update_policy
ROOT=Path(__file__).resolve().parents[1]

class Gr4PackageRecoveryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base=(ROOT/'data/research/gr4/RTOS.bin').read_bytes()
  if hashlib.sha256(cls.base).hexdigest()!=OFFICIAL7_SHA:raise AssertionError('official fixture identity differs')
 def registry(self):
  body=bytearray(self.base+bytes(32))
  metadata={'schema_version':3,'base_kind':'official-1.11.10.7','compiler_base_sha256':OFFICIAL7_SHA,'compiler_base_size':len(self.base),'compiler_base_restore':_canonical_restore(self.base,body),'m10v':{'initial_state_hex':'preserved'}}
  return _finish(body,metadata)
 def test_regression_generic_repacker_policy_omits_new_restore_words(self):
  source=self.registry();self.assertEqual(canonical_base(source),self.base)
  changed,proof=repacker_policy(source,allow_older=True)
  self.assertTrue(inspect_update_policy(changed)['installed']);self.assertTrue(_metadata(changed))
  with self.assertRaisesRegex(ValueError,'compiler base SHA256'):canonical_base(changed)
 def test_owned_policy_survives_generic_repacker_and_version_change(self):
  source=self.registry();ready,proof=prepare_package_policy(source,self.base)
  self.assertEqual(canonical_base(ready),self.base);self.assertTrue(inspect_update_policy(ready)['installed'])
  self.assertEqual(_metadata(ready)['m10v'],_metadata(source)['m10v'])
  self.assertGreater(len(_metadata(ready)['compiler_base_restore']),len(_metadata(source)['compiler_base_restore']))
  preserved,_=repacker_policy(ready,allow_older=True)
  self.assertEqual(preserved,ready)
  versioned=_patch_rtos_version(preserved,0x010b0a07,0x010b0a0a)
  self.assertEqual(canonical_base(versioned),self.base)
  self.assertEqual(_metadata(versioned)['m10v']['initial_state_hex'],'preserved')
 def test_policy_preparation_rejects_corrupt_registry(self):
  broken=bytearray(self.registry());broken[128]^=1
  with self.assertRaises(ValueError):prepare_package_policy(bytes(broken),self.base)
