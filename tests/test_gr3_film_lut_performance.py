"""Exact tetrahedral LUT regression; opt-in timing gate for optimization work.

M10V_ENFORCE_LUT_PERF=1 python3 -m unittest tests.test_gr3_film_lut_performance
"""
import ctypes as C
import os
import shutil
import statistics
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

REFERENCE = r'''
#include "film_5207.h"
#include "film_harman.h"
#include "film_5207_data.h"
#include "film_harman_data.h"
static void reference(unsigned variant,const unsigned char rgb[3],unsigned char out[3]) {
 const uint8_t (*table)[3]=variant?m10v_harman_luts[variant-1]:m10v_5207_lut;
 unsigned p[3],f[3],order[3]={0,1,2};
 for(unsigned c=0;c<3;c++){unsigned q=(unsigned)rgb[c]*14;p[c]=q/255;if(p[c]>13)p[c]=13;f[c]=q-p[c]*255;}
 for(unsigned i=0;i<2;i++)for(unsigned j=i+1;j<3;j++)if(f[order[j]]>f[order[i]]){unsigned t=order[i];order[i]=order[j];order[j]=t;}
 unsigned index=(p[0]*15+p[1])*15+p[2];static const unsigned step[3]={225,15,1};
 int total[3];for(unsigned c=0;c<3;c++)total[c]=(int)table[index][c]*255;
 for(unsigned i=0;i<3;i++){unsigned next=index+step[order[i]];
  for(unsigned c=0;c<3;c++)total[c]+=(int)f[order[i]]*((int)table[next][c]-(int)table[index][c]);index=next;}
 for(unsigned c=0;c<3;c++)out[c]=(uint8_t)((total[c]+127)/255);
}
static void current(unsigned variant,const unsigned char rgb[3],unsigned char out[3]) {
 if(variant)m10v_harman_rgb(variant-1,rgb,out);else m10v_5207_rgb(rgb,out);
}
unsigned compare(unsigned variant) {
 for(unsigned n=0;n<16777216;n++) {
  uint8_t rgb[3]={(uint8_t)(n>>16),(uint8_t)(n>>8),(uint8_t)n},a[3],b[3];
  reference(variant,rgb,a);current(variant,rgb,b);
  if(a[0]!=b[0]||a[1]!=b[1]||a[2]!=b[2])return n+1;
 }
 return 0;
}
uint64_t benchmark(unsigned variant,unsigned original) {
 uint64_t sum=0;unsigned random=0x5207250d;
 for(unsigned n=0;n<1048576;n++) {
  random^=random<<13;random^=random>>17;random^=random<<5;
  uint8_t rgb[3]={(uint8_t)(random>>16),(uint8_t)(random>>8),(uint8_t)random},out[3];
  if(original)reference(variant,rgb,out);else current(variant,rgb,out);
  sum+=out[0]+257u*out[1]+65537u*out[2];
 }
 return sum;
}
'''


class FilmLutPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        wrapper=Path(cls.tmp.name)/'lut.c';wrapper.write_text(REFERENCE)
        out=wrapper.with_suffix('.dylib')
        subprocess.run([shutil.which('clang'),'-Os','-dynamiclib','-I',str(ROOT/'native/gr3'),str(wrapper),str(ROOT/'native/gr3/film_5207.c'),str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c'),'-o',str(out)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(out));cls.lib.compare.argtypes=[C.c_uint32]
        cls.lib.benchmark.argtypes=[C.c_uint32,C.c_uint32];cls.lib.benchmark.restype=C.c_uint64

    def test_all_rgb_values_and_harman_variants_are_byte_identical(self):
        # Every input includes cube corners, ties, clipped endpoints, and all
        # six tetrahedron orderings, with no sampled-only equivalence claim.
        for variant in range(5):
            with self.subTest(variant=variant):self.assertEqual(self.lib.compare(variant),0)

    @unittest.skipUnless(os.environ.get('M10V_ENFORCE_LUT_PERF'),'optional host timing gate')
    def test_host_lut_reduces_median_runtime_by_at_least_ten_percent(self):
        for variant in (0,4):
            samples=[[],[]];sums=[]
            for iteration in range(5):
                for original in ((0,1) if iteration&1 else (1,0)):
                    start=time.perf_counter();checksum=self.lib.benchmark(variant,original)
                    samples[original].append(time.perf_counter()-start);sums.append(checksum)
            self.assertEqual(len(set(sums)),1)
            current,reference=map(statistics.median,samples)
            print(f'LUT variant={variant}: current={current:.6f}s reference={reference:.6f}s ratio={current/reference:.3f}',flush=True)
            self.assertLess(current,reference*0.90)


if __name__=='__main__':unittest.main()
