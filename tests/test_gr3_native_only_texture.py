"""Native-only grain contract: retired journal bytes cannot trigger CPU texture."""
import ctypes as C
import unittest
import zlib
from tests import test_gr3_m10v_library as harness
from tests.test_gr3_m10v_library import State, STORE, Date

class NativeOnlyTextureTests(unittest.TestCase):
    setUpClass = classmethod(harness.NativeFilmLibraryTests.setUpClass.__func__)
    state = harness.NativeFilmLibraryTests.state
    image = harness.NativeFilmLibraryTests.image
    render = harness.NativeFilmLibraryTests.render

    def legacy(self, state):
        state.slots[0].grain = 3
        state.effects[0][0:5] = [2,8,5,8,1]
        state.crc = zlib.crc32(bytes(state)[:-4])
        self.assertEqual(self.lib.m10v_library_valid(C.byref(state)),1)

    def test_retired_setters_reject_nonzero_without_store_or_mutation(self):
        state=self.state(); calls=[]
        store=STORE(lambda _,value: calls.append(bytes(value.contents)) or 0)
        self.lib.m10v_library_effects.argtypes=[C.POINTER(State),C.c_uint32,C.c_uint32,C.c_uint32,STORE,C.c_void_p]
        for field in range(5):
            before=bytes(state)
            self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,field,1,store,None),-1)
            self.assertEqual(bytes(state),before)
        self.assertEqual(calls,[])
        self.legacy(state)
        before=bytes(state); bad=STORE(lambda _,value:-1)
        self.assertEqual(self.lib.m10v_library_effects(C.byref(state),0,0,0,bad,None),-2)
        self.assertEqual(bytes(state),before)

    def test_imported_texture_is_ignored_even_when_color_halo_or_stamp_runs(self):
        ok=STORE(lambda _,value:0)
        self.lib.m10v_library_render_native.argtypes=self.lib.m10v_library_render.argtypes+[C.c_uint32]
        for film in [1,33,40,66,67,68,78,289,290]:
            for completed in [0,1,31]:
                with self.subTest(film=film,completed=completed):
                    state=self.state(); self.lib.m10v_library_select(C.byref(state),0,film,ok,None)
                    if film in [33,67]: self.lib.m10v_library_halation(C.byref(state),0,4,3,5,2,ok,None)
                    self.lib.m10v_library_stamp(C.byref(state),1,0,0,0,ok,None)
                    expected=[]
                    for legacy in [False,True]:
                        if legacy:self.legacy(state)
                        im,y,uv,scratch=self.image(32,24)
                        date=Date(2026,10,23,12,30)
                        result=self.lib.m10v_library_render_native(C.byref(im),C.byref(state),0,C.byref(date),123,scratch,len(scratch)-32,completed)
                        self.assertEqual(result,0);expected.append((bytes(y),bytes(uv)))
                    self.assertEqual(*expected)

    def test_cpu_rendered_special_films_reject_upstream_grain(self):
        state=self.state(); ok=STORE(lambda _,value:0)
        for film in [289,290]:
            self.lib.m10v_library_select(C.byref(state),0,film,ok,None)
            before=bytes(state)
            self.assertEqual(self.lib.m10v_library_texture(C.byref(state),0,1,0,ok,None),-1)
            self.assertEqual(bytes(state),before)

    def test_scheduler_never_requests_cpu_grain_or_leak(self):
        import subprocess, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'probe.c'; out=Path(td)/'probe.dylib'
            source.write_text('#include "m10v_library.h"\nuint32_t plan(m10v_library_state *s,uint32_t done){return m10v_library_cpu_stages(s,0,done);}')
            subprocess.run(['clang','-O2','-dynamiclib','-I',str(harness.ROOT/'native/gr3'),str(source),'-o',str(out)],check=True,capture_output=True)
            lib=C.CDLL(str(out));lib.plan.argtypes=[C.POINTER(State),C.c_uint32]
            state=self.state();self.legacy(state)
            for done in range(32):
                self.assertEqual(lib.plan(C.byref(state),done)&18,0)
                self.assertEqual(bool(lib.plan(C.byref(state),done)&1),not bool(done&1))

    def test_color_fallback_matches_frozen_reference_scalar_and_vector(self):
        import random, subprocess, tempfile
        from pathlib import Path
        native=harness.ROOT/'native/gr3'
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); libs=[]
            sources=[(harness.ROOT/'tests/fixtures/gr3_texture_reference.c',[]),
                     (native/'film_5207.c',[]),(native/'film_5207.c',['-DM10V_TEXTURE_NEON=1'])]
            for index,(source,flags) in enumerate(sources):
                out=td/(str(index)+'.dylib')
                subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-dynamiclib','-I',str(native),*flags,str(source),
                    *[str(native/f) for f in ['film_harman.c','film_curated.c','film_newstocks.c']],
                    *([str(native/'m10v_texture_accel.c')] if flags else []),'-o',str(out)],check=True,capture_output=True)
                lib=C.CDLL(str(out));lib.m10v_5207_texture_q8.argtypes=[C.POINTER(harness.Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32];libs.append(lib)
            rng=random.Random(481)
            for width in [2,6,8,10,30,128]:
                size=(width+8)*9; source=[rng.randbytes(size) for _ in range(2)]
                for color in range(17):
                    results=[]
                    for lib in libs:
                        y=(C.c_uint8*size).from_buffer_copy(source[0]);uv=(C.c_uint8*size).from_buffer_copy(source[1])
                        image=harness.Image(y,uv,size,size,width,9,width+8);effects=(C.c_uint8*8)()
                        lib.m10v_5207_texture_q8(C.byref(image),effects,0,123,color)
                        results.append((bytes(y),bytes(uv)))
                    with self.subTest(width=width,color=color):
                        self.assertEqual(results[0],results[1]);self.assertEqual(results[0],results[2])

if __name__=='__main__':unittest.main()
