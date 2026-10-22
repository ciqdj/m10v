"""Global HDF inherits the original JPEG phase and shared scratch ownership."""
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2HdfPostprocessTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    def test_global_grades_preserve_native_effects_hdr_and_two_block_scratch_budget(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        runtime=self.build();self.assertIn('gr2_hdf_postprocess',runtime['symbols'])
        for strength in (0,1,2,3):
            for effect in range(21):
                stock={7:[4],12:[5],16:[13],17:[14],19:[15]}.get(effect,[])
                with self.subTest(strength=strength,effect=effect):
                    result=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,postprocess_effect=effect,
                                                     postprocess_original_prepare=True,postprocess_hdf=strength)
                    post=result['postprocessor'];extra=bool(strength and effect not in (16,19))
                    self.assertEqual([row['operation'] for row in post['packets']],stock+([13] if extra else []))
                    self.assertTrue(post['primary_retained']);self.assertTrue(post['property_counters_balanced']);self.assertTrue(post['ring_restored'])
                    self.assertEqual(post['reserved_after'],0);self.assertLessEqual(post['peak_jpeg_blocks'],2)
                    self.assertTrue(all(row['stage6'] for row in post['preparation_trace']))
                    if strength:self.assertNotEqual(post['reserved_before'],0)
                    self.assertEqual(len(post['preparation_trace']),2 if strength or effect in (12,16,17,19) else 1)
                    self.assertEqual(post['postprocess_return'],post['original_returns'][0])
                    self.assertEqual(post['hdf_after'],[0x10000|strength,77])
                    if extra:
                        packet=post['packets'][-1];self.assertEqual(packet['native_workspace_bytes'],0xe5800)
                        self.assertEqual(packet['core_request'][3:5],[4960,2496]);self.assertEqual(packet['core_request'][10],0xcc01340)

    def test_global_and_stock_clarity_execute_original_drivers_in_the_same_owned_capture_chain(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        from collections import Counter
        runtime=self.build()
        for effect in (0,16):
            result=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,postprocess_effect=effect,
                                             postprocess_original_prepare=True,postprocess_hdf=3,postprocess_execute_hdf=True,postprocess_clarity_strength=9)
            post=result['postprocessor'];dsp=post['dsp'];workspace=post['packets'][-1]['scratch'][0]
            self.assertEqual(dsp['graph_calls'],1)
            self.assertEqual(dsp['bands'],[[level,workspace+0xe040+(level-1)*8192] for level in range(11,0,-1)])
            self.assertEqual(Counter(dsp['resources_acquired']),Counter(dsp['resources_released']))
            self.assertTrue(post['primary_retained']);self.assertTrue(post['ring_restored']);self.assertTrue(post['property_counters_balanced'])
            self.assertEqual(post['clarity_strength_after'],9);self.assertEqual(post['peak_jpeg_blocks'],2)
            self.assertEqual(post['postprocess_return'],post['original_returns'][0]);self.assertTrue(result['stack_preserved'])
            self.assertGreater(result['cpu_stack_write_bytes'],0);self.assertLess(result['cpu_stack_write_bytes'],0x3000)

    def test_global_capture_uses_original_ring_and_fixed_scratch_layouts_without_rebuilding_live_pools(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        runtime=self.build()
        for bank in range(5):
            with self.subTest(bank=bank):
                result=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,initial_layout=bank,
                                                 postprocess_effect=0,postprocess_hdf=3)
                post=result['postprocessor'];self.assertEqual([row['operation'] for row in post['packets']],[] if bank==1 else [13])
                self.assertTrue(post['primary_retained']);self.assertTrue(post['ring_restored']);self.assertTrue(post['property_counters_balanced'])
                self.assertTrue(result['stack_preserved']);self.assertEqual(post['peak_jpeg_blocks'],1 if bank==1 else 2)

    def test_original_two_pass_isp_keeps_one_snapshot_when_ui_publishes_between_passes(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        runtime=self.build()
        post=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,postprocess_effect=13,
                                           postprocess_original_prepare=True,postprocess_production_epoch=True)['postprocessor']
        passes=post['epoch']['passes'];self.assertEqual(len(passes),2)
        self.assertEqual(passes[0]['argument'],0);self.assertNotEqual(passes[1]['argument'],0)
        self.assertTrue(all(row['read']==1 and row['values']==[0x10001,10] for row in passes))
        self.assertEqual(post['epoch']['publication'],1);self.assertEqual(post['hdf_after'],[0x10001,10])
        self.assertEqual([row['operation'] for row in post['packets']],[13])
        self.assertTrue(post['primary_retained']);self.assertTrue(post['ring_restored']);self.assertTrue(post['property_counters_balanced'])

    def test_global_allocation_failures_release_inserted_and_retained_handles_before_return(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        runtime=self.build()
        for tag in (0x17,0x20,0x2e):
            result=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,postprocess_effect=0,
                                             postprocess_original_prepare=False,postprocess_hdf=3,postprocess_fail_tag=tag)
            post=result['postprocessor'];self.assertEqual(post['allocation_faults'],[tag]);self.assertEqual(post['packets'],[])
            self.assertEqual(post['reserved_after'],0);self.assertTrue(post['primary_retained']);self.assertTrue(post['ring_restored'])
            self.assertTrue(post['property_counters_balanced']);self.assertEqual(post['postprocess_return'],post['original_returns'][0])

    def test_alias_metadata_failure_retires_early_reserved_block_without_changing_primary(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        runtime=self.build()
        post=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,postprocess_effect=0,
                                        postprocess_original_prepare=True,postprocess_hdf=3,postprocess_fail_alias=True)['postprocessor']
        self.assertEqual(post['allocation_faults'],['alias']);self.assertEqual(post['packets'],[])
        self.assertNotEqual(post['reserved_before'],0);self.assertEqual(post['reserved_after'],0)
        self.assertTrue(post['primary_retained']);self.assertTrue(post['property_counters_balanced']);self.assertTrue(post['ring_restored'])
        self.assertEqual(post['postprocess_return'],post['original_returns'][0])
