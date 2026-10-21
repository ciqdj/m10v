"""Research-only component assembly must preserve model-specific load ownership."""
import copy
import importlib.util
import struct
import unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import ROOT,component

class Gr2ComponentTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build

    def implementation(self):
        source=ROOT/'scripts/build_gr2_component.py'
        self.assertTrue(source.exists(),'research GR II component assembler is missing')
        spec=importlib.util.spec_from_file_location('gr2_component',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def test_source_component_preserves_update_policy_existing_records_and_deferred_payload(self):
        from scripts.analyze_unity_runtime import parse_executable_load_map
        from scripts.analyze_unity_update import compute_update_checksum
        module=self.implementation();runtime=self.build();official=component('gr2','b01firm8')
        candidate,audit=module.build_gr2_component(official,runtime)
        before=parse_executable_load_map(official);after=parse_executable_load_map(candidate)
        self.assertFalse(audit['can_package']);self.assertFalse(audit['activation_ready'])
        self.assertEqual(candidate[0x170:0x180],official[0x170:0x180]);self.assertEqual(after[15],before[15])
        self.assertEqual(after[0]['length'],before[0]['length']+44)
        self.assertEqual(after[14]['address'],runtime['base']);self.assertEqual(after[14]['length'],runtime['code_bytes'])
        self.assertEqual(after[14]['zero_length'],runtime['memory_bytes']-runtime['code_bytes'])
        for index in range(1,14):
            for field in ('source_field','address','length','zero_address','zero_length'):
                self.assertEqual(after[index][field],before[index][field])
        self.assertEqual(struct.unpack_from('>I',candidate,0x16c)[0],compute_update_checksum(candidate[512:]))
        self.assertLessEqual(len(candidate),0x81fc00)
        self.assertEqual(candidate[after[14]['source_file_offset']:after[14]['source_file_offset']+after[14]['length']],bytes.fromhex(runtime['runtime_hex']))

    def test_original_updater_accepts_the_complete_modified_component_payload(self):
        from scripts.analyze_unity_update import execute_update_checksum
        module=self.implementation();runtime=self.build();official=component('gr2','b01firm8')
        candidate,audit=module.build_gr2_component(official,runtime)
        proof=execute_update_checksum(official,'gr2',candidate[512:],audit['weighted_checksum'],initial_position=struct.unpack_from('>I',candidate,0x20)[0])
        self.assertTrue(proof['accepted']);self.assertEqual(proof['computed_checksum'],audit['weighted_checksum'])

    def test_actual_candidate_header_and_module_sources_follow_early_bootstrap(self):
        from scripts.analyze_unity_runtime import probe_gr2_startup_order
        module=self.implementation();runtime=self.build();official=component('gr2','b01firm8')
        candidate,_=module.build_gr2_component(official,runtime)
        proof=probe_gr2_startup_order(official,native_runtime=runtime,early_native=True,candidate_component=candidate)
        self.assertEqual(proof['returned'],0);self.assertEqual(proof['native_load_count'],1)
        self.assertEqual(proof['native_bss_canary'],0x12345678);self.assertTrue(proof['original_stub_restored'])
        self.assertTrue(proof['stack_preserved']);self.assertTrue(proof['callee_saved_preserved'])
        self.assertTrue(proof['candidate_reservations_loaded'])
        self.assertEqual(proof['candidate_loaded_records'],sorted(set(proof['module_indices'])))
        self.assertLess(proof['events'].index(['native_early_load',14]),proof['events'].index(['phase',1]))

    def test_corrupt_or_wrong_model_inputs_and_unsafe_runtime_reports_are_rejected(self):
        module=self.implementation();runtime=self.build();official=component('gr2','b01firm8')
        for change in ('digest','base','endianness','gate'):
            bad=copy.deepcopy(runtime)
            if change=='digest':bad['runtime_sha256']='0'*64
            elif change=='base':bad['base']+=4
            elif change=='endianness':bad['endianness']='little'
            else:bad['can_package']=True
            with self.subTest(change=change),self.assertRaises(ValueError):module.build_gr2_component(official,bad)
        with self.assertRaises(ValueError):module.build_gr2_component(component('gr1','b01firm8'),runtime)
