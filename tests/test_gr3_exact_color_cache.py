"""Exact per-capture cache: collisions, exhausted memory and padded rows."""
import ctypes as C
import random
import unittest
from tests import test_gr3_m10v_library as host

class ExactColorCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host.NativeFilmLibraryTests.setUpClass()
        cls.addClassCleanup(host.NativeFilmLibraryTests.doClassCleanups)
        cls.lib=host.NativeFilmLibraryTests.lib

    def test_cache_matches_uncached_pixels_for_every_color_engine_and_reused_storage(self):
        width,height,stride=128,97,144;n=stride*height
        rng=random.Random(381)
        scratch=(C.c_uint8*(6*width*height+65536+32))()
        ok=host.STORE(lambda _,state:0)
        for film in (34,35,65,66,67,68):
            for noisy in (False,True,"collision") :
                state=host.State();self.lib.m10v_library_init(C.byref(state))
                self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,film,ok,None),0)
                # Include leak, grain, and halo. Low-entropy and all-noise inputs
                # exercise both hits and collisions; reusing scratch must reset keys.
                state.effects[0][1]=8;state.effects[0][2]=5;state.effects[0][4]=1
                import zlib
                state.crc=zlib.crc32(bytes(state)[:100])
                source=(rng.randbytes(n),rng.randbytes(n)) if noisy else ((bytes(range(256))*((n+255)//256))[:n],bytes([122,143])*(n//2))
                if noisy=="collision":
                    # Force the input probe to select cache, then make other
                    # pixels noisy so the active loop must handle collisions.
                    a,b=map(bytearray,source)
                    for row in range(16):
                        for col in range(32):
                            at=row*(height>>4)*stride+col*((width>>5)&~1)
                            a[at:at+2]=bytes([64,65]);b[at:at+2]=bytes([122,143])
                    source=(bytes(a),bytes(b))
                outputs=[]
                for capacity in ((6*width*height if film==67 else 0),6*width*height+65536):
                    C.memset(scratch,173,C.sizeof(scratch))
                    y=(C.c_uint8*n).from_buffer_copy(source[0]);uv=(C.c_uint8*n).from_buffer_copy(source[1]);im=host.Image(y,uv,n,n,width,height,stride)
                    self.assertEqual(self.lib.m10v_library_render(C.byref(im),C.byref(state),0,None,0xffffffff,scratch,capacity),0)
                    outputs.append((bytes(y),bytes(uv)))
                    self.assertEqual(bytes(scratch)[capacity:],bytes([173])*(C.sizeof(scratch)-capacity))
                self.assertEqual(outputs[0],outputs[1],(film,noisy))

    def test_color_cache_bounds_lut_calls_on_repeated_input(self):
        import shutil,subprocess,tempfile
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            source=(root/'native/gr3/film_5207.c').read_text().replace('void m10v_5207_rgb(const uint8_t rgb[3],uint8_t out[3]){','void m10v_5207_rgb(const uint8_t rgb[3],uint8_t out[3]){++lut_calls;')
            path=Path(tmp)/'probe.c'
            path.write_text('static unsigned lut_calls;\n'+source+'\nunsigned probe_calls(void){return lut_calls;}\nunsigned probe_enabled(void *memory,const m10v_library_image *im){return m10v_color_cache_prepare(memory,im)!=0;}\n')
            out=Path(tmp)/'probe.dylib'
            subprocess.run([shutil.which('clang'),'-O2','-dynamiclib','-I',str(root/'native/gr3'),str(path),str(root/'native/gr3/film_harman.c'),str(root/'native/gr3/film_curated.c'),str(root/'native/gr3/film_newstocks.c'),str(root/'native/gr3/film_style_filters_0.c'),str(root/'native/gr3/film_style_filters_1.c'),'-o',str(out)],check=True,capture_output=True)
            lib=C.CDLL(str(out));render=lib.m10v_5207_texture_cached_q8
            render.argtypes=[C.POINTER(host.Image),C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p]
            n=6000*4;y=(C.c_uint8*n)(*([64]*n));uv=(C.c_uint8*n)(*([128]*n))
            image=host.Image(y,uv,n,n,6000,4,6000);effects=(C.c_uint8*8)()
            cache=(C.c_uint32*(65536//4))()
            render(C.byref(image),effects,0,42,1,cache)
            self.assertEqual(lib.probe_calls(),1)
            lib.probe_enabled.argtypes=[C.c_void_p,C.POINTER(host.Image)]
            rng=random.Random(2);C.memmove(y,rng.randbytes(n),n);C.memmove(uv,rng.randbytes(n),n)
            self.assertEqual(lib.probe_enabled(cache,C.byref(image)),0)
