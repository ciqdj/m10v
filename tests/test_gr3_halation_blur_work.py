"""Independent scalar blur oracle and boundary-work budget."""
import ctypes as C
import random
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Image, Slot
ROOT=Path(__file__).resolve().parents[1]

class BlurWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        source=(ROOT/'native/gr3/halation_energy.h').read_text().replace(
            'uint32_t n, int delta) {','uint32_t n, int delta) { ++edges;')
        path=Path(cls.tmp.name)/'blur.c'
        path.write_text('#include "m10v_library.h"\nstatic unsigned edges;\n'+source+'''
void effect(m10v_library_image *im,const m10v_slot *v,unsigned char *scratch,unsigned w,unsigned h,unsigned shift){m10v_800t_effects(im,v,scratch,w,h,shift);}
unsigned probe(unsigned short *a,unsigned short *b,unsigned w,unsigned h,unsigned passes,int d){
 edges=0;energy_blur(a,b,w,h,passes,d);return edges;
}
''')
        out=path.with_suffix('.dylib')
        subprocess.run([shutil.which('clang'),'-O2','-dynamiclib','-I',str(ROOT/'native/gr3'),str(path),'-o',str(out)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(out));cls.lib.probe.argtypes=[C.c_void_p,C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32,C.c_int]

    def test_empty_masks_and_weak_sources_match_frozen_original_renderer(self):
        source=ROOT/'tests/fixtures/gr3_halation_reference.h'
        path=Path(self.tmp.name)/'old-effect.c'
        path.write_text('#include "m10v_library.h"\n#include "'+str(source)+'"\n'+
            'void effect(m10v_library_image *im,const m10v_slot *v,unsigned char *scratch,unsigned w,unsigned h,unsigned shift){m10v_800t_effects(im,v,scratch,w,h,shift);}')
        out=path.with_suffix('.dylib')
        subprocess.run([shutil.which('clang'),'-O2','-dynamiclib','-I',str(ROOT/'native/gr3'),str(path),'-o',str(out)],check=True,capture_output=True)
        reference=C.CDLL(str(out))
        for lib in (reference,self.lib):lib.effect.argtypes=[C.POINTER(Image),C.POINTER(Slot),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32]
        for width,height in ((2,1),(128,96),(386,259),(6000,32)):
            shift=0
            while (width+(1<<shift)-1)>>shift>384 or (height+(1<<shift)-1)>>shift>256:shift+=1
            gw=(width+(1<<shift)-1)>>shift;gh=(height+(1<<shift)-1)>>shift
            stride=width+8;n=stride*height
            # Both empty; only neutral bloom active; only red halo active;
            # one raw energy value whose cell average rounds to zero.
            for light,cr,soft,single in ((64,128,0,False),(64,128,3,False),(215,128,3,False),(100,250,3,False),(64,128,0,True)):
                original_y=bytearray([light]*n);original_c=bytes([128,cr])*(n//2)
                if single:original_y[(height//2)*stride+width//2]=217
                outputs=[]
                for lib in (reference,self.lib):
                    y=(C.c_uint8*n).from_buffer_copy(original_y);uv=(C.c_uint8*n).from_buffer_copy(original_c)
                    im=Image(y,uv,n,n,width,height,stride);v=Slot(33,0,soft,8,3,5,2)
                    scratch=(C.c_uint8*(6*gw*gh))()
                    lib.effect(C.byref(im),C.byref(v),scratch,gw,gh,shift)
                    outputs.append((bytes(y),bytes(uv)))
                with self.subTest(width=width,light=light,cr=cr,soft=soft,single=single):self.assertEqual(outputs[0],outputs[1])

    def test_blur_hoists_row_bounds_and_preserves_replicated_edges(self):
        for w,h in ((1,1),(2,7),(7,2),(17,13),(375,250)):
            for distance in (1,2):
                rng=random.Random(w+h+distance);want=[rng.randrange(49929) for _ in range(w*h)]
                a=(C.c_uint16*(w*h))(*want);b=(C.c_uint16*(w*h))()
                calls=self.lib.probe(a,b,w,h,3,distance)
                for _ in range(3):
                    temp=[(want[y*w+max(0,x-distance)]+2*want[y*w+x]+want[y*w+min(w-1,x+distance)])>>2 for y in range(h) for x in range(w)]
                    want=[(temp[max(0,y-distance)*w+x]+2*temp[y*w+x]+temp[min(h-1,y+distance)*w+x])>>2 for y in range(h) for x in range(w)]
                self.assertEqual(list(a),want)
                with self.subTest(width=w,height=h,distance=distance):
                    self.assertLessEqual(calls,6*h)
