import ctypes,json,random,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class MonoStorage(unittest.TestCase):
 def test_scalar_independent_tetrahedral(self):
  payloads=[bytes(s['values']) for s in json.loads((ROOT/'web/gr3/d76-luts.json').read_text())['stocks']]
  with tempfile.TemporaryDirectory() as d:
   lib=Path(d)/'scalar.so'
   sources=['film_harman','film_curated','film_newstocks','film_style_filters_0','film_style_filters_1','film_d76_0','film_d76_1']
   subprocess.run(['clang','-shared','-fPIC','-O2','-o',str(lib)]+[str(ROOT/f'native/gr3/{s}.c') for s in sources],check=True)
   fn=ctypes.CDLL(str(lib)).m10v_harman_rgb
   rng=random.Random(299305)
   samples=[(r,g,b) for r in (0,255) for g in (0,255) for b in (0,255)]+[(v,v,v) for v in range(256)]+[tuple(rng.randrange(256) for _ in range(3)) for _ in range(1200)]
   for stock,payload in enumerate(payloads):
    for rgb in samples:
     q=[v*14 for v in rgb];pos=[min(v//255,13) for v in q];fractions=[q[i]-255*pos[i] for i in range(3)];axes=sorted(range(3),key=lambda i:-fractions[i]);steps=[225,15,1]
     index=pos[0]*225+pos[1]*15+pos[2];ix=[index,index+steps[axes[0]],index+steps[axes[0]]+steps[axes[1]],index+241];f=[fractions[i] for i in axes];w=[255-f[0],f[0]-f[1],f[1]-f[2],f[2]]
     expected=(sum(payload[j*3]*weight for j,weight in zip(ix,w))+127)//255
     inp=(ctypes.c_uint8*3)(*rgb);out=(ctypes.c_uint8*3)();fn(stock+23,inp,out);self.assertEqual(bytes(out),bytes([expected]*3))
 def test_arm_mono_against_rgb_oracle(self):
  from scripts.build_gr3_texture_accel import build
  from tests.test_gr3_texture_accel import oracle
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,arm_const as A
  import struct
  with tempfile.TemporaryDirectory() as d:
   report=build(d);u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A9)
   u.mem_map(report['base'],65536);u.mem_write(report['base'],(Path(d)/'m10v-texture-arm.bin').read_bytes());u.mem_map(0x55000000,0x20000)
   u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
   rng=random.Random(299305)
   for stock in json.loads((ROOT/'web/gr3/d76-luts.json').read_text())['stocks']:
    payload=bytes(stock['values']);u.mem_write(0x55001000,payload[::3]);u.mem_write(0x55004000,bytes(80));u.mem_write(0x55010000,bytes(65536))
    for j in range(40):
     y=bytes(rng.randrange(256) for _ in range(8));uv=bytes([128]*8) if j<10 else bytes(rng.randrange(256) for _ in range(8));expected=oracle(y,uv,payload,[0]*8,0,[0]*8,[0]*8)
     for repeat in range(2):
      u.mem_write(0x55000100,y);u.mem_write(0x55000200,uv);u.mem_write(0x5500e000,struct.pack('<I',0x55010000))
      for i,v in enumerate([0x55000100,0x55000200,0x55001000,0x55004000]):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
      u.reg_write(A.UC_ARM_REG_SP,0x5500e000);u.reg_write(A.UC_ARM_REG_LR,0x5500f000);u.emu_start(report['symbols']['m10v_texture_mono_block8_cached'],0x5500f000,count=30000)
      self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x5500f000);self.assertEqual(tuple(bytes(u.mem_read(a,8)) for a in (0x55000100,0x55000200)),expected)
 def test_storage_and_vector_equivalence(self):
  from scripts.verify_gr3_d76_reference import verify
  payloads=verify(ROOT)
  for bank,n in [(0,4),(1,3)]:
   self.assertIn(f'[{n}][3375]',(ROOT/f'native/gr3/film_d76_{bank}_data.h').read_text())
   self.assertNotIn('[3375][3]',(ROOT/f'native/gr3/film_d76_{bank}_data.h').read_text())
  with tempfile.TemporaryDirectory() as d:
   lib=Path(d)/'mono.so';subprocess.run(['clang','-shared','-fPIC','-O2','-o',str(lib),str(ROOT/'native/gr3/m10v_texture_accel.c')],check=True)
   dll=ctypes.CDLL(str(lib));mono=dll.m10v_texture_mono_block8_cached;rgb=dll.m10v_texture_block8_cached
   rng=random.Random(299305);params=(ctypes.c_uint32*20)()
   for payload in payloads:
    compact=(ctypes.c_uint8*3375).from_buffer_copy(payload[::3]);expanded=(ctypes.c_uint8*10125).from_buffer_copy(payload)
    ca=(ctypes.c_uint32*16384)();cb=(ctypes.c_uint32*16384)()
    for j in range(160):
     ys=bytes(rng.randrange(256) for _ in range(8));uvs=bytes([128]*8) if j<20 else bytes(rng.randrange(256) for _ in range(8))
     for repeat in range(2):
      ya=(ctypes.c_uint8*8).from_buffer_copy(ys);yb=(ctypes.c_uint8*8).from_buffer_copy(ys);ua=(ctypes.c_uint8*8).from_buffer_copy(uvs);ub=(ctypes.c_uint8*8).from_buffer_copy(uvs)
      self.assertEqual(mono(ya,ua,compact,params,ca),rgb(yb,ub,expanded,params,cb));self.assertEqual(bytes(ya),bytes(yb));self.assertEqual(bytes(ua),bytes(ub))
if __name__=='__main__':unittest.main()
