"""Independent identity and corruption gates for new model research."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModelInventoryTests(unittest.TestCase):
    def analyzer(self):
        path = ROOT / 'scripts/analyze_model_firmware.py'
        self.assertTrue(path.exists(), 'model firmware inspector is not implemented')
        spec = importlib.util.spec_from_file_location('model_inventory', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @unittest.skipUnless((ROOT / 'bin/fwdc248b-gr4-officical.bin').exists(), 'official GR4 sample missing')
    def test_gr4_exact_image_and_component_inventory(self):
        result = self.analyzer().inspect_gr4((ROOT / 'bin/fwdc248b-gr4-officical.bin').read_bytes())
        self.assertEqual(result['model'], 'GR IV')
        self.assertEqual(result['internal_version'], '1.11.10.7')
        self.assertEqual(result['decoded_bytes'], 67948280)
        self.assertEqual(result['frames'], 2765)
        self.assertEqual(len(result['sections']), 13)
        rtos = next(row for row in result['sections'] if row['name'] == 'RTOS')
        self.assertEqual(rtos['payload_bytes'], 20785856)
        self.assertEqual(rtos['sha256'], 'a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1')
        self.assertTrue(result['proof']['decoded_checksum_valid'])
        self.assertTrue(result['proof']['byte_exact_roundtrip'])
        self.assertFalse(result['hardware_tested'])

    def test_gr4_rejects_unrecognized_and_truncated_images(self):
        inspect = self.analyzer().inspect_gr4
        for data in (b'', b'RICOH' + bytes(200)):
            with self.assertRaisesRegex(ValueError, 'identity|size'):
                inspect(data)

    @unittest.skipUnless((ROOT / 'bin/fwdc248b-gr4-officical.bin').exists(), 'official GR4 sample missing')
    def test_gr4_rejects_modified_source_before_address_analysis(self):
        data = bytearray((ROOT / 'bin/fwdc248b-gr4-officical.bin').read_bytes())
        data[0x2000] ^= 1
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.analyzer().inspect_gr4(bytes(data))


if __name__ == '__main__':
    unittest.main()
