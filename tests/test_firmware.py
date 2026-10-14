import hashlib
from pathlib import Path
import unittest

from m10v_core.firmware import FirmwareIdentityError, inspect_official, _noop_repack


SAMPLE = Path(__file__).resolve().parents[1] / 'fwdc239b.bin'
SHA = 'd6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4'


@unittest.skipUnless(SAMPLE.exists(), 'local official sample unavailable')
class FirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = SAMPLE.read_bytes()

    def test_exact_official_report(self):
        report = inspect_official(self.data)
        self.assertEqual((report.model, report.internal_version, report.public_version),
                         ('GR III', '2.10.21.27', '2.10'))
        self.assertEqual((report.sha256, report.size, len(report.sections)), (SHA, 30391780, 14))
        self.assertEqual(report.sections[0].name, 'BOOTPARA')
        self.assertEqual(report.sections[-2].name, 'FDRVPARA')
        self.assertTrue(all(report.proof.values()))

    def test_changed_byte_rejected(self):
        changed = bytearray(self.data)
        changed[200] ^= 1
        with self.assertRaises(FirmwareIdentityError):
            inspect_official(bytes(changed))

    def test_wrong_project_rejected(self):
        changed = bytearray(self.data)
        changed[48:52] = (636).to_bytes(4, 'little')
        with self.assertRaises(FirmwareIdentityError):
            inspect_official(bytes(changed))

    def test_truncated_frame_rejected(self):
        with self.assertRaises(FirmwareIdentityError):
            inspect_official(self.data[:-100])

    def test_internal_noop_repack_matches_exact_official_bytes(self):
        rebuilt = _noop_repack(self.data)
        self.assertEqual(hashlib.sha256(rebuilt).hexdigest(), SHA)
        self.assertEqual(rebuilt, self.data)
