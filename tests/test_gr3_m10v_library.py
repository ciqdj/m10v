"""Native M10V runtime tests; firmware integration is tested separately."""
import ctypes as C
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Slot(C.Structure):
    _fields_ = [('film', C.c_uint16), ('grain', C.c_uint8), ('soft', C.c_uint8), ('halo_gain',C.c_uint8),('halo_spread',C.c_uint8),('halo_threshold',C.c_uint8),('halo_profile',C.c_uint8)]


class State(C.Structure):
    _fields_ = [('magic', C.c_uint32), ('version', C.c_uint16), ('size', C.c_uint16),
                ('sequence', C.c_uint32), ('slots', Slot * 5),
                ('stamp', C.c_uint8), ('format', C.c_uint8), ('corner', C.c_uint8),
                ('color', C.c_uint8), ('reserved', C.c_uint32), ('crc', C.c_uint32)]


class Image(C.Structure):
    _fields_ = [('y', C.POINTER(C.c_uint8)), ('chroma', C.POINTER(C.c_uint8))] + [
        (n, C.c_uint32) for n in ('y_bytes', 'chroma_bytes', 'width', 'height', 'stride')]


class Date(C.Structure):
    _fields_ = [('year', C.c_uint16)] + [(n, C.c_uint8) for n in ('month', 'day', 'hour', 'minute')]


STORE = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(State))


class NativeFilmLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        out = Path(cls.tmp.name) / 'films.dylib'
        wrapper = Path(cls.tmp.name) / 'date_probe.c'
        wrapper.write_text('#include "' + str(ROOT / 'native/gr3/m10v_library.c') + '"\nuint32_t m10v_test_date(char *out,const m10v_library_date *date,uint32_t format,uint32_t mode){return date_text(out,date,format,mode);}')
        subprocess.run([shutil.which('clang') or 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-dynamiclib', str(wrapper), str(ROOT / 'native/gr3/halation_core.c'), '-o', str(out)],
                       check=True, capture_output=True)
        cls.lib = C.CDLL(str(out))
        cls.lib.m10v_library_init.argtypes = [C.POINTER(State)]
        cls.lib.m10v_library_valid.argtypes = [C.POINTER(State)]
        cls.lib.m10v_library_select.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_texture.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_stamp.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_render.argtypes = [C.POINTER(Image), C.POINTER(State), C.c_uint32,
                                             C.POINTER(Date), C.c_uint32, C.POINTER(C.c_uint8), C.c_uint32]
        cls.lib.m10v_library_halation.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        cls.lib.m10v_library_tables.argtypes=[C.c_uint32,C.POINTER(C.c_int16),C.POINTER(C.c_int16),C.POINTER(C.c_uint16),C.POINTER(C.c_uint16)]
        cls.lib.m10v_library_name.argtypes = [C.c_uint32]; cls.lib.m10v_library_name.restype = C.c_char_p

    def test_800t_invalid_halo_stride_leaves_pixels_unchanged(self):
        state=self.state();store=STORE(lambda context,value:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,33,store,None),0)
        image,y,uv,scratch=self.image();image.stride-=1
        before=(bytes(y),bytes(uv))
        self.assertLess(self.render(image,state,scratch),0)
        self.assertEqual((bytes(y),bytes(uv)),before)

    def test_existing_matrices_curves_and_knots_decode_losslessly(self):
        import json
        looks=json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']
        for index,look in enumerate(looks):
            matrix=(C.c_int16*9)();post=(C.c_int16*9)();curves=(C.c_uint16*768)();knots=(C.c_uint16*99)()
            self.assertEqual(self.lib.m10v_library_tables(index+34,matrix,post,curves,knots),0)
            self.assertEqual(list(matrix),look['matrixQ13']);self.assertEqual(list(post),look['postQ512'])
            self.assertEqual(list(curves),sum(look['curves'],[]));self.assertEqual(list(knots),sum(look['knots'],[]))

    def test_four_halation_controls_are_atomic_and_preserve_other_slots(self):
        state=self.state();before=bytes(state);bad=STORE(lambda context,next:-1);ok=STORE(lambda context,next:0)
        self.assertEqual(self.lib.m10v_library_halation(C.byref(state),4,8,1,7,3,bad,None),-2)
        self.assertEqual(bytes(state),before)
        self.assertEqual(self.lib.m10v_library_halation(C.byref(state),4,8,1,7,3,ok,None),0)
        self.assertEqual([state.slots[4].halo_gain,state.slots[4].halo_spread,state.slots[4].halo_threshold,state.slots[4].halo_profile],[8,1,7,3])
        self.assertEqual(bytes(state)[12:44],before[12:44]);self.assertEqual(self.lib.m10v_library_valid(C.byref(state)),1)

    def test_date_format_and_enabled_mode_are_independent(self):
        date = Date(2026, 10, 14, 23, 59)
        expected = ['2026.10.14', '14.10.2026', '2026-10-14', '26.10.14']
        for i, text in enumerate(expected):
            for mode in (1, 2):
                out = C.create_string_buffer(24)
                self.lib.m10v_test_date(out, C.byref(date), i, mode)
                self.assertEqual(out.value.decode(), text + (' 23:59' if mode == 2 else ''))

    def state(self):
        state = State(); self.lib.m10v_library_init(C.byref(state)); return state

    def image(self, width=128, height=96, padding=8):
        stride = width + padding; size = stride * height
        y = (C.c_uint8 * (size + 32))(*([64] * size + [173] * 32))
        uv = (C.c_uint8 * (size + 32))(*([128] * size + [197] * 32))
        for row in range(height):
            for x in range(width, stride): y[row * stride + x] = 173; uv[row * stride + x] = 197
        scratch = (C.c_uint8 * (2 * 384 * 256 + 32))(*([91] * (2 * 384 * 256 + 32)))
        return Image(y, uv, size, size, width, height, stride), y, uv, scratch

    def render(self, image, state, scratch, date=None, seed=123):
        return self.lib.m10v_library_render(C.byref(image), C.byref(state), 0,
            C.byref(date) if date else None, seed, scratch, len(scratch) - 32)

    def test_65_shared_presets_and_crc_state(self):
        state = self.state(); self.assertEqual(self.lib.m10v_library_valid(C.byref(state)), 1)
        self.assertEqual([slot.film for slot in state.slots], [34,35,36,37,33])
        names = [self.lib.m10v_library_name(i) for i in range(1, 66)]
        self.assertEqual(len(set(names)), 65); self.assertTrue(all(names))
        self.assertIsNone(self.lib.m10v_library_name(0)); self.assertIsNone(self.lib.m10v_library_name(66))
        state.slots[2].film = 31
        self.assertEqual(self.lib.m10v_library_valid(C.byref(state)), 0)

    def test_slot_change_is_atomic_on_store_failure_and_preserves_other_slots(self):
        state = self.state(); before = bytes(state); saved = []
        @STORE
        def fail(_, proposed): saved.append(bytes(proposed.contents)); return -1
        self.assertLess(self.lib.m10v_library_select(C.byref(state), 2, 32, fail, None), 0)
        self.assertEqual(bytes(state), before); self.assertNotEqual(saved[0], before)
        @STORE
        def success(_, proposed): return 0
        self.assertEqual(self.lib.m10v_library_select(C.byref(state), 2, 32, success, None), 0)
        self.assertEqual(state.slots[2].film, 32); self.assertEqual(state.sequence, 1)
        self.assertEqual([state.slots[i].film for i in (0, 1, 3, 4)], [34, 35, 37, 33])
        self.assertEqual(self.lib.m10v_library_valid(C.byref(state)), 1)
        before = bytes(state)
        self.assertLess(self.lib.m10v_library_select(C.byref(state), 5, 1, success, None), 0)
        self.assertLess(self.lib.m10v_library_select(C.byref(state), 0, 66, success, None), 0)
        self.assertEqual(bytes(state), before)

    def test_neutral_disabled_effects_are_byte_identical_and_padding_is_protected(self):
        state = self.state(); image, y, uv, scratch = self.image()
        @STORE
        def save(_, proposed): return 0
        self.assertEqual(self.lib.m10v_library_select(C.byref(state), 0, 1, save, None), 0)
        before = bytes(y), bytes(uv), bytes(scratch)
        self.assertEqual(self.render(image, state, scratch), 0)
        self.assertEqual((bytes(y), bytes(uv), bytes(scratch)), before)

    def test_color_preset_changes_color_and_grain_is_seeded_and_bounded(self):
        @STORE
        def save(_, proposed): return 0
        state = self.state()
        self.lib.m10v_library_select(C.byref(state), 0, 2, save, None)
        image, y, uv, scratch = self.image(); old = bytes(y), bytes(uv)
        self.assertEqual(self.render(image, state, scratch), 0)
        self.assertNotEqual((bytes(y), bytes(uv)), old)
        outputs = []
        for seed in (12, 12, 13):
            state = self.state(); self.lib.m10v_library_texture(C.byref(state), 0, 3, 0, save, None)
            self.lib.m10v_library_select(C.byref(state), 0, 1, save, None)
            image, y, uv, scratch = self.image(); self.assertEqual(self.render(image, state, scratch, seed=seed), 0)
            outputs.append(bytes(y)); self.assertEqual(bytes(uv), bytes(self.image()[2]))
            for row in range(image.height): self.assertEqual(bytes(y[row * image.stride + 128:(row + 1) * image.stride]), bytes([173] * 8))
            self.assertEqual(bytes(y)[image.y_bytes:], bytes([173] * 32))
        self.assertEqual(outputs[0], outputs[1]); self.assertNotEqual(outputs[0], outputs[2])

    def test_soft_bloom_spreads_highlight_without_chroma_or_scratch_overrun(self):
        @STORE
        def save(_, proposed): return 0
        state = self.state(); self.lib.m10v_library_texture(C.byref(state), 0, 0, 3, save, None)
        self.lib.m10v_library_select(C.byref(state), 0, 1, save, None)
        image, y, uv, scratch = self.image(); at = 48 * image.stride + 64; y[at] = 255
        before_uv = bytes(uv)
        self.assertEqual(self.render(image, state, scratch), 0)
        self.assertGreater(y[at + 2], 64); self.assertEqual(y[at], 255)
        self.assertEqual(bytes(uv), before_uv); self.assertEqual(bytes(scratch)[-32:], bytes([91] * 32))

    def test_timestamp_draws_valid_date_in_all_corners_and_rejects_bad_date_before_mutation(self):
        @STORE
        def save(_, proposed): return 0
        for corner in range(4):
            state = self.state(); self.lib.m10v_library_stamp(C.byref(state), 1, 0, corner, 1, save, None)
            self.lib.m10v_library_select(C.byref(state), 0, 1, save, None)
            image, y, uv, scratch = self.image(320, 240); before = bytes(y)
            self.assertEqual(self.render(image, state, scratch, Date(2026, 10, 14, 23, 59)), 0)
            changed = [i for i in range(image.y_bytes) if y[i] != before[i]]
            self.assertTrue(changed)
            self.assertTrue(all((i // image.stride < 120) == (corner < 2) for i in changed))
            self.assertEqual(bytes(y)[image.y_bytes:], bytes([173] * 32))
        image, y, uv, scratch = self.image(); before = bytes(y), bytes(uv)
        self.assertLess(self.render(image, state, scratch, Date(2026, 2, 30, 0, 0)), 0)
        self.assertEqual((bytes(y), bytes(uv)), before)

    def test_invalid_image_or_state_cannot_write_pixels(self):
        state = self.state(); image, y, uv, scratch = self.image(); before = bytes(y), bytes(uv)
        image.width = 129
        self.assertLess(self.render(image, state, scratch), 0)
        image.width = 128; image.chroma = image.y
        self.assertLess(self.render(image, state, scratch), 0)
        self.assertEqual((bytes(y), bytes(uv)), before)


if __name__ == '__main__': unittest.main()
