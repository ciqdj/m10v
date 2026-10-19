"""Instruction-work budgets for the saved JPEG path, not camera latency claims.

Runs the real linked Cortex-A9 ARM code. Block sizes bound executed work;
conditional ARM instructions count even when their predicate is false.
"""
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unicorn import UC_HOOK_BLOCK
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_library_arm as arm_tests


class CaptureWorkBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.manifest = build(Path(cls.tmp.name))
        cls.code = (Path(cls.tmp.name) / 'm10v-library-arm.bin').read_bytes()

    def test_default_slow_films_stay_within_saved_image_work_budgets(self):
        # Full-width rows exercise the actual grain lattice rather than
        # thumbnail resampling. A dark scene must not composite an empty halo.
        # These budgets cover the selected defaults:
        # 800T halation, 5207 LUT+grain, Phoenix LUT+grain+halation.
        for film, budget in ((33, 100), (66, 350), (67, 400)):
            with self.subTest(film=film):
                h = arm_tests.FilmLibraryArmTests()
                h.manifest, h.code = self.manifest, self.code
                u = h.machine()
                h.call(u, 'm10v_library_init', 0x55001000)
                h.call(u, 'm10v_camera_library_select', 0x55001000, 1, film)
                width, height = 6000, 2
                pixels = width * height
                u.mem_write(0x55010000, bytes([64]) * pixels)
                u.mem_write(0x55020000, bytes([122, 143]) * (pixels // 2))
                u.mem_write(0x55003000, struct.pack('<7I', 0x55010000,
                    0x55020000, pixels, pixels, width, height, width))
                work = [0]
                def block(uc, address, size, data):
                    work[0] += size // 4
                hook = u.hook_add(UC_HOOK_BLOCK, block)
                self.assertEqual(h.call(u, 'm10v_library_render', 0x55003000,
                    0x55001000, 1, 0, 42, 0x55080000, 6 * pixels), 0)
                u.hook_del(hook)
                print(json.dumps({'film': film, 'arm_instructions': work[0],
                    'instructions_per_pixel': round(work[0] / pixels, 2)}), flush=True)
                self.assertLess(work[0], budget * pixels)
