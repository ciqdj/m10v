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

    def test_original_first_clarity_stage_submits_exact_geometry_before_waiting_for_hardware_completion(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_clarity_stage_submit'))
        for geometry in (0x00040020,0x0cc01340):
            with self.subTest(geometry=geometry):
                result=native.probe_clarity_stage_submit(component('gr2','b01firm8'),geometry)
                self.assertEqual(result['resource_requests'],[[5,0xffffffff]])
                self.assertEqual(result['wait_timeout'],0xffffffff)
                self.assertEqual(result['input_address'],0x55000000)
                self.assertEqual(result['input_width'],geometry&0xffff)
                self.assertEqual(result['input_height'],geometry>>16)
                self.assertEqual(result['input_stride'],geometry&0xffff)
                self.assertTrue(result['descriptor_matches_submission'])
                self.assertTrue(result['pixel_addresses_not_accessed']);self.assertTrue(result['critical_sections_balanced'])
                self.assertFalse(result['completion_claimed'])

    def test_original_clarity_wait_maps_event_status_and_releases_resource_even_after_timeout(self):
        from scripts import analyze_gr2_native_contract as native
        for event_result in (0,0xffffffce,0xffffffff):
            with self.subTest(event_result=event_result):
                result=native.probe_clarity_stage_submit(component('gr2','b01firm8'),0x00040020,event_result=event_result)
                self.assertTrue(result['stage_returned']);self.assertEqual(result['released_resources'],[5])
                self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])
                self.assertEqual(result['event_waits'],[[11,1,1,0xffffffff]])
                self.assertEqual(result['wait_result'],0 if event_result==0 else (0x0a000011 if event_result==0xffffffce else 0x0a000099))
                self.assertEqual(result['clock_requests'][-2:],[[16,0,0],[17,0,0]])
                self.assertTrue(result['critical_sections_balanced']);self.assertFalse(result['completion_claimed'])

    def test_original_complete_clarity_control_graph_balances_resources_and_preserves_context_with_explicit_device_model(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_clarity_control_graph'))
        for geometry,strength,hdr in ((0x40020,1,False),(0x40020,9,False),(0xcc01340,1,False),(0xcc01340,9,False),(0x40020,3,True)):
            with self.subTest(geometry=geometry,strength=strength,hdr=hdr):
                result=native.probe_clarity_control_graph(component('gr2','b01firm8'),strength,geometry,hdr=hdr)
                self.assertTrue(result['returned_normally']);self.assertTrue(result['resources_balanced'])
                self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])
                self.assertTrue(result['request_preserved']);self.assertTrue(result['context_preserved'])
                self.assertTrue(result['arena_guards_preserved']);self.assertTrue(result['cpu_pixel_writes_bounded'])
                self.assertTrue(result['hdf_reserved_region_preserved']);self.assertEqual(result['hdf_reserved_cpu_reads'],0)
                self.assertGreater(result['hardware_stage_count'],8)
                self.assertFalse(result['pixel_processing_verified'])

    def test_original_layout_selector_reserves_a_second_jpeg_for_clarity_without_changing_effect_property(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_buffer_layout_selection'))
        for current in range(5):
            for effect in (0,9,12,16,17,18,19,20):
                with self.subTest(current=current,effect=effect):
                    result=native.probe_buffer_layout_selection(component('gr2','b01firm8'),6,(0,0,0),current,{0x2d:effect})
                    self.assertEqual(result['selected_layout'],0 if effect in (12,16,17,19) else 1)
                    self.assertTrue(result['properties_preserved']);self.assertTrue(result['current_layout_preserved'])
                    self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])
        for properties,expected in (({1:2},3),({1:0},4)):
            mode=5 if expected==3 else 10
            self.assertEqual(native.probe_buffer_layout_selection(component('gr2','b01firm8'),mode,(0,0,0),0,properties)['selected_layout'],expected)

        for current in range(5):
            result=native.probe_buffer_layout_selection(component('gr2','b01firm8'),7,(0,0,0),current,{0x2d:0})
            self.assertEqual(result['selected_layout'],current if current in (0,1) else 1)
            self.assertTrue(result['current_layout_preserved'])

    def test_original_idle_pool_transitions_reuse_one_arena_and_preserve_constant_pool_owners(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_buffer_pool_transitions'))
        result=native.probe_buffer_pool_transitions(component('gr2','b01firm8'),(1,2,3,4,0))
        self.assertEqual(result['layouts'],[0,1,2,3,4,0])
        self.assertEqual(result['linear_allocation_count'],2)
        self.assertTrue(result['constant_pools_preserved']);self.assertTrue(result['live_pool_identities_match'])
        self.assertTrue(result['ring_metadata_reclaimed']);self.assertTrue(result['all_live_spans_bounded'])
        self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])

    def test_original_full_resolution_pyramid_selects_eleven_detail_band_curves_in_reverse_level_order(self):
        from scripts import analyze_gr2_native_contract as native
        for strength in (1,9):
            result=native.probe_clarity_control_graph(component('gr2','b01firm8'),strength,0x0cc01340)
            self.assertIn('band_curves',result)
            bands=result['band_curves'];self.assertEqual([row['level'] for row in bands],list(range(11,0,-1)))
            uploads=result['curve_uploads'];self.assertEqual(len(uploads),13)
            self.assertEqual([entry['source'] for entry in uploads[:11]],[entry['selected_pointer'] for entry in bands])
            self.assertEqual([(entry['mode'],entry['read_bytes']) for entry in uploads],[(1,8192)]*11+[(3,1024),(2,8192)])
            self.assertEqual([entry['caller'] for entry in result['stage_curve_references'][-2:]],[0xa014b234,0xa014b364])
            for row in bands:
                thresholds=row['thresholds'];level=row['level']
                divisor=1<<level
                self.assertEqual((row['geometry']&65535,row['geometry']>>16),((4928+divisor-1)//divisor,(3264+divisor-1)//divisor))
                index=next((i for i,threshold in enumerate(thresholds) if level<threshold),3)
                self.assertEqual(row['selected_pointer'],0x51000000+8192*index)

    def test_original_layout_manager_defers_hdf_admission_while_native_pipeline_reports_busy(self):
        from scripts import analyze_gr2_native_contract as native
        self.assertTrue(hasattr(native,'probe_buffer_layout_manager'))
        for busy in ({},{0x342:2},{0x343:1},{0x344:1},{0x345:1}):
            with self.subTest(busy=busy):
                result=native.probe_buffer_layout_manager(component('gr2','b01firm8'),1,1,busy)
                self.assertEqual(result['transition_requests'],[] if busy else [0])
                self.assertEqual(result['final_layout'],1 if busy else 0)
                self.assertEqual(result['deferred'],int(bool(busy)))
                self.assertTrue(result['effect_property_preserved']);self.assertTrue(result['stack_preserved'])
        result=native.probe_buffer_layout_manager(component('gr2','b01firm8'),0,0,{0x344:1})
        self.assertEqual(result['transition_requests'],[]);self.assertEqual(result['final_layout'],0)

    def test_negative_clarity_grades_change_detail_uploads_but_preserve_postband_tables_and_other_cpu_register_writes(self):
        from scripts import analyze_gr2_native_contract as native
        for geometry in (0x40020,0xcc01340):
            results=[native.probe_clarity_control_graph(component('gr2','b01firm8'),strength,geometry) for strength in (1,2,3,4)]
            self.assertEqual(len({row['non_lut_mmio_sha256'] for row in results}),1)
            post=[[(entry['mode'],entry['read_bytes'],entry['source_sha256']) for entry in row['curve_uploads'][-2:]] for row in results]
            self.assertTrue(all(row==post[0] for row in post))
            self.assertEqual(post[0],[(3,1024,'588eb9934761a8508729c1ab59c25a89fb74138ef8d4964482ac73e23bb8a529'),
                                     (2,8192,'85a821a3d487430c79a42f944b67db8b12a76a8a4f96c66c1c3c8f725bfb3444')])
            self.assertGreater(len({tuple(entry['source_sha256'] for entry in row['curve_uploads'][:-2]) for row in results}),1)
