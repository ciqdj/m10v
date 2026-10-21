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

    def test_original_buffer_initializer_sizes_the_shared_arena_and_preserves_layout_alias_owners(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_buffer_pool_layout'))
        for mode in range(5):
            with self.subTest(mode=mode):
                result=native.probe_buffer_pool_layout(component('gr2','b01firm8'),mode)
                self.assertEqual(result['arena_requested_bytes'],0x1dcb02e0)
                self.assertTrue(result['all_aliases_match']);self.assertTrue(result['all_pool_spans_bounded'])
                self.assertTrue(result['definitions_preserved']);self.assertTrue(result['stack_preserved'])
                self.assertTrue(result['callee_saved_preserved']);self.assertEqual(result['final_layout'],mode)
                self.assertEqual(result['buffers']['32']['declared_bytes'],0xe5800)
                self.assertEqual(result['buffers']['46']['declared_bytes'],0x2000000)
                self.assertEqual(result['buffers']['46']['owner_tag'],46 if mode==3 else 38)

    def test_original_scratch_buffers_exhaust_without_overlap_and_release_out_of_order_without_leaks(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_buffer_lifetime'))
        for mode in range(5):
            with self.subTest(mode=mode):
                result=native.probe_buffer_lifetime(component('gr2','b01firm8'),mode)
                self.assertTrue(result['exhaustion_returned_null']);self.assertTrue(result['all_spans_disjoint'])
                self.assertTrue(result['handles_cleared']);self.assertTrue(result['metadata_reclaimed'])
                self.assertTrue(result['pool_restored']);self.assertTrue(result['raw_access_matches'])
                self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])
                self.assertEqual(result['out_of_order_release_deferred'],mode!=3)
                self.assertGreaterEqual(result['large_buffer_count'],1)

    def test_original_clarity_preserves_full_resolution_geometry_and_bounds_pregraph_tables_to_small_scratch(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_clarity_graph_admission'))
        for geometry in (0x00040020,0x0cc01340):
            for strength in (1,4,6,9):
                with self.subTest(geometry=geometry,strength=strength):
                    result=native.probe_clarity_graph_admission(component('gr2','b01firm8'),strength,geometry)
                    self.assertEqual(result['geometry'],geometry);self.assertEqual(result['stage'],0xa013ea7c)
                    self.assertEqual(result['table_write_bytes'],0xe000)
                    self.assertTrue(result['cpu_workspace_writes_bounded']);self.assertTrue(result['arena_guards_preserved'])
                    self.assertTrue(result['request_preserved']);self.assertTrue(result['context_preserved'])
