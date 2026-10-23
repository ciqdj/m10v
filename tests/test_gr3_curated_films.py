"""New stocks: independent integer LUT reference against the C renderer."""
import ctypes as C,json,random,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class CuratedFilmsTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  path=Path(cls.tmp.name)/'lut.so'
  subprocess.run(['clang','-shared','-fPIC','-O2',str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c'),'-o',str(path)],check=True,capture_output=True)
  cls.lib=C.CDLL(str(path));cls.fn=cls.lib.m10v_harman_rgb
  cls.fn.argtypes=[C.c_uint32,C.POINTER(C.c_uint8),C.POINTER(C.c_uint8)]
 def test_assets_have_matching_provenance_and_c_web_bytes(self):
  from scripts.verify_gr3_curated_reference import verify
  self.assertEqual(list(map(len,verify(ROOT))),[10125]*4)
 def test_all_new_c_tables_match_independent_integer_tetrahedra(self):
  web=json.loads((ROOT/'web/gr3/curated-luts.json').read_text());rng=random.Random(697071)
  cases=[(r,g,b) for r in (0,255) for g in (0,255) for b in (0,255)]
  cases += [(i,i,i) for i in range(256)]+[tuple(rng.randrange(256) for _ in range(3)) for _ in range(1024)]
  for variant,spec in enumerate(web['stocks'],4):
   table=spec['values']
   for rgb in cases:
    q=[v*14 for v in rgb];base=[min(v//255,13) for v in q];f=[q[i]-base[i]*255 for i in range(3)]
    axes=sorted(range(3),key=lambda i:-f[i]);weights=[255-f[axes[0]],f[axes[0]]-f[axes[1]],f[axes[1]]-f[axes[2]],f[axes[2]]]
    at=(base[0]*225+base[1]*15+base[2])*3;corners=[at]
    for a in axes:corners.append(corners[-1]+[675,45,3][a])
    expected=[(sum(weights[j]*table[corners[j]+c] for j in range(4))+127)//255 for c in range(3)]
    out=(C.c_uint8*3)();self.fn(variant,(C.c_uint8*3)(*rgb),out)
    self.assertEqual(list(out),expected)
if __name__=='__main__':unittest.main()
