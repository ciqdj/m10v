"""Native ABI evidence must execute original wrappers, with hardware boundaries explicit."""
import importlib.util
import unittest
from tests.test_unity_update import ROOT,component

class Gr2NativeContractTests(unittest.TestCase):
    def implementation(self):
        source=ROOT/'scripts/analyze_gr2_native_contract.py'
        self.assertTrue(source.exists(),'GR II native ABI analyzer is missing')
        spec=importlib.util.spec_from_file_location('gr2_native_contract',source)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def test_original_rtc_wrapper_expands_compact_driver_time_to_six_big_endian_halfwords(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for fields in ((2026,10,20,18,30,45),(2000,1,1,0,0,0),(2127,12,31,23,59,59)):
            with self.subTest(fields=fields):
                report=module.probe_rtc_get_time(code,fields)
                self.assertEqual(report['fields'],list(fields))
                self.assertEqual(report['output_hex'],''.join(f'{v:04x}' for v in fields))
                self.assertTrue(report['guards_unchanged'])
                self.assertTrue(report['callee_saved_preserved'])
                self.assertEqual(report['returned'],fields[-1])
                self.assertEqual(report['driver_calls'],1)

    def test_native_contract_rejects_unverified_or_other_model_code(self):
        module=self.implementation()
        with self.assertRaisesRegex(ValueError,'identity'):module.probe_rtc_get_time(bytes(4096),(2026,10,20,1,2,3))
        if (ROOT/'bin/rg1_v051.frm').exists():
            with self.assertRaisesRegex(ValueError,'identity'):module.probe_rtc_get_time(component('gr1','b01firm8'),(2026,10,20,1,2,3))

    def test_original_sd_io_wrappers_preserve_distinct_read_and_write_backend_contracts(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for operation in ('read','write'):
            with self.subTest(operation=operation):
                report=module.probe_sd_io(code,operation,b'M10V\x00config\xff')
                self.assertEqual(report['returned'],12)
                self.assertEqual(report['transferred_hex'],b'M10V\x00config\xff'.hex())
                self.assertTrue(report['guards_unchanged'])
                self.assertEqual(report['backend_items'],12 if operation=='read' else 1)
                self.assertEqual(report['backend_item_bytes'],1 if operation=='read' else 12)

    def test_original_sd_open_translates_bit_flags_to_backend_modes(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        code=component('gr2','b01firm8')
        for flags,mode in ((0,'r'),(1,'w'),(9,'a'),(2,'r+'),(10,'a+'),(0x102,'w+')):
            with self.subTest(flags=flags):
                report=module.probe_sd_open_mode(code,flags)
                self.assertEqual(report['mode'],mode)
                self.assertEqual(report['path'],'H:/M10V.BIN')
                self.assertFalse(report['opened'])

    def test_read_wrapper_returns_short_count_at_eof_without_touching_tail(self):
        module=self.implementation()
        if not (ROOT/'bin/rg2_v003.frm').exists():self.skipTest('official GR II sample missing')
        report=module.probe_sd_io(component('gr2','b01firm8'),'read',b'12345678',read_count=3)
        self.assertEqual(report['returned'],3)
        self.assertEqual(report['buffer_hex'],b'123'.hex()+'a5'*5)
        self.assertTrue(report['guards_unchanged'])
