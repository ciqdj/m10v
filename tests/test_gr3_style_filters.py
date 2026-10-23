"""Sparse style-filter identities, independent LUT interpolation and SD validation."""
import ctypes as C,json,random,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StyleFiltersTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);out=Path(cls.tmp.name)/'filters.so'
  sources=['film_harman.c','film_curated.c','film_newstocks.c','film_d76_0.c','film_d76_1.c']
  sources += [p.name for p in sorted((ROOT/'native/gr3').glob('film_style_filters_*.c'))]
  subprocess.run(['clang','-shared','-fPIC','-O2',*[str(ROOT/'native/gr3'/p) for p in sources],'-o',str(out)],check=True,capture_output=True)
  cls.lib=C.CDLL(str(out));cls.rgb=cls.lib.m10v_harman_rgb;cls.rgb.argtypes=[C.c_uint32,C.POINTER(C.c_uint8),C.POINTER(C.c_uint8)]
 def test_leica_is_neutral_instead_of_passthrough(self):
  out=(C.c_uint8*3)();self.rgb(15,(C.c_uint8*3)(200,30,10),out)
  self.assertEqual(out[0],out[1]);self.assertEqual(out[1],out[2])
 def test_native_tables_match_independent_integer_interpolation(self):
  stocks=json.loads((ROOT/'web/gr3/style-filters-luts.json').read_text())['stocks'];rng=random.Random(290296)
  cases=[(r,g,b) for r in [0,255] for g in [0,255] for b in [0,255]]+[(i,i,i) for i in range(256)]+[tuple(rng.randrange(256) for _ in range(3)) for _ in range(1024)]
  for variant,stock in enumerate(stocks,15):
   table=stock['values']
   for rgb in cases:
    q=[v*14 for v in rgb];base=[min(v//255,13) for v in q];f=[q[i]-base[i]*255 for i in range(3)]
    axes=sorted(range(3),key=lambda i:-f[i]);w=[255-f[axes[0]],f[axes[0]]-f[axes[1]],f[axes[1]]-f[axes[2]],f[axes[2]]]
    at=(base[0]*225+base[1]*15+base[2])*3;corners=[at]
    for axis in axes:corners.append(corners[-1]+[675,45,3][axis])
    expected=[(sum(w[j]*table[corners[j]+c] for j in range(4))+127)//255 for c in range(3)]
    out=(C.c_uint8*3)();self.rgb(variant,(C.c_uint8*3)(*rgb),out);self.assertEqual(list(out),expected)
 def test_sparse_journal_selection_failure_atomicity_and_padding(self):
  from tests import test_gr3_m10v_library as fixture
  out=Path(self.tmp.name)/'full.so'
  sources=['m10v_library.c','halation_core.c','film_5207.c','film_harman.c','film_curated.c','film_newstocks.c','film_style_filters_0.c','film_style_filters_1.c','film_d76_0.c','film_d76_1.c']
  subprocess.run(['clang','-shared','-fPIC','-O2',*[str(ROOT/'native/gr3'/p) for p in sources],'-o',str(out)],check=True,capture_output=True)
  lib=C.CDLL(str(out));lib.m10v_library_select.argtypes=[C.POINTER(fixture.State),C.c_uint32,C.c_uint32,fixture.STORE,C.c_void_p]
  lib.m10v_library_render.argtypes=[C.POINTER(fixture.Image),C.POINTER(fixture.State),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32]
  lib.m10v_library_name.restype=C.c_char_p;state=fixture.State();lib.m10v_library_init(C.byref(state))
  ok=fixture.STORE(lambda ctx,next:0);bad=fixture.STORE(lambda ctx,next:-1);others=bytes(state.slots)[8:]
  for film in range(291,298):
   before=bytes(state);self.assertEqual(lib.m10v_library_select(C.byref(state),0,film,bad,None),-2);self.assertEqual(bytes(state),before)
   self.assertEqual(lib.m10v_library_select(C.byref(state),0,film,ok,None),0);self.assertEqual(lib.m10v_library_valid(C.byref(state)),1)
   self.assertEqual(bytes(state.slots)[8:],others);self.assertEqual(state.effects[0][0],0);self.assertIsNotNone(lib.m10v_library_name(film))
   y=(C.c_uint8*4)(100,160,91,92);uv=(C.c_uint8*4)(80,180,81,82);im=fixture.Image(y,uv,4,4,2,1,4)
   self.assertEqual(lib.m10v_library_render(C.byref(im),C.byref(state),0,None,0,None,0),0)
   self.assertEqual(list(y)[2:],[91,92]);self.assertEqual(list(uv)[2:],[81,82]);self.assertNotEqual((list(y)[:2],list(uv)[:2]),([100,160],[80,180]))
   if film==291:self.assertEqual(list(uv)[:2],[128,128])
  before=bytes(state);self.assertEqual(lib.m10v_library_select(C.byref(state),0,298,ok,None),-1);self.assertEqual(bytes(state),before)
 def test_sparse_sd_records_cross_node_native_boundary(self):
  import struct,zlib
  out=Path(self.tmp.name)/'sd.so';subprocess.run(['clang','-shared','-fPIC','-O2',str(ROOT/'native/gr3/m10v_sd_library.c'),'-o',str(out)],check=True,capture_output=True)
  lib=C.CDLL(str(out));lib.m10v_sd_header.argtypes=[C.c_void_p,C.c_uint32];lib.m10v_sd_record.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32]
  pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack([291,292,293,294,295,296,297]));"],cwd=ROOT)
  self.assertEqual(lib.m10v_sd_header(pack[:4096],len(pack)),7)
  for i in range(7):
   record=pack[4096+i*12288:4096+(i+1)*12288];self.assertEqual(lib.m10v_sd_record(record,len(record),291+i),291+i)
   damaged=bytearray(record);damaged[64]^=1;struct.pack_into('<I',damaged,12284,zlib.crc32(damaged[:-4]));self.assertEqual(lib.m10v_sd_record(bytes(damaged),len(damaged),291+i),0)
 def test_provenance_and_embedded_bytes(self):
  from scripts.verify_gr3_style_filters_reference import verify
  self.assertEqual([len(p) for p in verify(ROOT)],[10125]*7)
if __name__=='__main__':unittest.main()
