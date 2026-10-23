import ctypes as C,json,random,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NewStocksTests(unittest.TestCase):
 def test_reference_has_six_independent_pinned_models(self):
  from scripts.verify_gr3_newstocks_reference import verify
  tables=verify(ROOT)
  self.assertEqual(len(tables),6)
  self.assertEqual(len(set(tables)),6)
 def test_native_tetrahedra_match_independent_reference(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'new.so';subprocess.run(['clang','-shared','-fPIC','-O2',str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c'),'-o',str(p)],check=True,capture_output=True)
   lib=C.CDLL(str(p));fn=lib.m10v_harman_rgb;fn.argtypes=[C.c_uint32,C.POINTER(C.c_uint8),C.POINTER(C.c_uint8)]
   stocks=json.loads((ROOT/'web/gr3/newstocks-luts.json').read_text())['stocks'];rng=random.Random(7378)
   cases=[(v,v,v) for v in range(256)]+[tuple(rng.randrange(256) for _ in range(3)) for _ in range(1024)]
   for variant,spec in enumerate(stocks,8):
    table=spec['values']
    for rgb in cases:
     q=[v*14 for v in rgb];base=[min(v//255,13) for v in q];f=[q[i]-base[i]*255 for i in range(3)];axes=sorted(range(3),key=lambda i:-f[i]);w=[255-f[axes[0]],f[axes[0]]-f[axes[1]],f[axes[1]]-f[axes[2]],f[axes[2]]];at=(base[0]*225+base[1]*15+base[2])*3;corners=[at]
     for a in axes:corners.append(corners[-1]+[675,45,3][a])
     expected=[(sum(w[j]*table[corners[j]+c] for j in range(4))+127)//255 for c in range(3)]
     out=(C.c_uint8*3)();fn(variant,(C.c_uint8*3)(*rgb),out);self.assertEqual(list(out),expected)
if __name__=='__main__':unittest.main()
