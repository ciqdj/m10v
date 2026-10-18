"""Regression checks against the exact official native ownership ABI."""
import hashlib
import json
import struct
import unittest
from pathlib import Path
from scripts.build_gr4_settings_hooks import BASE, BASE_VTABLE, ROOT, build_settings_hooks

class SettingsHooksTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rtos=(ROOT/'data/research/gr4/RTOS.bin').read_bytes()
  cls.profile=json.loads((ROOT/'native/gr4/ui-abi.json').read_text())
  cls.base=0x54e00000
  cls.symbols={'m10v_settings_controller_'+n:0x54d00000+i*4 for i,n in enumerate(['destroy','enter','ready','key','factory','top_dtor','top_ctor','key_route'])}
 def test_profile_function_preimages(self):
  self.assertEqual(hashlib.sha256(self.rtos).hexdigest(),self.profile['source_sha256'])
  for entry in self.profile['functions']:
   a=int(entry['gr4'],16)-BASE;expected=bytes.fromhex(entry['preimage'])
   self.assertEqual(self.rtos[a:a+len(expected)],expected)
 def test_all_patches_match_and_do_not_overlap(self):
  code,report=build_settings_hooks(self.base,self.symbols,self.rtos)
  claimed=set()
  for p in report['patches']:
   expected=bytes.fromhex(p['expected']);replacement=bytes.fromhex(p['replacement'])
   self.assertEqual(len(expected),len(replacement))
   self.assertEqual(self.rtos[p['address']-BASE:p['address']-BASE+len(expected)],expected)
   addresses=set(range(p['address'],p['address']+len(expected)))
   self.assertFalse(claimed&addresses);claimed|=addresses
  self.assertEqual(report['owner_bytes'],0x13ec+2*0x2c0)
  self.assertFalse(report['camera_tested'])
  # Custom pages replace only lifecycle slots; original virtual contracts stay.
  table=list(struct.unpack_from('<15I',code,report['vtable']-self.base))
  for i in range(15):
   self.assertEqual(table[i],self.symbols.get({1:'m10v_settings_controller_destroy',2:'m10v_settings_controller_destroy',7:'m10v_settings_controller_enter',9:'m10v_settings_controller_ready',10:'m10v_settings_controller_key'}.get(i),BASE_VTABLE[i]))
 def test_preserves_original_setup_rows_and_footer_layout(self):
  _,report=build_settings_hooks(self.base,self.symbols,self.rtos)
  patches={p['address']:p for p in report['patches']}
  self.assertEqual(patches[0x53d9ca98]['replacement'],'1a1c1e21')
  for i in [31,32]:
   self.assertIn(0x53d9ca10+0x8c+i*8,patches)
   self.assertIn(0x53d9ca10+0x1bc+i*4,patches)
  self.assertNotIn(0x5325ca14,patches) # route getter must remain global-stock
  # New keys dispatch is scoped to the original key-dispatch call only.
  self.assertIn(0x532544c0,patches)
 def test_rejects_modified_official_source(self):
  changed=bytearray(self.rtos);changed[0x187880]^=1
  with self.assertRaisesRegex(ValueError,'exact official'):build_settings_hooks(self.base,self.symbols,changed)

if __name__=='__main__':unittest.main()
