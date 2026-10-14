"""Execute official GR IV instructions to establish the image-buffer ABI."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'bin/fwdc248b-gr4-officical.bin'


@unittest.skipUnless(SAMPLE.exists(), 'official GR IV image missing')
class Gr4CaptureTests(unittest.TestCase):
    def inspector(self):
        path = ROOT / 'scripts/analyze_gr4_capture.py'
        self.assertTrue(path.exists(), 'GR IV capture contract inspector is not implemented')
        spec = importlib.util.spec_from_file_location('gr4_capture_probe', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def rtos(self):
        sys.path.insert(0, str(ROOT / 'vendor/gr4'))
        from gr4_editor.firmware import load_image
        return load_image(SAMPLE).rtos

    def test_official_allocation_carries_full_resolution_main_plane_and_real_padding(self):
        result = self.inspector().analyze(self.rtos())
        self.assertEqual(result['allocation_entry'], '0x5370e804')
        self.assertEqual(result['encoder_call']['target'], '0x538dd430')
        self.assertEqual(result['encoder_call']['caller'], '0x537035c8')
        self.assertEqual(len(result['cases']), 2)
        for case, gap in zip(result['cases'], (905536, 451648)):
            main = case['main']
            self.assertEqual(main['offset'], '0xb0')
            self.assertEqual(main['format'], 1)
            self.assertEqual(main['enum_byte'], 2)
            self.assertEqual(main['padding_bytes'], 'a5a5a5')
            self.assertEqual(main['gap_bytes'], gap)
            self.assertEqual(main['width'], case['input']['width'])
            self.assertEqual(main['height'], case['input']['height'])
            self.assertEqual(main['stride'], case['input']['stride'])
            self.assertEqual(case['preview']['width'], 720)
            self.assertEqual(case['preview']['height'], 480)
            self.assertTrue(case['returned'])
        self.assertEqual(result['cases'][0]['main']['width'], 6256)
        self.assertEqual(result['cases'][0]['main']['height'], 4176)
        self.assertFalse(result['native_bridge_ready'])

    def test_unknown_rtos_is_rejected_before_emulation(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.inspector().analyze(bytes(4096))


if __name__ == '__main__':
    unittest.main()
