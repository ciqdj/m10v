"""Retired texture performs no hash work and preserves exact color/padding."""
import ctypes as C
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Image
ROOT = Path(__file__).resolve().parents[1]

class TextureWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.libs=[]
        for name,source in [('reference',(ROOT/'tests/fixtures/gr3_texture_reference.c').read_text()),
                            ('current',(ROOT/'native/gr3/film_5207.c').read_text())]:
            source=source.replace('static uint32_t random32(uint32_t x){','static uint32_t random32(uint32_t x){++hashes;')
            path=Path(cls.tmp.name)/(name+'.c')
            path.write_text('static unsigned hashes;\n'+source+'''
unsigned probe(m10v_library_image *im,const m10v_film_effects *e,unsigned grain,unsigned seed,unsigned color){
 hashes=0;m10v_5207_texture_q8(im,e,grain,seed,color);return hashes;
}
''')
            out=path.with_suffix('.dylib')
            subprocess.run([shutil.which('clang'),'-O2','-dynamiclib','-I',str(ROOT/'native/gr3'),str(path),str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c'),str(ROOT/'native/gr3/film_d76_0.c'),str(ROOT/'native/gr3/film_d76_1.c'),'-o',str(out)],check=True,capture_output=True)
            lib=C.CDLL(str(out));lib.probe.argtypes=[C.POINTER(Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32];cls.libs.append(lib)

    def run_texture(self,width,height,size,gain=0,color=1,grain=768,seed=42,position=5):
        stride=width+8;n=stride*height;rng=random.Random(5207+width)
        initial=(rng.randbytes(n)+bytes([173])*32,rng.randbytes(n)+bytes([197])*32)
        e=(C.c_uint8*8)(size,gain,position,8,1,0,0,0)
        outputs=[];counts=[]
        for index,lib in enumerate(self.libs):
            y=(C.c_uint8*len(initial[0])).from_buffer_copy(initial[0]);uv=(C.c_uint8*len(initial[1])).from_buffer_copy(initial[1])
            image=Image(y,uv,n,n,width,height,stride)
            counts.append(lib.probe(C.byref(image),(C.c_uint8*8)() if index==0 else e,0 if index==0 else grain,seed,color));outputs.append((bytes(y),bytes(uv)))
        self.assertEqual(outputs[0],outputs[1])
        return counts[1]

    def test_retired_grain_hash_work_is_zero_at_full_width(self):
        for size in (0,1,2):
            with self.subTest(size=size):
                calls=self.run_texture(6000,2,size)
                self.assertEqual(calls,0)

    def test_legacy_texture_args_preserve_exact_color_and_partial_rows(self):
        for width,height in ((2,1),(18,7),(128,96),(6000,2)):
            for size in (0,1,2):
                for color in (0,1,2,3,4,5):
                    for gain in (0,8):
                        with self.subTest(width=width,size=size,color=color,gain=gain):
                            self.run_texture(width,height,size,gain=gain,color=color,seed=0xffffffff)
        for position in range(6):
            self.run_texture(38,9,2,gain=8,color=0,grain=0,position=position)

    def test_retired_leak_hash_work_is_zero(self):
        # A full-width crop: leak coordinates repeat many times, but the exact
        # field needs at most 256 rows of 256 cells (plus randomized position).
        calls=self.run_texture(6000,400,2,gain=8,color=1,grain=0)
        self.assertEqual(calls,0)
