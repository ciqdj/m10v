"""Native stock amplitude, with no CPU noise-size rewrite or software fallback."""
import os
import hashlib
import json
from pathlib import Path
import struct
import unittest
import zlib
from tests import test_gr3_native_recipe_handoff as prior
from tests.test_gr3_isp_recipe_color import state
from unicorn import arm_const as A


class NativeGrainOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact=os.environ.get('M10V_APPENDED_CANDIDATE')
        cls.tone=25 if artifact else 12
        if artifact:
            from tests.test_gr3_appended_recipe import AppendedRecipeTests
            AppendedRecipeTests.setUpClass.__func__(cls)
            folder=Path(artifact)/'gr3'
            receipt=json.loads((folder/'receipt.json').read_text())
            assert hashlib.sha256((folder/'fwdc239b.bin').read_bytes()).hexdigest()==receipt['candidate_sha256']
        else:
            prior.NativeRecipeHandoffTests.setUpClass.__func__(cls)

    fixture = prior.NativeRecipeHandoffTests.fixture
    snapshot = prior.NativeRecipeHandoffTests.snapshot
    callback = prior.NativeRecipeHandoffTests.callback
    status = prior.NativeRecipeHandoffTests.status

    def test_retired_cpu_noise_rewriter_has_no_runtime_export(self):
        self.assertNotIn('m10v_isp_frame_recipe_grain_noise', self.manifest['exports'])
        self.assertNotIn('m10v_isp_native_effects_noise_shape', self.manifest['exports'])

    def test_old_grain_size_does_not_change_native_plan_or_completion(self):
        for film in (67, *range(291,298)):
            for size in (0, 1, 2):
                for grain in (1, 2, 3):
                    e, r, o, i, c, si = self.fixture(self.tone)
                    data = bytearray(state((film,) * 5))
                    data[14] = grain
                    data[56] = size
                    struct.pack_into('<I', data, 100, zlib.crc32(data[:100]))
                    self.snapshot(e, r, data)
                    digital = r + 0x4320
                    e.u.mem_write(digital, bytes(e.u.mem_read(c, 0x40)))
                    e.w32(digital, 0x53d0fc60)
                    params, values = e.alloc(0x40), e.alloc(12)
                    e.w32(params + 0x10, values)
                    exports = self.manifest['exports']
                    for phase in (0, 1):
                        e.call(exports['m10v_isp_frame_recipe_grain_settings'], digital, params, phase)
                        self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0), 1)
                        self.assertEqual(struct.unpack('<h', e.u.mem_read(values + 4, 2))[0], 4 - grain)
                    self.assertEqual(struct.unpack('<I', e.u.mem_read(r + 0x4a08 + 40 + 16, 4))[0], 0)
                    e.call(exports['m10v_isp_frame_recipe_grain_done'], digital, params, 1)
                    src = e.alloc(104)
                    e.u.mem_write(src, bytes(data))
                    e.call(exports['m10v_isp_frame_recipe_completed'], r, si, self.tone, src)
                    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0), 2)
