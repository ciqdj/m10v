import ctypes as C,json,subprocess,tempfile,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class Target(C.Structure):
 _fields_=[('matrix',C.c_int16*9),('post',C.c_int16*9),('curves',(C.c_uint16*256)*3)]
class Look(C.Structure):
 _fields_=[(k,C.c_uint32) for k in ['magic','version','generation','film','exposure','status','frame']]+[('target',Target)]
class Image(C.Structure):
 _fields_=[('y',C.POINTER(C.c_uint8)),('chroma',C.POINTER(C.c_uint8))]+[(k,C.c_uint32) for k in ['yn','cn','width','height','stride']]

class AnimeIntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);folder=Path(cls.tmp.name)
  wrapper=folder/'probe.c';wrapper.write_text('#include "m10v_library.h"\nuint32_t stages(const m10v_library_state*s,uint32_t slot,uint32_t mask){return m10v_library_cpu_stages(s,slot,mask);}\n')
  files=['m10v_library.c','film_5207.c','film_harman.c','film_curated.c','film_newstocks.c','film_style_filters_0.c','film_style_filters_1.c','film_d76_0.c','film_d76_1.c','halation_core.c','m10v_isp_native_look.c','m10v_isp_frame_color.c','m10v_isp_multiaxis.c']
  subprocess.run(['clang','-shared','-fPIC','-O2','-I',str(ROOT/'native/gr3'),str(wrapper),*[str(ROOT/'native/gr3'/f) for f in files],'-o',str(folder/'lib.so')],check=True,capture_output=True)
  cls.lib=C.CDLL(str(folder/'lib.so'))
  cls.lib.m10v_library_render_native.argtypes=[C.POINTER(Image),C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32]
  cls.lib.m10v_isp_native_look_prepare.argtypes=[C.POINTER(Look),C.c_uint32,C.c_uint32,C.c_uint32]
  cls.initial=subprocess.check_output(['node','--input-type=module','-e',"import{initialState}from'./node/gr3-native-library.mjs';import{defaultConfiguration}from'./web/gr3/native-library-state.mjs';const c=defaultConfiguration();c.slots[0].film=306;process.stdout.write(initialState(c));"],cwd=ROOT)
 def state(self,mode=0):
  raw=bytearray(self.initial);raw[103]=mode;raw[180:]=zlib.crc32(raw[:180]).to_bytes(4,'little');return C.create_string_buffer(bytes(raw),184)
 def test_native_unpacks_every_exact_quantized_knot(self):
  ref=json.loads((ROOT/'native/gr3/anime-e6-reference.json').read_text())
  self.assertEqual(C.sizeof(Look),1600)
  for q in ref['native_profiles_full']:
   s=Look();self.assertEqual(self.lib.m10v_isp_native_look_prepare(C.byref(s),q['film_id'],0,17),1)
   self.assertEqual(list(s.target.matrix),sum(q['matrix_q13'],[]));self.assertEqual(list(s.target.post),sum(q['post_q9'],[]))
   self.assertEqual([list(c) for c in s.target.curves],q['curves'])
 def test_mode_is_an_explicit_residual_after_isp_and_off_remains_zero(self):
  self.assertEqual(self.lib.stages(self.state(),0,1),0)
  for mode in [1,2,3]:self.assertEqual(self.lib.stages(self.state(mode),0,1),64)
 def test_spatial_render_preserves_native_colour_and_mode0_exactly(self):
  for mode in [0,1,2,3]:
   y=(C.c_uint8*16)(*([30,90,180,230]*4));uv=(C.c_uint8*16)(*([101,159]*8));im=Image(y,uv,16,16,4,4,4);scratch=(C.c_uint8*24)()
   original=bytes(y)+bytes(uv);state=self.state(mode)
   self.assertEqual(self.lib.m10v_library_render_native(C.byref(im),state,0,None,0,scratch,24,1),0)
   if not mode:self.assertEqual(bytes(y)+bytes(uv),original)
   else:self.assertNotEqual(bytes(y)+bytes(uv),original)
 def test_missing_isp_completion_never_dispatches_an_unrelated_cpu_lut(self):
  y=(C.c_uint8*4)(*([100]*4));uv=(C.c_uint8*4)(*([128]*4));im=Image(y,uv,4,4,2,2,2);original=bytes(y)+bytes(uv)
  self.assertEqual(self.lib.m10v_library_render_native(C.byref(im),self.state(1),0,None,0,None,0,0),-1)
  self.assertEqual(bytes(y)+bytes(uv),original)

if __name__=='__main__':unittest.main()
