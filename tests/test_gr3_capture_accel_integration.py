"""Full CPU texture integration: SIMD batching preserves all existing effects."""
import ctypes as C,random,shutil,subprocess,tempfile,unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Image,ROOT

class CaptureAccelIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.libs=[]
  for accel in (0,1,2):
   path=Path(cls.tmp.name)/f'accel{accel}.dylib'
   spatial=ROOT/'native/gr3/m10v_spatial_accel.c'
   if accel==2:
    spatial=Path(cls.tmp.name)/'reject-noise.c'
    spatial.write_text((ROOT/'native/gr3/m10v_spatial_accel.c').read_text().replace('int m10v_spatial_grain_noise8(', 'int unused_grain_noise8(')+'\nint m10v_spatial_grain_noise8(const uint32_t*a,uint32_t b,uint32_t c,uint32_t d,uint32_t*e,int32_t*f){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;return -1;}\n')
   subprocess.run([shutil.which('clang'),'-O2','-dynamiclib',f'-DM10V_SPATIAL_NEON={int(accel>0)}','-DM10V_FILM_COLOR_CANDIDATE=1','-I',str(ROOT/'native/gr3'),str(ROOT/'native/gr3/film_5207.c'),str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(spatial),'-o',str(path)],check=True,capture_output=True)
   lib=C.CDLL(str(path));lib.m10v_5207_texture_q8.argtypes=[C.POINTER(Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32];cls.libs.append(lib)
 def test_full_texture_tiles_tails_and_all_color_variants_are_exact(self):
  for width,height in ((2,1),(6,7),(8,3),(10,5),(18,9),(6000,2)):
   for size in (0,1,2):
    for color in (0,1,2,3,4,5):
     with self.subTest(width=width,size=size,color=color):
      stride=width+8;n=stride*height;randomizer=random.Random(width+size)
      y0=randomizer.randbytes(n+32);uv0=randomizer.randbytes(n+32);outputs=[]
      effects=(C.c_uint8*8)(size,8,5,8,1,0,0,0)
      for lib in self.libs:
       y=(C.c_uint8*(n+32)).from_buffer_copy(y0);uv=(C.c_uint8*(n+32)).from_buffer_copy(uv0);im=Image(y,uv,n,n,width,height,stride)
       lib.m10v_5207_texture_q8(C.byref(im),effects,768,0xffffffff,color);outputs.append((bytes(y),bytes(uv)))
      self.assertEqual(outputs[0],outputs[1])
      self.assertEqual(outputs[0],outputs[2])
      for row in range(height):
       self.assertEqual(outputs[1][0][row*stride+width:(row+1)*stride],y0[row*stride+width:(row+1)*stride])
      self.assertEqual(outputs[1][0][n:],y0[n:]);self.assertEqual(outputs[1][1][n:],uv0[n:])
