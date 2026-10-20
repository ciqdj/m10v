"""GR4 export must accept the same bounded EI values as camera/browser state."""
import struct,unittest,zlib
from scripts.build_gr4_m10v_library import default_state,validate_state

class PhoenixExportTests(unittest.TestCase):
    def state(self,film,exposure):
        state=bytearray(default_state())
        struct.pack_into('<H',state,12,film);state[61]=exposure
        struct.pack_into('<I',state,100,zlib.crc32(state[:100]))
        return bytes(state)

    def test_phoenix_ei120_is_accepted_but_other_stocks_cannot_inherit_it(self):
        validate_state(self.state(67,1))
        for film,exposure in [(67,2),(66,1),(73,1),(68,3)]:
            with self.subTest(film=film,exposure=exposure),self.assertRaises(ValueError):
                validate_state(self.state(film,exposure))
