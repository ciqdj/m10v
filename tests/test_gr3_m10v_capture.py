"""M10V capture adapter ARM tests with explicit camera-service boundaries."""
import ctypes as C
import hashlib
import json
import os
import struct
import tempfile
import subprocess
import zlib
import unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_PC, UC_ARM_REG_LR
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_library_arm as arm_tests
from tests import test_gr3_m10v_library as host_tests


class M10VCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        candidate = os.environ.get('M10V_CAPTURE_BIN')
        if candidate:
            candidate = Path(candidate).resolve()
            manifest_path = Path(os.environ.get('M10V_CAPTURE_MANIFEST',
                str(candidate.parent.parent / 'evidence/M10V-runtime-manifest.json')))
            cls.manifest = json.loads(manifest_path.read_text())
            script = "import {readFileSync} from 'node:fs';import {decodeFrameMap} from './node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
            rtos = subprocess.check_output(['node','--input-type=module','-e',script,str(candidate)],cwd=Path(__file__).resolve().parents[1])
            offset = cls.manifest['base'] - 0x53000000
            cls.code = rtos[offset:offset + cls.manifest['code_bytes']]
            if hashlib.sha256(cls.code).hexdigest() != cls.manifest['code_sha256']:
                raise AssertionError('Final firmware runtime does not match the evidence manifest')
            if not cls.manifest.get('debug_mode'):
                raise AssertionError('Final candidate must enable debug events for diagnostic regressions')
            cls.debug_manifest = cls.manifest; cls.debug_code = cls.code
        else:
            cls.manifest = build(Path(cls.tmp.name)); cls.code = (Path(cls.tmp.name) / 'm10v-library-arm.bin').read_bytes()
            cls.debug_manifest = build(Path(cls.tmp.name) / 'debug', debug_mode=True)
            cls.debug_code = (Path(cls.tmp.name) / 'debug/m10v-library-arm.bin').read_bytes()
        js = "import {readFileSync} from 'node:fs';import {officialResources} from './node/gr3-stock-presets.mjs';const {decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.RTOS.offset,s.RTOS.offset+s.RTOS.size));"
        cls.official = subprocess.check_output(['node', '--input-type=module', '-e', js], cwd=Path(__file__).resolve().parents[1])
        host_tests.NativeFilmLibraryTests.setUpClass(); cls.addClassCleanup(host_tests.NativeFilmLibraryTests.doClassCleanups)

    def fixture(self, tone=18, jpeg=1, raw=0, raw_alias=False, allocation=True, raw_bank=0x60000000, film=2, clock_ready=1, date=(2026, 10, 14, 23, 59, 17), stamp=2, debug=False, capture_date=None):
        h = arm_tests.FilmLibraryArmTests(); h.manifest = self.debug_manifest if debug else self.manifest; h.code = self.debug_code if debug else self.code; u = h.machine()
        h.capture_events = []
        for address in (0x536af000, 0x5383c000, 0x532b3000): u.mem_map(address, 4096)
        # Execute the official getter/property/date-copy instructions, not a fake
        # success result. Only the firmware assertion terminal is substituted.
        for page in (0x532b3000, 0x535be000, 0x5356b000, 0x536b5000,
                     0x536b9000, 0x53d62000, 0x54055000, 0x53432000, 0x536bd000, 0x536b6000):
            if page != 0x532b3000: u.mem_map(page, 4096)
            u.mem_write(page, self.official[page - 0x53000000:page - 0x53000000 + 4096])
        u.mem_write(0x550062ac, struct.pack('<I', clock_ready))
        u.mem_write(0x550063c0, struct.pack('<H6BH', *date, 0, 0))
        cache = []; frees = []
        def camera(uc, address, size, data):
            if h.manifest.get('debug_mode') and address == h.manifest['symbols']['m10v_debug_log']:
                h.capture_events.append(tuple(uc.reg_read(r) for r in
                    (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)) +
                    (struct.unpack('<I', uc.mem_read(uc.reg_read(UC_ARM_REG_SP), 4))[0],))
                uc.reg_write(UC_ARM_REG_R0, 0)
            elif address == 0x536af2a8:
                self.assertLessEqual(uc.reg_read(UC_ARM_REG_R0), 589824)
                uc.reg_write(UC_ARM_REG_R0, 0x550b0000 if allocation else 0)
            elif address == 0x536af2e4: frees.append(uc.reg_read(UC_ARM_REG_R0))
            elif address == 0x5383c8a8: cache.append((uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)))
            elif address == 0x5320b97c: uc.reg_write(UC_ARM_REG_R0, 0x55006000)
            elif address == 0x536bd838:
                uc.reg_write(UC_ARM_REG_R0, 0x55006400)
            elif address == 0x536b6510:
                # Only the runtime clock provider is substituted; execute the
                # original metadata producer and weekday conversion below it.
                uc.mem_write(uc.reg_read(UC_ARM_REG_R1), struct.pack('<H6BH', *capture_date, 0, 0))
            elif address == 0x536b93d0: self.assertEqual(uc.reg_read(UC_ARM_REG_R0), 1)
            else: return
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, camera)
        h.call(u, 'm10v_library_init', 0x55001000)
        h.call(u, 'm10v_camera_library_select', 0x55001000, 1, film)
        h.call(u, 'm10v_camera_library_texture', 0x55001000, 1, 2, 3)
        h.call(u, 'm10v_camera_library_stamp', 0x55001000, stamp, 2, 3, 1)
        h.file_calls.clear()
        recipe = 0x55070000; req = 0x55076000; shooting = 0x55078000
        if capture_date is not None:
            h.manifest = {**h.manifest, 'symbols': {**h.manifest['symbols'], 'official_date_producer': 0x534322d8}}
            h.call(u, 'official_date_producer', 0, 0, shooting)
            self.assertEqual(bytes(u.mem_read(shooting + 0x944, 4)), struct.pack('<HBB', *capture_date[:3]))
            self.assertEqual(bytes(u.mem_read(shooting + 0x949, 3)), bytes(capture_date[3:]))
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

    def test_common_leak_is_consumed_by_non_5207_capture_with_per_shot_seed(self):
        h,u,context,y,uv,cache,frees,width,height,stride=self.fixture(film=40,stamp=0,debug=True)
        self.assertEqual(h.call(u,'m10v_camera_library_effects',0x55001000,1,1,8),0)
        self.assertEqual(h.call(u,'m10v_camera_library_effects',0x55001000,1,4,1),0)
        self.assertEqual(h.call(u,'m10v_capture_library',context),0)
        events=[e for e in h.capture_events if e[0]==112]
        self.assertEqual(len(events),1);self.assertEqual(events[0][2],40)
        state=host_tests.State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(host_tests.State)))
        hy=(C.c_uint8*len(y)).from_buffer_copy(y);hc=(C.c_uint8*len(uv)).from_buffer_copy(uv)
        image=host_tests.Image(hy,hc,stride*height,stride*height,width,height,stride)
        scratch=(C.c_uint8*(6*width*height))()
        self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(
            C.byref(image),C.byref(state),1,None,events[0][3],scratch,len(scratch)),0)
        self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(hy))
        self.assertEqual(bytes(u.mem_read(0x55020000,len(uv))),bytes(hc))

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

    def test_unavailable_or_invalid_date_skips_only_stamp_and_preserves_saved_setting(self):
        # Regression: returning -7 (or passing invalid date to render) loses
        # every effect. Compare the output with the same saved recipe minus stamp.
        for options in ({'clock_ready': 0}, {'clock_ready': 2},
                        {'date': (2026, 2, 30, 23, 59, 17)},
                        {'date': (2026, 10, 14, 24, 0, 0)},
                        {'date': (2026, 10, 14, 23, 59, 60)}):
            with self.subTest(options=options):
                h,u,context,y,uv,cache,frees,width,height,stride = self.fixture(film=33, **options)
                saved = dict(h.files)
                self.assertEqual(h.call(u, 'm10v_capture_library', context), 0)
                state = host_tests.State.from_buffer_copy(u.mem_read(0x55001000, C.sizeof(host_tests.State)))
                self.assertEqual(state.stamp, 2)
                self.assertEqual(h.files, saved)
                state.stamp = 0
                state.crc = zlib.crc32(bytes(state)[:-4])
                hy=(C.c_uint8*len(y)).from_buffer_copy(y); hc=(C.c_uint8*len(uv)).from_buffer_copy(uv)
                image=host_tests.Image(hy,hc,stride*height,stride*height,width,height,stride)
                scratch=(C.c_uint8*(6*width*height))()
                self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(
                    C.byref(image),C.byref(state),1,None,state.sequence^0x55010000,scratch,len(scratch)),0)
                self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(hy))
                self.assertEqual(bytes(u.mem_read(0x55020000,len(uv))),bytes(hc))
                self.assertNotEqual(bytes(hy),bytes(y))
                self.assertGreater(max(hc[row*stride+x+1] for row in range(42,55) for x in range(58,72,2)),128)
                self.assertEqual(len(cache),4); self.assertEqual(frees,[0x550b0000])

    def test_official_capture_metadata_date_wins_over_unready_or_different_ui_date(self):
        for ready in (0,1):
            h,u,context,y,uv,cache,frees,width,height,stride = self.fixture(
                debug=True,film=33,clock_ready=ready,capture_date=(2024,2,29,6,7,8))
            h.capture_events.clear()
            self.assertEqual(h.call(u,'m10v_capture_library',context),0)
            self.assertEqual([e[2] for e in h.capture_events if e[0]==120],[4])
            state=host_tests.State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(host_tests.State)))
            hy=(C.c_uint8*len(y)).from_buffer_copy(y);hc=(C.c_uint8*len(uv)).from_buffer_copy(uv)
            image=host_tests.Image(hy,hc,stride*height,stride*height,width,height,stride)
            date=host_tests.Date(2024,2,29,6,7);scratch=(C.c_uint8*(6*width*height))()
            seed=state.sequence^0x55010000^(2024<<16)^(2<<8)^29^(6<<24)^(7<<16)^(8<<8)
            self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(
                C.byref(image),C.byref(state),1,C.byref(date),seed,scratch,len(scratch)),0)
            self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(hy))
            self.assertEqual(bytes(u.mem_read(0x55020000,len(uv))),bytes(hc))

    def test_clock_diagnostics_distinguish_unavailable_invalid_and_valid_date(self):
        for options,status in (({'clock_ready':0},2),({'date':(2026,2,30,0,0,0)},3),({},1)):
            h,u,context,*_ = self.fixture(debug=True,film=33,**options)
            h.capture_events.clear()
            self.assertEqual(h.call(u,'m10v_capture_library',context),0)
            clock = [e for e in h.capture_events if e[0] == 120]
            self.assertEqual(clock,[(120,context,status,2,0x55006000)])
            self.assertEqual([e[0] for e in h.capture_events],[100,120,110,111,101])
            self.assertEqual(h.capture_events[-1][2],0)

    def test_grain_without_stamp_survives_unready_official_clock(self):
        h,u,context,y,uv,cache,frees,*_ = self.fixture(film=33,clock_ready=0,stamp=0)
        self.assertEqual(h.call(u,'m10v_capture_library',context),0)
        self.assertNotEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(y))
        self.assertEqual(len(cache),4)

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
