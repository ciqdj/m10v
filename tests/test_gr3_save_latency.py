"""Real Still Make -> recipe completion using the encoder's ShootingInfo tone.

No assertion here translates emulated instructions into camera save seconds.
"""
import json
import os
import struct
from pathlib import Path
import unittest
from tests import test_gr3_appended_recipe as appended
from tests.test_gr3_isp_recipe_color import state
from unicorn import arm_const as A
from unicorn import UC_HOOK_CODE


class SaveLatencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        appended.AppendedRecipeTests.setUpClass.__func__(cls)
        folder = os.environ.get('M10V_APPENDED_CANDIDATE')
        cls.full = json.loads((Path(folder) / 'gr3/manifest.json').read_text()) if folder else None

    fixture = appended.AppendedRecipeTests.fixture
    snapshot = appended.AppendedRecipeTests.snapshot
    callback = appended.AppendedRecipeTests.callback
    status = appended.AppendedRecipeTests.status

    def complete(self, e, recipe, si, data):
        source = e.alloc(104)
        e.u.mem_write(source, data)
        # This is precisely what m10v_capture_library reads, not the stage-1
        # sub-shot tone at SI+71248+77c used by the tuning callback.
        tone = e.u.mem_read(si + 0x77c, 1)[0]
        e.call(self.manifest['exports']['m10v_isp_frame_recipe_completed'],
               recipe, si, tone, source)
        return e.u.reg_read(A.UC_ARM_REG_R0)

    def test_stage1_completion_uses_encoder_identity_when_subshot_tone_differs(self):
        for film in (33, 35, 66, 67, 68, 69, 78):
            with self.subTest(film=film):
                e, r, o, i, c, si = self.fixture(25, 1)
                e.u.mem_write(si + 0x77c, bytes([26]))
                data = state((film,) * 5)
                self.snapshot(e, r, data)
                shooting = bytes(e.u.mem_read(si, 0x80000))
                self.callback(e, o, i, c)
                self.assertEqual(self.status(e, r), 2)
                self.assertEqual(self.complete(e, r, si, data), 1)
                self.assertEqual(bytes(e.u.mem_read(si, 0x80000)), shooting)

    def test_stock_bases_keep_color_preserving_fallback(self):
        for previous in (11, 12, 15, 22):
            e, r, o, i, c, si = self.fixture(previous)
            data = state((67,) * 5)
            self.snapshot(e, r, data)
            e.u.mem_write(r + 0x4a08 + 22, struct.pack('<H', 25))
            self.callback(e, o, i, c)
            self.assertEqual(self.complete(e, r, si, data), 0)

    def test_delivered_native_make_to_24mp_encoder_never_touches_planes_or_heap(self):
        if not self.full:
            self.skipTest('requires final BIN via M10V_APPENDED_CANDIDATE')
        for film in range(33, 79):
            for stage, previous in ((0, 25), (1, 26)):
                with self.subTest(film=film, stage=stage, previous=previous):
                    e, r, o, i, c, si = self.fixture(25 if stage else previous, stage)
                    e.u.mem_write(si + 0x77c, bytes([previous]))
                    data = state((film,) * 5)
                    self.snapshot(e, r, data)
                    e.u.mem_write(r + 0x4a08 + 22, struct.pack('<H', 25))
                    self.callback(e, o, i, c)
                    req = e.alloc(16)
                    raw_dims = e.alloc(4)
                    e.u.mem_write(raw_dims, struct.pack('<HH', 6112, 4064))
                    for off, value in ((0x18, 0), (0x5c, req), (0x60, 0x70000000),
                                       (0x230, raw_dims), (0x44c8, si)):
                        e.w32(r + off, value)
                    ctx = r + 0x9b8
                    for off, value in ((0, 0x53d0fbe0), (0x30, r+0x1a8),
                                       (0x34, si), (0x38, req), (0x3c, r+0xb0),
                                       (0x48, r+0x110), (0x4c, r+0x130)):
                        e.w32(ctx + off, value)
                    e.w32(req, 0x53d0fe60)
                    e.u.mem_write(req + 12, bytes([1, 1]))
                    e.u.mem_write(r+0x140, bytes([1]))
                    # Valid 24MP addresses, deliberately NOT mapped. Any
                    # software pixel read or write faults instead of hiding
                    # behind a mocked completion mask or tiny image timing.
                    e.u.mem_write(r+0xb0, struct.pack('<4I8H', 1, 0x64000000,
                                  0x66000000, 0, 6000, 4000, 6000, 4000, 0, 0, 2, 0))
                    e.u.mem_write(r+0x110, struct.pack('<4I8H', 1, 0x55050000,
                                  0x55060000, 0, 64, 48, 64, 48, 0, 0, 2, 0))
                    forbidden = {0x536af2a8, 0x536af2e4, 0x5383c8a8,
                                 self.full['symbols']['m10v_camera_library_load']}
                    def guard(u, at, size, unused):
                        self.assertNotIn(at, forbidden, 'unexpected CPU fallback/cache/heap/IO')
                    hook = e.u.hook_add(UC_HOOK_CODE, guard)
                    e.call(self.full['symbols']['m10v_capture_library'], ctx)
                    e.u.hook_del(hook)
                    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0), 0)

    def test_frozen_stock_selection_still_rejects_a_lagging_film_frame(self):
        e, r, o, i, c, si = self.fixture(25)
        data = state((67,) * 5)
        self.snapshot(e, r, data)
        e.u.mem_write(r + 0x4a08 + 22, struct.pack('<H', 11))
        self.callback(e, o, i, c)
        self.assertEqual(self.complete(e, r, si, data), 0)
