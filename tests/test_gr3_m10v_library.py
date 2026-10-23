"""Native M10V runtime tests; firmware integration is tested separately."""
import ctypes as C
import shutil
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Slot(C.Structure):
    _fields_ = [('film', C.c_uint16), ('grain', C.c_uint8), ('soft', C.c_uint8), ('halo_gain',C.c_uint8),('halo_spread',C.c_uint8),('halo_threshold',C.c_uint8),('halo_profile',C.c_uint8)]


class State(C.Structure):
    _fields_ = [('magic', C.c_uint32), ('version', C.c_uint16), ('size', C.c_uint16),
                ('sequence', C.c_uint32), ('slots', Slot * 5),
                ('stamp', C.c_uint8), ('format', C.c_uint8), ('corner', C.c_uint8),
                ('color', C.c_uint8), ('effects', (C.c_uint8*8)*5), ('reserved', C.c_uint32), ('crc', C.c_uint32)]


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
        wrapper.write_text('#include "' + str(ROOT / 'native/gr3/m10v_library.c') + '"\nuint32_t m10v_test_date(char *out,const m10v_library_date *date,uint32_t format,uint32_t mode){return date_text(out,date,format,mode); }\nvoid m10v_test_stamp(m10v_library_image *image,const m10v_library_state *state,const m10v_library_date *date,const char *name){stamp(image,state,date,name); }\nvoid m10v_test_line(m10v_library_image *image,const m10v_library_state *state,const char *text){stamp_line(image,state,text,1,0,0,108);}')
        subprocess.run([shutil.which('clang') or 'clang', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-dynamiclib', str(wrapper), str(ROOT / 'native/gr3/halation_core.c'), str(ROOT/'native/gr3/film_5207.c'),str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c'), '-o', str(out)],
                       check=True, capture_output=True)
        cls.lib = C.CDLL(str(out))
        cls.lib.m10v_test_line.argtypes = [C.POINTER(Image), C.POINTER(State), C.c_char_p]
        cls.lib.m10v_test_stamp.argtypes = [C.POINTER(Image), C.POINTER(State), C.POINTER(Date), C.c_char_p]
        cls.lib.m10v_library_init.argtypes = [C.POINTER(State)]
        cls.lib.m10v_library_valid.argtypes = [C.POINTER(State)]
        cls.lib.m10v_library_select.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_select_custom.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_texture.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_stamp.argtypes = [C.POINTER(State), C.c_uint32, C.c_uint32, C.c_uint32, C.c_uint32, STORE, C.c_void_p]
        cls.lib.m10v_library_film_name_stamp.argtypes = [C.POINTER(State),C.c_uint32,STORE,C.c_void_p]
        cls.lib.m10v_library_render.argtypes = [C.POINTER(Image), C.POINTER(State), C.c_uint32,
                                             C.POINTER(Date), C.c_uint32, C.POINTER(C.c_uint8), C.c_uint32]
        cls.lib.m10v_library_render_custom.argtypes = [C.POINTER(Image),C.POINTER(State),C.c_uint32,C.POINTER(Date),C.c_uint32,C.POINTER(C.c_uint8),C.c_uint32,C.c_uint32,C.POINTER(C.c_uint8),C.c_char_p]
        cls.lib.m10v_library_halation.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        cls.lib.m10v_library_tables.argtypes=[C.c_uint32,C.POINTER(C.c_int16),C.POINTER(C.c_int16),C.POINTER(C.c_uint16),C.POINTER(C.c_uint16)]
        cls.lib.m10v_library_name.argtypes = [C.c_uint32]; cls.lib.m10v_library_name.restype = C.c_char_p

    def test_extra_effects_are_opt_in_on_init_selection_and_reset(self):
        state=self.state();ok=STORE(lambda ctx,next:0)
        self.lib.m10v_library_reset.argtypes=[C.POINTER(State),C.c_uint32,STORE,C.c_void_p]
        def off():
            self.assertEqual((state.slots[0].grain,state.slots[0].soft,state.slots[0].halo_gain,state.effects[0][1]),(0,0,0,0))
        off()
        for film in list(range(33,79))+[289]:
            self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,film,ok,None),0);off()
            grain=0 if film==289 else 3
            self.assertEqual(self.lib.m10v_library_texture(C.byref(state),0,grain,0,ok,None),0)
            if film not in (66,68):self.assertEqual(self.lib.m10v_library_halation(C.byref(state),0,6,3,5,2,ok,None),0)
            saved=bytes(state)
            self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,film,ok,None),0)
            self.assertEqual(state.slots[0].grain,grain);self.assertEqual(state.slots[0].halo_gain,0 if film in (66,68) else 6)
            self.assertEqual(self.lib.m10v_library_reset(C.byref(state),0,ok,None),0);off()
            self.assertNotEqual(bytes(state),saved)

    def test_pixel_world_flat_cells_partial_edge_padding_and_native_completion(self):
        state=self.state();ok=STORE(lambda ctx,next:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,290,ok,None),0)
        self.assertEqual(self.lib.m10v_library_name(290),b'Pixel World')
        self.lib.m10v_library_render_native.argtypes=self.lib.m10v_library_render.argtypes+[C.c_uint32]
        for completed in (0,31):
            y=(C.c_uint8*24)(*[100,100,180,180,240,240,91,92]*3)
            uv=(C.c_uint8*24)(*(([128]*6+[81,82])*3))
            image=Image(y,uv,24,24,6,3,8)
            self.assertEqual(self.lib.m10v_library_render_native(C.byref(image),C.byref(state),0,None,0,None,0,completed),0)
            self.assertEqual(list(y),[96,96,176,176,240,240,91,92]*3)
            self.assertEqual(list(uv),([128]*6+[81,82])*3)
        before=bytes(state)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,298,ok,None),-1)
        self.assertEqual(bytes(state),before)

    def test_charmera_colors_are_atomic_per_slot_and_render_preserves_padding(self):
        state=self.state();ok=STORE(lambda ctx,next:0);bad=STORE(lambda ctx,next:-1)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,289,ok,None),0)
        self.assertEqual(state.slots[0].grain,0)
        other=bytes(state.slots[1]);self.assertEqual(self.lib.m10v_library_name(289),b'Kodak Charmera')
        for color,(light,cb,cr) in enumerate([(77,85,254),(207,55,158),(29,252,108),(224,128,128)]):
            before=bytes(state)
            self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,7,color,bad,None),-2)
            self.assertEqual(bytes(state),before)
            self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,7,color,ok,None),0)
            self.assertEqual(state.effects[0][7],color);self.assertEqual(bytes(state.slots[1]),other)
            y=(C.c_uint8*8)(127,127,128,128,91,92,93,94);uv=(C.c_uint8*8)(0,255,50,200,81,82,83,84)
            image=Image(y,uv,8,8,4,1,8)
            self.assertEqual(self.lib.m10v_library_render(C.byref(image),C.byref(state),0,None,0,None,0),0)
            self.assertEqual(list(y),[0,0,light,light,91,92,93,94])
            self.assertEqual(list(uv),[128,128,cb,cr,81,82,83,84])
        before=bytes(state);self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,7,4,ok,None),-1);self.assertEqual(bytes(state),before)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,33,ok,None),0);self.assertEqual(state.effects[0][7],0)

    def test_short_display_names_are_shared_with_lut_metadata(self):
        import json
        expected={74:'ProImage 100',76:'Aerochrome',77:'2460',78:'5203'}
        stocks={stock['id']:stock for stock in json.loads((ROOT/'web/gr3/newstocks-luts.json').read_text())['stocks']}
        for film,name in expected.items():
            self.assertEqual(self.lib.m10v_library_name(film).decode(),name)
            self.assertEqual(stocks[film]['name'],name)
            self.assertEqual(stocks[film]['ascii_name'],name)

    def test_800t_invalid_halo_stride_leaves_pixels_unchanged(self):
        state=self.state();store=STORE(lambda context,value:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,33,store,None),0)
        image,y,uv,scratch=self.image();image.stride-=1
        before=(bytes(y),bytes(uv))
        self.assertLess(self.render(image,state,scratch),0)
        self.assertEqual((bytes(y),bytes(uv)),before)

    def test_selecting_new_custom_film_does_not_inherit_previous_light_leak(self):
        state=self.state();ok=STORE(lambda ctx,next:0)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        # Imported old journal remains readable; selection retires its leak.
        state.effects[0][1]=8;state.crc=zlib.crc32(bytes(state)[:-4])
        self.assertEqual(self.lib.m10v_library_valid(C.byref(state)),1)
        self.assertEqual(self.lib.m10v_library_select_custom(C.byref(state),0,79,0,ok,None),0)
        self.assertEqual(state.effects[0][1],0)

    def test_custom_slot_bank_commits_only_with_state_and_clears_on_builtin(self):
        state=self.state();before=bytes(state);bad=STORE(lambda ctx,next:-1);ok=STORE(lambda ctx,next:0)
        self.assertEqual(self.lib.m10v_library_select_custom(C.byref(state),0,79,1,bad,None),-2)
        self.assertEqual(bytes(state),before)
        self.assertEqual(self.lib.m10v_library_select_custom(C.byref(state),0,79,1,ok,None),0)
        self.assertEqual(state.slots[0].film,79);self.assertEqual(state.effects[0][6],2)
        self.assertEqual(self.lib.m10v_library_valid(C.byref(state)),1)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,33,ok,None),0)
        self.assertEqual(state.effects[0][6],0)

    def test_custom_lut_changes_saved_rgb_without_sd_and_missing_table_is_rejected(self):
        state=self.state();ok=STORE(lambda ctx,next:0)
        self.assertEqual(self.lib.m10v_library_select_custom(C.byref(state),0,79,0,ok,None),0)
        image,y,uv,scratch=self.image();uv[0]=80;uv[1]=200;before=(bytes(y),bytes(uv))
        self.assertLess(self.render(image,state,scratch),0)
        self.assertEqual((bytes(y),bytes(uv)),before)
        lut=(C.c_uint8*6591)();i=0
        for b in range(13):
            for g in range(13):
                for r in range(13):
                    lut[i:i+3]=(round(b*255/12),round(g*255/12),round(r*255/12));i+=3
        self.assertEqual(self.lib.m10v_library_render_custom(C.byref(image),C.byref(state),0,None,1,scratch,len(scratch)-32,0,lut,b'Custom'),0)
        self.assertNotEqual(bytes(uv),before[1])

    def test_film_name_stamp_is_independent_of_date_and_uses_stamp_style(self):
        state=self.state();ok=STORE(lambda ctx,next:0)
        self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,1,ok,None),0)
        self.assertEqual(self.lib.m10v_library_film_name_stamp(C.byref(state),1,ok,None),0)
        self.assertEqual(state.reserved,1);self.assertEqual(self.lib.m10v_library_valid(C.byref(state)),1)
        image,y,uv,scratch=self.image(320,240);before=bytes(y)
        self.assertEqual(self.render(image,state,scratch,Date(2026,2,30,0,0)),0)
        changed={i//image.stride for i in range(image.y_bytes) if y[i]!=before[i]}
        self.assertTrue(changed);self.assertLess(max(changed),30)
        self.assertEqual(bytes(y)[image.y_bytes:],bytes([173]*32))
        self.assertEqual(self.lib.m10v_library_stamp(C.byref(state),1,0,0,1,ok,None),0)
        image,y,uv,scratch=self.image(320,240);before=bytes(y)
        self.assertEqual(self.render(image,state,scratch,Date(2026,10,14,23,59)),0)
        changed={i//image.stride for i in range(image.y_bytes) if y[i]!=before[i]}
        self.assertTrue(any(row<12 for row in changed));self.assertTrue(any(row>=12 for row in changed))
        self.assertEqual(self.lib.m10v_library_film_name_stamp(C.byref(state),0,ok,None),0)
        self.assertEqual(state.reserved,0)

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
        self.assertIsNone(self.lib.m10v_library_name(0)); self.assertIsNone(self.lib.m10v_library_name(79))
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
        self.assertLess(self.lib.m10v_library_select(C.byref(state), 0, 79, success, None), 0)
        self.assertEqual(bytes(state), before)

    def test_neutral_disabled_effects_are_byte_identical_and_padding_is_protected(self):
        state = self.state(); image, y, uv, scratch = self.image()
        @STORE
        def save(_, proposed): return 0
        self.assertEqual(self.lib.m10v_library_select(C.byref(state), 0, 1, save, None), 0)
        before = bytes(y), bytes(uv), bytes(scratch)
        self.assertEqual(self.render(image, state, scratch), 0)
        self.assertEqual((bytes(y), bytes(uv), bytes(scratch)), before)

    def test_color_preset_changes_color_and_cpu_ignores_native_grain(self):
        @STORE
        def save(_, proposed): return 0
        state = self.state()
        self.lib.m10v_library_select(C.byref(state), 0, 2, save, None)
        image, y, uv, scratch = self.image(); old = bytes(y), bytes(uv)
        self.assertEqual(self.render(image, state, scratch), 0)
        self.assertNotEqual((bytes(y), bytes(uv)), old)
        outputs = []
        for seed in (12, 12, 13):
            state = self.state(); self.lib.m10v_library_select(C.byref(state), 0, 1, save, None)
            self.lib.m10v_library_texture(C.byref(state), 0, 3, 0, save, None)
            image, y, uv, scratch = self.image(); self.assertEqual(self.render(image, state, scratch, seed=seed), 0)
            outputs.append(bytes(y)); self.assertEqual(bytes(uv), bytes(self.image()[2]))
            for row in range(image.height): self.assertEqual(bytes(y[row * image.stride + 128:(row + 1) * image.stride]), bytes([173] * 8))
            self.assertEqual(bytes(y)[image.y_bytes:], bytes([173] * 32))
        self.assertEqual(outputs[0], outputs[1]); self.assertEqual(outputs[0], outputs[2])

    def test_retired_soft_does_not_spread_highlight_or_touch_chroma_or_scratch(self):
        @STORE
        def save(_, proposed): return 0
        state = self.state(); self.lib.m10v_library_texture(C.byref(state), 0, 0, 3, save, None)
        self.lib.m10v_library_select(C.byref(state), 0, 1, save, None)
        image, y, uv, scratch = self.image(); at = 48 * image.stride + 64; y[at] = 255
        before_uv = bytes(uv)
        self.assertEqual(self.render(image, state, scratch), 0)
        self.assertEqual(y[at + 2], 64); self.assertEqual(y[at], 255)
        self.assertEqual(bytes(uv), before_uv); self.assertEqual(bytes(scratch)[-32:], bytes([91] * 32))

    def stamp_pixels(self, width=6000, height=4000, corner=0, name=None, mode=1, planes=False):
        import numpy as np
        stride=width+16
        y=np.full((height+1,stride),73,dtype=np.uint8)
        uv=np.full_like(y,129)
        image=Image(y.ctypes.data_as(C.POINTER(C.c_uint8)),uv.ctypes.data_as(C.POINTER(C.c_uint8)),height*stride,height*stride,width,height,stride)
        state=self.state();state.stamp=mode;state.color=2;state.corner=corner;state.reserved=bool(name)
        date=Date(2026,10,20,23,59)
        self.lib.m10v_test_stamp(C.byref(image),C.byref(state),C.byref(date),name)
        self.assertTrue((y[:,width:]==73).all());self.assertTrue((uv[:,width:]==129).all())
        self.assertTrue((y[height]==73).all());self.assertTrue((uv[height]==129).all())
        return (y[:height,:width],uv[:height,:width]) if planes else y[:height,:width]

    def test_segmented_stamp_24mp_date_and_name_sizes(self):
        import numpy as np
        y=self.stamp_pixels()
        rows=np.flatnonzero((y==82).any(axis=1))
        self.assertGreaterEqual(rows[-1]-rows[0]+1,105)
        self.assertLessEqual(rows[-1]-rows[0]+1,108)
        y=self.stamp_pixels(name=b'Kodak 5207',mode=0)
        rows=np.flatnonzero((y==82).any(axis=1))
        self.assertGreaterEqual(rows[-1]-rows[0]+1,90)
        self.assertLessEqual(rows[-1]-rows[0]+1,100)

    def test_date_and_alphabet_share_hollow_beveled_italic_segments(self):
        import numpy as np
        for char in [b'8',b'A',b'a',b'B',b'D']:
            y=np.full((120,128),73,dtype=np.uint8);uv=np.full_like(y,129)
            image=Image(y.ctypes.data_as(C.POINTER(C.c_uint8)),uv.ctypes.data_as(C.POINTER(C.c_uint8)),y.size,uv.size,128,120,128)
            state=self.state();state.color=2
            self.lib.m10v_test_line(C.byref(image),C.byref(state),char)
            self.assertEqual(y[25,30],73)  # counters remain open, unlike solid blocks
            top=np.flatnonzero(y[0]==82);middle=np.flatnonzero(y[6]==82)
            self.assertGreater(len(middle),len(top))  # bevel opens after the tip
            if char==b'8':
                bottom=np.flatnonzero(y[107]==82)
                self.assertGreater(top.min(),bottom.min()+7)  # italic shear
            if char in [b'B',b'D']:self.assertEqual(y[30,15],82)
            if char==b'A':upper=y.copy()
            if char==b'a':self.assertTrue((upper==y).all())

    def test_short_film_name_aligns_with_date_at_right_corners(self):
        import numpy as np
        for corner in [1,3]:
            y=self.stamp_pixels(corner=corner,name=b'8')
            rows=np.flatnonzero((y==82).any(axis=1))
            split=np.flatnonzero(np.diff(rows)>10)[0]
            date_right=np.where(y[rows[:split+1]]==82)[1].max()
            name_right=np.where(y[rows[split+1:]]==82)[1].max()
            self.assertLess(abs(date_right-name_right),25)

    def test_stamp_fits_corners_small_aspects_long_ascii_and_two_lines(self):
        import numpy as np
        for w,h in [(320,240),(240,320),(96,64),(6000,4000),(4000,6000)]:
            for corner in range(4):
                y=self.stamp_pixels(w,h,corner,b"CUSTOM ABCDEFGHIJKLMNOP",2)
                rows,cols=np.where(y==82)
                self.assertGreater(len(rows),0)
                self.assertEqual(bool(rows.mean()>h/2),bool(corner&2))
                self.assertEqual(bool(cols.mean()>w/2),bool(corner&1))
                runs=np.flatnonzero(np.diff(np.unique(rows))>1)
                self.assertGreater(len(runs),0)

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
