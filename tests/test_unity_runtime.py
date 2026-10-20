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

if __name__=='__main__':unittest.main()
