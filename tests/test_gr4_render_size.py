"""Full GR IV dimensions must reach the shared renderer without weakening GR3 limits."""
import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest
from tests.test_gr3_m10v_library import State,Image
ROOT=Path(__file__).resolve().parents[1]
class Gr4RenderSizeTests(unittest.TestCase):
    def test_gr4_full_resolution_and_padding(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'render.dylib'
            from scripts.build_gr4_m10v_library import gr4_renderer_source
            core=Path(d)/'gr4-core.c';core.write_text(gr4_renderer_source())
            subprocess.run(['clang','-shared','-fPIC','-O2','-I'+str(ROOT/'native/gr3'),str(core),
                *[str(ROOT/'native/gr3'/s) for s in ('halation_core.c','film_5207.c','film_harman.c','film_curated.c')],'-o',str(out)],check=True,capture_output=True)
            lib=C.CDLL(str(out));state=State();lib.m10v_library_init(C.byref(state))
            # Original 6000-pixel bound rejected GR4 full resolution before reading pixels.
            # Empty capacities still fail, ensuring validation remains bounded.
            w,h,stride=6256,4176,6288;n=stride*h
            y=(C.c_uint8*n)();uv=(C.c_uint8*n)();C.memset(y,96,n);C.memset(uv,128,n)
            im=Image(y,uv,n,n,w,h,stride)
            self.assertEqual(lib.m10v_library_render(C.byref(im),C.byref(state),0,None,1,None,0),0)
            self.assertEqual(y[w],96);self.assertEqual(uv[w],128)
