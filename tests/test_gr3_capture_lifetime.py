"""Locked stock-image lifetime contracts. Synthetic ARM probes are not camera QA."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('capture_lifetime',ROOT/'scripts/analyze_gr3_capture_lifetime.py')
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)

class CaptureLifetimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        image=ROOT/MODULE.DEFAULT
        if not image.exists():raise unittest.SkipTest('locked stock RTOS fixture unavailable')
        cls.image=image.read_bytes()
        if hashlib.sha256(cls.image).hexdigest()!=MODULE.SHA:raise AssertionError('wrong stock RTOS fixture')
    def word(self,address):return struct.unpack_from('<I',self.image,address-MODULE.BASE)[0]
    def test_virtual_setter_and_raw_case(self):
        self.assertEqual(self.word(0x53d0fc90+0x70),0x5350d7e8)
        # id1 is decremented to switch index0; this table word is data.
        self.assertEqual(self.word(0x5350d810),0x5350d878)
        self.assertEqual(self.word(0x53d5edcc),0xffffffff)
    def test_original_arm_results(self):
        probes=MODULE.probe_original(self.image)
        self.assertEqual([x['raw_source'] for x in probes['setter']],['0x0','0x70000100'])
        self.assertEqual(len(probes['callback']),12)
        for row in probes['callback']:
            self.assertEqual(row['r0'],0)
            self.assertEqual(row['stored_success'],{0:1,1:0,2:0,3:0x7f}[row['status']])
        self.assertEqual(len(probes['wait']),6)
        for row in probes['wait']:
            self.assertEqual(row['kernel_call']['stack0'],row['input_timeout'])
            self.assertEqual(row['bool_return'],int(row['kernel_return']=='0x0'))

if __name__=='__main__':unittest.main()
