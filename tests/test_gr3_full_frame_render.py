"""Golden 24MP output from the pre-optimization renderer, including row padding."""
import ctypes as C
import hashlib
import unittest
from tests import test_gr3_m10v_library as host

class FullFrameRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host.NativeFilmLibraryTests.setUpClass()
        cls.addClassCleanup(host.NativeFilmLibraryTests.doClassCleanups)
        cls.lib=host.NativeFilmLibraryTests.lib

    def test_24mp_slow_films_preserve_preoptimization_output_and_padded_rows(self):
        width,height,stride=6000,4000,6016;n=stride*height
        original_y=(bytes(range(256))*((n+255)//256))[:n]
        original_c=(bytes([122,143])*((n+1)//2))[:n]
        # Captured from the original -Os C implementation, before any changes.
        expected={33:'2e3dde220361e6c2ac3b3b1e0f60b3459834a661e8addba7c081fdd3a0ce3ddd',
                  66:'2a3687c72d85714fdb0c1fb35603ecc49abfd55676c1eaa2271d40a6b1d2b3ab',
                  67:'bedc8f0f702e5d691cdeb6e913f34ce872d9335858c4da837ad3fbb59a959f70'}
        ok=host.STORE(lambda _,state:0)
        for film,digest in expected.items():
            with self.subTest(film=film):
                state=host.State();self.lib.m10v_library_init(C.byref(state))
                self.assertEqual(self.lib.m10v_library_select(C.byref(state),0,film,ok,None),0)
                y=(C.c_uint8*n).from_buffer_copy(original_y);uv=(C.c_uint8*n).from_buffer_copy(original_c)
                scratch=(C.c_uint8*(6*375*250))()
                image=host.Image(y,uv,n,n,width,height,stride)
                self.assertEqual(self.lib.m10v_library_render(C.byref(image),C.byref(state),0,None,42,scratch,len(scratch)),0)
                checksum=hashlib.sha256(bytes(y));checksum.update(bytes(uv))
                self.assertEqual(checksum.hexdigest(),digest)
