"""Full texture path must execute the new block and retain scalar tail bytes."""
import ctypes as C
import random,shutil,subprocess,tempfile,unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Image,ROOT

class TextureBlockIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
  cls.libs=[]
  wrap=Path(cls.temp.name)/'block.c'
  wrap.write_text('#define m10v_texture_block8 block_impl\n#define m10v_texture_block8_cached cached_impl\n#include "m10v_texture_accel.c"\n#undef m10v_texture_block8\n#undef m10v_texture_block8_cached\n'
   'static unsigned calls; unsigned block_calls(void){return calls;}\n'
   'int m10v_texture_block8(uint8_t*y,uint8_t*u,const uint8_t*l,const m10v_texture_block_params*p){++calls;return block_impl(y,u,l,p);}\n'
   'int m10v_texture_block8_cached(uint8_t*y,uint8_t*u,const uint8_t*l,const m10v_texture_block_params*p,void*c){++calls;return cached_impl(y,u,l,p,c);}\n')
  for enabled in (0,1):
   out=Path(cls.temp.name)/f'path{enabled}.dylib'
   subprocess.run([shutil.which('clang'),'-O2','-dynamiclib','-DM10V_SPATIAL_NEON=1',f'-DM10V_TEXTURE_NEON={enabled}',
    '-DM10V_FILM_COLOR_CANDIDATE=1','-I',str(ROOT/'native/gr3'),str(ROOT/'native/gr3/film_5207.c'),
    str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/m10v_spatial_accel.c'),str(wrap),'-o',str(out)],check=True,capture_output=True)
   lib=C.CDLL(str(out));lib.m10v_5207_texture_q8.argtypes=[C.POINTER(Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32]
   cls.libs.append(lib)
 def test_enabled_full_color_uses_blocks_and_retains_all_effects_and_tails(self):
  for width,height in ((2,1),(6,3),(8,3),(10,5),(18,7),(6000,2)):
   for color in (1,2,3,4,5):
    for size,grain,gain in ((0,0,0),(1,768,8),(2,333,3)):
     with self.subTest(width=width,color=color,size=size,grain=grain,gain=gain):
      n=(width+8)*height;rng=random.Random(width+color+grain)
      initial=(rng.randbytes(n+32),rng.randbytes(n+32));outputs=[]
      count=self.libs[1].block_calls()
      for lib in self.libs:
       y=C.create_string_buffer(initial[0]);uv=C.create_string_buffer(initial[1]);im=Image(C.cast(y,C.POINTER(C.c_uint8)),C.cast(uv,C.POINTER(C.c_uint8)),n,n,width,height,width+8)
       e=(C.c_uint8*8)(size,gain,5,8,1,0,0,0)
       lib.m10v_5207_texture_q8(C.byref(im),e,grain,0xffffffff,color)
       outputs.append((y.raw,uv.raw))
      self.assertEqual(outputs[0],outputs[1])
      self.assertEqual(self.libs[1].block_calls()-count,(width//8)*height)
 def test_cache_enabled_image_still_executes_exact_blocks_and_reports_real_coverage(self):
  width,height,stride=66,5,74;n=stride*height
  for color in (1,2,3,4,5):
   for grain in (0,768,921):
    outputs=[]
    for lib in self.libs:
     y=C.create_string_buffer(bytes([121])*(n+32));uv=C.create_string_buffer(bytes([97,151])*((n+32)//2))
     im=Image(C.cast(y,C.POINTER(C.c_uint8)),C.cast(uv,C.POINTER(C.c_uint8)),n,n,width,height,stride)
     e=(C.c_uint8*8)(1,8,5,8,1,0,0,0);cache=(C.c_uint32*16384)();stats=(C.c_uint32*3)(0,0,0)
     f=lib.m10v_5207_texture_cached_stats_q8
     f.argtypes=[C.POINTER(Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p]
     f(C.byref(im),e,grain,42,color,cache,stats);outputs.append((y.raw,uv.raw))
     if lib is self.libs[1]:
      self.assertEqual(stats[0],(width//8)*8*height)
      self.assertEqual(stats[2]&3,3)
      self.assertGreater(stats[1],0)
    self.assertEqual(outputs[0],outputs[1])
