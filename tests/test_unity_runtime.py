"""Verify the module loader's original copy/zero/deferred-record instructions."""
import importlib.util
from pathlib import Path
import unittest
from tests.test_unity_update import component,ROOT

def implementation():
    source=ROOT/'scripts/analyze_unity_runtime.py'
    if not source.exists():raise AssertionError('official loading-chain analyzer is missing')
    spec=importlib.util.spec_from_file_location('unity_runtime_analysis',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class UnityRuntimeTests(unittest.TestCase):
    def test_gr2_original_loader_copies_first_fifteen_records_clears_aux_and_defers_last(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=implementation().analyze_runtime(component('gr2','b01firm8'),'gr2')
        self.assertEqual(report['entry_field'],'0xa0020400')
        rows=report['load_records'];self.assertEqual(len(rows),16)
        self.assertEqual(rows[0]['source_file_offset'],512)
        self.assertEqual(rows[0]['address'],0xa0020400);self.assertEqual(rows[0]['length'],0xa46c4)
        self.assertEqual(rows[0]['zero_address'],0xa05f5800);self.assertEqual(rows[0]['zero_length'],0xc5700)
        self.assertEqual(rows[15]['address'],0x400);self.assertEqual(rows[15]['mode'],'deferred')
        proof=report['loader_cpu']
        self.assertTrue(proof['all_records_processed']);self.assertTrue(proof['direct_bytes_match'])
        self.assertTrue(proof['aux_zeroed']);self.assertTrue(proof['guards_unchanged'])
        self.assertTrue(proof['deferred_buffer_matches']);self.assertTrue(proof['low_target_unchanged'])
        self.assertEqual(proof['loaded_indices'],list(range(16)))
        self.assertEqual(proof['deferred_record']['address'],0x400)
        self.assertFalse(report['deferred_commit_proved'])
        self.assertEqual(report['indexed_loader_cpu']['returned'],0)
        self.assertEqual(report['startup_cpu']['module_indices'][-1],14)
        self.assertEqual(report['rom_capacity_cpu'][0]['capacity_bytes'],0x81fc00)
        self.assertEqual(report['rom_capacity_cpu'][1]['capacity_bytes'],0x7ffc00)

    def test_gr2_loader_probe_detects_partial_reads_even_if_entry_looks_valid(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        module=implementation();code=component('gr2','b01firm8')
        proof=module.probe_loader(code,'gr2',short_read_index=3)
        self.assertFalse(proof['all_records_processed'])
        self.assertEqual(proof['loaded_indices'],[0,1,2])
        self.assertFalse(proof['direct_bytes_match'])

    def test_cross_model_code_cannot_supply_loading_addresses(self):
        module=implementation()
        with self.assertRaisesRegex(ValueError,'identity'):module.analyze_runtime(bytes(4096),'gr2')
        if (ROOT/'bin/rg1_v051.frm').exists():
            with self.assertRaisesRegex(ValueError,'identity'):module.analyze_runtime(component('gr1','b01firm8'),'gr2')

    def test_gr_uses_its_own_loader_and_aux_ranges(self):
        if not (ROOT/'bin/rg1_v051.frm').exists():self.skipTest('official GR sample missing')
        report=implementation().analyze_runtime(component('gr1','b01firm8'),'gr1')
        self.assertEqual(report['loader_cpu']['loop_entry'],'0xa003f0fa')
        self.assertTrue(report['loader_cpu']['all_records_processed'])
        self.assertTrue(report['loader_cpu']['aux_zeroed'])
        self.assertTrue(report['loader_cpu']['deferred_buffer_matches'])
        self.assertEqual(report['load_records'][0]['length'],0xa1b00)
        self.assertEqual(report['load_records'][0]['zero_address'],0xa05aa400)
        self.assertEqual(report['load_records'][0]['zero_length'],0x105a90)

    def test_load_map_rejects_source_overlap_destination_overlap_and_entry_in_a_gap(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        module=implementation();code=component('gr2','b01firm8')
        parse=module.parse_executable_load_map
        self.assertEqual(len(parse(code)),16)
        # These deliberately invalidate checksums: this tests the independent map
        # gate, not the identity/checksum gate which runs before it in production.
        import struct
        for offset,value,reason in ((0x34,0,'source.*overlap'),(0x38,0xa0020400,'destination.*overlap'),
                                    (0x40,0xa0020400,'zero.*overlap'),(0x160,0xa00c4b00,'entry'),
                                    (0x20+15*20,0xfffffe00,'source.*bounds')):
            changed=bytearray(code);struct.pack_into('>I',changed,offset,value)
            with self.subTest(offset=hex(offset)),self.assertRaisesRegex(ValueError,reason):parse(bytes(changed))

    def test_gr2_startup_indexed_loader_reads_sectors_copies_tails_and_clears_aux(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        module=implementation();code=component('gr2','b01firm8')
        for offset,length in ((0,1),(0,512),(0,513),(1,513),(511,1025),(512,1024)):
            with self.subTest(offset=offset,length=length):
                report=module.probe_gr2_indexed_loader(code,source_offset=offset,length=length)
                self.assertEqual(report['returned'],0)
                self.assertTrue(report['payload_matches']);self.assertTrue(report['aux_zeroed'])
                self.assertTrue(report['guards_unchanged']);self.assertTrue(report['loaded'])
                self.assertEqual(report['entry_out'],0x52001000)

    def test_gr2_startup_indexed_loader_does_not_mark_failed_io_loaded(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        module=implementation();code=component('gr2','b01firm8')
        report=module.probe_gr2_indexed_loader(code,source_offset=1,length=1025,fail_read=1)
        self.assertEqual(report['returned'],0xffffffff)
        self.assertFalse(report['loaded']);self.assertEqual(report['entry_out'],0xdeadbeef)
        invalid=module.probe_gr2_indexed_loader(code,record_index=16)
        self.assertEqual(invalid['returned'],0xffffffff);self.assertEqual(invalid['reads'],[])

    def test_gr2_startup_loads_record_14_before_the_common_post_load_call(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=implementation().probe_gr2_startup_order(component('gr2','b01firm8'))
        self.assertEqual(report['module_indices'],[0,1,4,2,3,5,10,11,8,9,6,12,13,14])
        self.assertEqual(report['post_load_call'],'0xa0020ab4')
        self.assertEqual(report['events'][-5:-3],[['module',14],['post_load',0]])
        self.assertEqual(report['returned'],0)

    def test_gr2_early_startup_branches_still_load_record_14(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        module=implementation();code=component('gr2','b01firm8')
        early=module.probe_gr2_startup_order(code,phase_results={1:2})
        self.assertEqual(early['module_indices'],[0,1,14])
        for outcomes in ({1:1},{1:1,2:2},{8:2},{9:2},{6:2},{12:2},{13:2}):
            with self.subTest(outcomes=outcomes):
                report=module.probe_gr2_startup_order(code,phase_results=outcomes)
                self.assertEqual(report['module_indices'][-1],14)
                self.assertEqual(report['events'][-5:-3],[['module',14],['post_load',0]])

    def test_gr2_original_module_wrapper_skips_reloading_a_completed_record(self):
        module=implementation();self.assertTrue(hasattr(module,'probe_gr2_module_guard'))
        for loaded,calls in ((False,[[14,0]]),(True,[])):
            with self.subTest(loaded=loaded):
                result=module.probe_gr2_module_guard(component('gr2','b01firm8'),loaded=loaded)
                self.assertEqual(result['indexed_load_requests'],calls)
                self.assertTrue(result['reached_guard_continuation'])

    def test_gr2_original_rom_size_policy_keeps_exact_capacity_boundaries(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        module=implementation();code=component('gr2','b01firm8')
        for kind,capacity in ((1,0x81fc00),(2,0x7ffc00)):
            with self.subTest(kind=kind):
                valid=module.probe_gr2_rom_capacity(code,kind,capacity)
                self.assertEqual(valid['capacity_bytes'],capacity);self.assertEqual(valid['returned'],0)
                self.assertEqual(valid['block_bytes'],131072)
                invalid=module.probe_gr2_rom_capacity(code,kind,capacity+1)
                self.assertEqual(invalid['returned'],0xffffffff)


    def test_gr2_original_post_load_stub_preserves_final_initialization_callbacks(self):
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=implementation().probe_gr2_startup_order(component('gr2','b01firm8'))
        self.assertEqual(report['post_load_return'],0xffffffff)
        self.assertEqual(report['events'][-4:],[['post_load',0],['phase',0],['phase',0xffffffff],['finalize',0xffffffff]])
        self.assertNotIn('0xa0023234',report['helpers_intercepted'])
