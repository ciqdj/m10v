"""Original GR4 CPU topology evidence, independent of the injected runtime."""
import unittest
from pathlib import Path

class Gr4NativeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rtos=Path('data/research/gr4/RTOS.bin').read_bytes()
    def test_original_planner_admits_only_synchronized_jpeg_lifetimes(self):
        from scripts.analyze_gr4_native_contract import analyze
        proof=analyze(self.rtos)
        self.assertEqual(proof['allowed_modes'],[0,1,5,6,7,8,12,13,16])
        self.assertEqual(proof['config_offset'],0xb60)
        self.assertEqual(proof['shooting_offset'],0x4688)
        for case in proof['modes']:
            if case['mode'] in proof['allowed_modes']:
                self.assertTrue(case['producer_waits'])
                self.assertTrue(case['jpeg_waits'])
                self.assertTrue(case['cleanup_after_jpeg'])
        self.assertEqual(proof['creator']['main_descriptor'],0xb0)
        self.assertEqual(proof['creator']['request'],0x60006000)
    def test_unknown_identity_is_rejected(self):
        from scripts.analyze_gr4_native_contract import analyze
        with self.assertRaisesRegex(ValueError,'identity'): analyze(bytes(4096))
