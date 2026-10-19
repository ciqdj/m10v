"""Hardware-parameter feasibility, never a claim of hardware image rendering."""
import json
import unittest
from pathlib import Path
from scripts.analyze_gr3_isp_color_backend import ROOT,run_probe

class ISPColorBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'builds/gr3-extension-validation/official-rtos.bin'
        if not path.exists():raise unittest.SkipTest('locked official RTOS not extracted')
        cls.rom=path.read_bytes()
        cls.looks=json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']

    def test_matrix_curve_post_writers_keep_shooting_state_and_next_stock_frame(self):
        for film in (34,35,37,65):
            for stage in (0,1):
                with self.subTest(film=film,stage=stage):
                    row=run_probe(self.rom,self.looks[film-34],stage=stage)
                    self.assertEqual(row['assertions'],[])
                    self.assertEqual(row['outside_allowed_offsets'],[])
                    self.assertTrue(row['shooting_info_unchanged'])
                    self.assertTrue(row['shared_records_unchanged'])
                    self.assertTrue(row['initialized_globals_match_stock'])
                    self.assertTrue(row['next_standard_unchanged'])
                    self.assertTrue(row['reused_object_next_standard_unchanged'])
                    self.assertGreater(row['changed_bytes'],0)
                    self.assertEqual([e['phase'] for e in row['events']],['matrix','post','curves'])
                    post=next(e for e in row['events'] if e['phase']=='post')
                    # This exposes any hardware-width wrapping instead of
                    # silently accepting a "valid" but wrong parameter bank.
                    self.assertTrue(all(-256<=v<=255 for v in post['composed_csp']))
                    self.assertEqual(row['csp_registers_signed9'],post['composed_csp'])

    def test_saturation_hue_and_highlight_controls_still_use_native_writers(self):
        for settings in ({0x77d:1,0x77e:0,0x780:2,0x793:6,0x794:2},
                         {0x77d:7,0x77e:8,0x780:6,0x793:2,0x794:6}):
            row=run_probe(self.rom,self.looks[1],extra=settings)
            self.assertEqual(row['assertions'],[])
            self.assertEqual(row['outside_allowed_offsets'],[])
            self.assertTrue(row['shooting_info_unchanged']);self.assertTrue(row['next_standard_unchanged'])

    def test_unknown_firmware_is_rejected_before_emulator_or_parameter_writes(self):
        with self.assertRaisesRegex(ValueError,'RTOS hash'):run_probe(b'not firmware',self.looks[1])

    def test_post_matrix_that_wraps_hardware_precision_is_rejected(self):
        import copy
        look=copy.deepcopy(self.looks[1]);look['postQ512']=[5120,0,0,0,5120,0,0,0,5120]
        with self.assertRaisesRegex(ValueError,'CSP.*signed9'):run_probe(self.rom,look)

    def test_unrestored_gamma_reproduces_cross_frame_cache_contamination(self):
        row=run_probe(self.rom,self.looks[1],restore_cache=False)
        self.assertTrue(row['next_standard_unchanged'])
        self.assertFalse(row['reused_object_next_standard_unchanged'])
        self.assertGreater(len(row['reused_object_difference_offsets']),0)
        self.assertTrue(all(0x2688<=i<0x5088 for i in row['reused_object_difference_offsets']))

    def test_curve_only_change_reaches_gamma_banks_without_changing_matrices(self):
        import copy
        look=copy.deepcopy(self.looks[1])
        a=run_probe(self.rom,look)
        look['curves']=[[min(v*3//4,16383) for v in channel] for channel in look['curves']]
        b=run_probe(self.rom,look)
        self.assertEqual(a['matrix_registers_signed12'],b['matrix_registers_signed12'])
        self.assertEqual(a['csp_registers_signed9'],b['csp_registers_signed9'])
        self.assertNotEqual(a['gamma_banks_sha256'],b['gamma_banks_sha256'])
        self.assertTrue(b['reused_object_next_standard_unchanged'])
