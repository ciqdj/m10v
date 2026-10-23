"""Sparse halo work may skip only provably zero bilinear support; all pixels stay exact."""
import ctypes as C,hashlib,random,shutil,subprocess,tempfile,unittest
from pathlib import Path
from tests import test_gr3_m10v_library as h
ROOT=Path(__file__).resolve().parents[1]
class SparsePhoenixTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);p=Path(cls.tmp.name)
  source=p/'probe.c';source.write_text('#include "'+str(ROOT/'native/gr3/m10v_library.c')+'"\n#include "'+str(ROOT/'tests/fixtures/gr3_phoenix_halation_reference.h')+'"\nvoid probe(m10v_library_image *im,m10v_slot *v,uint8_t *s,uint32_t ref){uint32_t shift=0,w=im->width,h=im->height;while(w>384||h>256){shift++;w=(im->width+(1u<<shift)-1)>>shift;h=(im->height+(1u<<shift)-1)>>shift;}if(ref){reference_phoenix_source(im,v,s,w,h,shift);reference_phoenix_compose(im,v,s,w,h,shift);}else{phoenix_halation_source(im,v,s,w,h,shift);phoenix_halation_compose(im,v,s,w,h,shift);}}')
  out=p/'probe.dylib';subprocess.run([shutil.which('clang'),'-O2','-dynamiclib',str(source),str(ROOT/'native/gr3/film_5207.c'),str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c'),str(ROOT/'native/gr3/film_d76_0.c'),str(ROOT/'native/gr3/film_d76_1.c'),str(ROOT/'native/gr3/halation_core.c'),'-o',str(out)],check=True,capture_output=True)
  cls.lib=C.CDLL(str(out));cls.lib.probe.argtypes=[C.POINTER(h.Image),C.POINTER(h.Slot),C.c_void_p,C.c_uint32]
 def test_sparse_and_boundary_images_match_baseline_exactly(self):
  for w,ht in ((2,1),(18,9),(386,259),(6000,2),(6000,4000)):
   for scene in ('dark','tiny','border','panel'):
    n=(w+8)*ht;initial=bytearray([64])*n;uv=bytes([128])*n
    if scene!='dark':
     for row in range(ht//2,min(ht,ht//2+(1 if scene=='tiny' else 8))):
      for x in range(0 if scene=='border' else w//2,min(w,(0 if scene=='border' else w//2)+(1 if scene=='tiny' else 8))):initial[row*(w+8)+x]=255
    for row in range(ht):initial[row*(w+8)+w:(row+1)*(w+8)]=bytes([173])*8
    for gain,spread in ((1,0),(3,3),(8,8)):
     outputs=[]
     for ref in (1,0):
      y=(C.c_uint8*n).from_buffer_copy(initial);c=(C.c_uint8*n).from_buffer_copy(uv);im=h.Image(y,c,n,n,w,ht,w+8);v=h.Slot(67,0,0,gain,spread,5,2);scratch=(C.c_uint8*(6*384*256))()
      self.lib.probe(C.byref(im),C.byref(v),scratch,ref);outputs.append(hashlib.sha256(bytes(y)+bytes(c)).hexdigest())
     self.assertEqual(*outputs,(w,ht,scene,gain,spread))
