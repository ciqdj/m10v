"""Original GR II native Clarity tables, before any HDF adaptation."""
import unittest
from tests.test_unity_update import component

class Gr2ClarityTests(unittest.TestCase):
    def test_original_clarity_expands_all_nine_rows_with_exact_fixed_point_curves_and_bounded_writes(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_clarity_tables'))
        code=component('gr2','b01firm8')
        for row in (*range(9),9,255):
            with self.subTest(row=row):
                result=native.probe_clarity_tables(code,row)
                self.assertEqual(result['effective_row'],row if row<9 else 4)
                self.assertTrue(result['curves_match']);self.assertTrue(result['metadata_matches'])
                self.assertTrue(result['guards_preserved']);self.assertTrue(result['source_tables_preserved'])
                self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])
                self.assertEqual(result['curve_bytes'],4*8192)

    def test_original_clarity_clamps_strength_bypasses_neutral_and_selects_four_owned_workspace_tables(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_clarity_entry'))
        code=component('gr2','b01firm8')
        for strength in (0,1,4,5,6,9,10,0xffffffff):
            with self.subTest(strength=strength):
                result=native.probe_clarity_entry(code,strength)
                effective=min(9,max(1,strength))
                self.assertEqual(result['effective_strength'],effective)
                self.assertEqual(result['returned_normally'],effective==5)
                self.assertEqual(result['coefficient_entry_reached'],effective!=5)
                self.assertTrue(result['request_preserved']);self.assertTrue(result['context_outside_strength_preserved'])
                self.assertEqual(result['hardware_calls'],[])
                if effective!=5:
                    self.assertEqual(result['row'],effective-1)
                    self.assertEqual(result['workspace_bases'],[0x51000000+i*8192 for i in range(4)])
                else:self.assertTrue(result['stack_preserved'])
        hdr=native.probe_clarity_entry(code,1,hdr=True)
        self.assertFalse(hdr['returned_normally']);self.assertEqual(hdr['row'],4)
        self.assertEqual(hdr['effective_strength'],5)
