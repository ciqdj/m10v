import os
import unittest
from pathlib import Path
from scripts.analyze_gr3_800t_chroma import inspect_chroma, validate_identity


class ChromaIdentityTests(unittest.TestCase):
    def test_unknown_and_truncated_firmware_cannot_be_proof(self):
        for data in (b'', bytes(64), bytes(0x8000)):
            with self.assertRaisesRegex(ValueError, 'identity'):
                validate_identity(data)


@unittest.skipUnless(os.environ.get('GR3_RTOS_PATH'), 'set GR3_RTOS_PATH to locked decoded RTOS')
class OriginalChromaExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rtos = Path(os.environ['GR3_RTOS_PATH']).read_bytes()
        cls.report = inspect_chroma(cls.rtos)

    def test_actual_converter_identifies_components_neutral_and_extremes(self):
        self.assertEqual(len(self.report['pixel_cases']), 9)
        self.assertEqual(self.report['execution']['calls_stubbed'], 0)
        self.assertEqual(self.report['contract']['combined_order'], 'CbCr')
        self.assertEqual(self.report['contract']['neutral'], 128)

    def test_both_formats_preserve_extremes_and_allocation_padding(self):
        rows = self.report['fill_adapter_cases']
        self.assertEqual(len(rows), 28)
        self.assertEqual({row['low_format'] for row in rows}, {1, 2})
        for row in rows:
            self.assertEqual(row['combined_first_pair'], row['input_YCbCr'][1:])
            self.assertTrue(row['padding_unchanged'])

    def test_independent_consumer_shares_chroma_over_two_rows(self):
        pixels = self.report['independent_420_consumer_RGBA']
        self.assertEqual(pixels[:4], pixels[4:])
        self.assertGreater(pixels[0][2], pixels[0][0])
        self.assertGreater(pixels[2][0], pixels[2][2])

    def test_one_byte_firmware_change_is_rejected(self):
        modified = bytearray(self.rtos)
        modified[0x6c9450] ^= 1
        with self.assertRaisesRegex(ValueError, 'identity'):
            inspect_chroma(modified)
