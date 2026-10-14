"""M10V capture adapter ARM tests with explicit camera-service boundaries."""
import ctypes as C
import struct
import tempfile
import unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_PC, UC_ARM_REG_LR
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_library_arm as arm_tests
from tests import test_gr3_m10v_library as host_tests


class M10VCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.manifest = build(Path(cls.tmp.name)); cls.code = (Path(cls.tmp.name) / 'm10v-library-arm.bin').read_bytes()
        host_tests.NativeFilmLibraryTests.setUpClass(); cls.addClassCleanup(host_tests.NativeFilmLibraryTests.doClassCleanups)

    def fixture(self, tone=18, jpeg=1, raw=0, raw_alias=False, allocation=True, raw_bank=0x60000000, film=2):
        h = arm_tests.FilmLibraryArmTests(); h.manifest = self.manifest; h.code = self.code; u = h.machine()
        for address in (0x536af000, 0x5383c000, 0x532b3000): u.mem_map(address, 4096)
        cache = []; frees = []
        def camera(uc, address, size, data):
            if address == 0x536af2a8:
                self.assertLessEqual(uc.reg_read(UC_ARM_REG_R0), 589824)
                uc.reg_write(UC_ARM_REG_R0, 0x550b0000 if allocation else 0)
            elif address == 0x536af2e4: frees.append(uc.reg_read(UC_ARM_REG_R0))
            elif address == 0x5383c8a8: cache.append((uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)))
            elif address == 0x5320b97c: uc.reg_write(UC_ARM_REG_R0, 0x55006000)
            elif address == 0x532b36cc:
                uc.mem_write(uc.reg_read(UC_ARM_REG_R1), struct.pack('<H6BH', 2026, 10, 14, 23, 59, 17, 0, 0))
                uc.reg_write(UC_ARM_REG_R0, 1)
            else: return
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, camera)
        h.call(u, 'm10v_library_init', 0x55001000)
        h.call(u, 'm10v_camera_library_select', 0x55001000, 1, film)
        h.call(u, 'm10v_camera_library_texture', 0x55001000, 1, 2, 3)
        h.call(u, 'm10v_camera_library_stamp', 0x55001000, 2, 2, 3, 1)
        h.file_calls.clear()
        recipe = 0x55070000; req = 0x55076000; shooting = 0x55078000
        width, height, stride = 128, 96, 136; capacity = stride * height
        for offset, value in ((0x18, 0), (0x5c, req), (0x60, 0x55020000 if raw_alias else raw_bank),
                              (0x230, 0x55075000), (0x44c8, shooting)):
            u.mem_write(recipe + offset, struct.pack('<I', value))
        u.mem_write(0x55075000, struct.pack('<HH', 6112, 4064))
        context = bytearray(0x60); struct.pack_into('<I', context, 0, 0x53d0fbe0)
        for offset, value in ((0x30, recipe + 0x1a8), (0x34, shooting), (0x38, req),
                              (0x3c, recipe + 0xb0), (0x48, recipe + 0x110), (0x4c, recipe + 0x130)):
            struct.pack_into('<I', context, offset, value)
        u.mem_write(recipe + 0x9b8, bytes(context))
        u.mem_write(req, struct.pack('<I', 0x53d0fe60)); u.mem_write(req + 12, bytes([jpeg, raw]))
        u.mem_write(shooting + 0x77c, bytes([tone])); u.mem_write(recipe + 0x140, b'\x01')
        for at, y_address, c_address in ((recipe + 0xb0, 0x55010000, 0x55020000),
                                         (recipe + 0x110, 0x55090000, 0x550a0000)):
            u.mem_write(at, struct.pack('<4I8H', 1, y_address, c_address, 0,
                                       width, height, stride, height, 0, 0, 2, 0))
        y = bytearray([64] * capacity + [173] * 32); uv = bytearray([128] * capacity + [197] * 32)
        for row in range(height):
            y[row * stride + width:(row + 1) * stride] = bytes([173] * 8)
            uv[row * stride + width:(row + 1) * stride] = bytes([197] * 8)
        y[48 * stride + 64] = 255
        u.mem_write(0x55010000, bytes(y)); u.mem_write(0x55020000, bytes(uv))
        return h, u, recipe + 0x9b8, y, uv, cache, frees, width, height, stride

    def test_capture_jpeg_and_raw_jpeg_use_stored_slot_and_match_native_pixels(self):
        for raw, bank in ((0, 0x60000000), (1, 0xa3000000)):
            h, u, context, y, uv, cache, frees, width, height, stride = self.fixture(raw=raw, raw_bank=bank)
            self.assertEqual(h.call(u, 'm10v_capture_library', context), 0)
            state = host_tests.State.from_buffer_copy(u.mem_read(0x55001000, C.sizeof(host_tests.State)))
            hy = (C.c_uint8 * len(y)).from_buffer_copy(y); hc = (C.c_uint8 * len(uv)).from_buffer_copy(uv)
            image = host_tests.Image(hy, hc, stride * height, stride * height, width, height, stride)
            date = host_tests.Date(2026, 10, 14, 23, 59); scratch = (C.c_uint8 * (2 * width * height))()
            seed = state.sequence ^ (2026 << 16) ^ (10 << 8) ^ 14 ^ (23 << 24) ^ (59 << 16) ^ (17 << 8) ^ 0x55010000
            self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(C.byref(image), C.byref(state),
                1, C.byref(date), seed, scratch, len(scratch)), 0)
            self.assertEqual(bytes(u.mem_read(0x55010000, len(y))), bytes(hy))
            self.assertEqual(bytes(u.mem_read(0x55020000, len(uv))), bytes(hc))
            self.assertEqual(len(cache), 4); self.assertEqual(frees, [0x550b0000])

    def test_unsupported_tone_raw_only_or_cfa_alias_do_not_access_library_or_pixels(self):
        for options in ({'tone': 11}, {'jpeg': 0, 'raw': 1}, {'raw_alias': True}):
            h, u, context, y, uv, cache, frees, *_ = self.fixture(**options)
            self.assertLess(h.call(u, 'm10v_capture_library', context), 0)
            self.assertEqual(bytes(u.mem_read(0x55010000, len(y))), bytes(y))
            self.assertEqual(bytes(u.mem_read(0x55020000, len(uv))), bytes(uv))
            self.assertFalse(h.file_calls); self.assertFalse(cache); self.assertFalse(frees)

    def test_800t_is_a_real_library_film_with_halation_and_shared_texture_stamp_chain(self):
        h,u,context,y,uv,cache,frees,width,height,stride=self.fixture(film=33)
        self.assertEqual(h.call(u,'m10v_capture_library',context),0)
        state=host_tests.State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(host_tests.State)))
        hy=(C.c_uint8*len(y)).from_buffer_copy(y);hc=(C.c_uint8*len(uv)).from_buffer_copy(uv)
        image=host_tests.Image(hy,hc,stride*height,stride*height,width,height,stride)
        date=host_tests.Date(2026,10,14,23,59);scratch=(C.c_uint8*(6*width*height))()
        seed=state.sequence^0x55010000^(2026<<16)^(10<<8)^14^(23<<24)^(59<<16)^(17<<8)
        self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(C.byref(image),C.byref(state),1,C.byref(date),seed,scratch,len(scratch)),0)
        self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(hy))
        self.assertEqual(bytes(u.mem_read(0x55020000,len(uv))),bytes(hc))
        self.assertGreater(max(hc[row*stride+x+1] for row in range(42,55) for x in range(58,72,2)),128)
        self.assertEqual(len(cache),4);self.assertEqual(len(frees),1)
        h,u,context,y,uv,cache,frees,*_=self.fixture(film=33,allocation=False)
        self.assertEqual(h.call(u,'m10v_capture_library',context),-6)
        self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(y))

    def test_800t_off_gain_and_profile_disable_only_halo_and_need_no_scratch(self):
        h,u,context,y,uv,cache,frees,*_=self.fixture(film=33,allocation=False)
        h.call(u,'m10v_camera_library_texture',0x55001000,1,0,0)
        h.call(u,'m10v_camera_library_stamp',0x55001000,0,0,0,0)
        h.call(u,'m10v_camera_library_halation',0x55001000,1,8,8,0,0)
        self.assertEqual(h.call(u,'m10v_capture_library',context),0);self.assertFalse(frees)
        self.assertEqual(len(cache),4)
        h,u,context,y,uv,cache,frees,*_=self.fixture(film=33,allocation=False)
        h.call(u,'m10v_camera_library_texture',0x55001000,1,0,0)
        h.call(u,'m10v_camera_library_halation',0x55001000,1,0,8,0,3)
        self.assertEqual(h.call(u,'m10v_capture_library',context),0);self.assertFalse(frees)

    def test_failed_scratch_allocation_preserves_image(self):
        h, u, context, y, uv, cache, frees, *_ = self.fixture(allocation=False)
        self.assertLess(h.call(u, 'm10v_capture_library', context), 0)
        self.assertEqual(bytes(u.mem_read(0x55010000, len(y))), bytes(y))
        self.assertEqual(bytes(u.mem_read(0x55020000, len(uv))), bytes(uv))
        self.assertFalse(cache); self.assertFalse(frees)


if __name__ == '__main__': unittest.main()
