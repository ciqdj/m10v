"""Initial GR III/IIIx firmware state must retain the chosen Phoenix EI."""
import struct
import tempfile
import unittest
import zlib
from scripts.build_gr3_m10v_library import build
from scripts.build_gr4_m10v_library import default_state


class PhoenixExportTests(unittest.TestCase):
    def state(self, film, exposure):
        state = bytearray(default_state())
        struct.pack_into('<H', state, 12, film)
        state[61] = exposure
        struct.pack_into('<I', state, 100, zlib.crc32(state[:100]))
        return bytes(state)

    def test_initial_phoenix_ei120_survives_build(self):
        state = self.state(67, 1)
        with tempfile.TemporaryDirectory() as directory:
            manifest = build(directory, initial_state_hex=state.hex())
        self.assertEqual(bytes.fromhex(manifest['initial_state_hex']), state)

    def test_exposure_is_bounded_for_each_stock(self):
        with tempfile.TemporaryDirectory() as directory:
            for film, exposure in [(67, 2), (66, 1), (73, 1), (68, 3)]:
                with self.subTest(film=film, exposure=exposure), self.assertRaises(ValueError):
                    build(directory, initial_state_hex=self.state(film, exposure).hex())
