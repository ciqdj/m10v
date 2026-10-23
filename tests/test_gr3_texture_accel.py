import ctypes as C
import random,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def clip(v):return max(0,min(255,v))
def rq(v,b):return ((v+(1<<(b-1)))>>b) if v>=0 else -((-v+(1<<(b-1)))>>b)
def trunc(v,d):return v//d if v>=0 else -((-v)//d)
def oracle(y,uv,lut,light,grain,hashes,noise):
 out=[]
 for i in range(8):
  cb,cr=uv[i&~1]-128,uv[(i&~1)+1]-128
  rgb=[clip(y[i]+rq(91881*cr,16)),clip(y[i]-rq(22554*cb+46802*cr,16)),clip(y[i]+rq(116130*cb,16))]
  q=[v*14 for v in rgb];p=[min(v//255,13) for v in q];f=[q[j]-p[j]*255 for j in range(3)]
  axes=sorted(range(3),key=lambda j:-f[j]);s=[225,15,1];fs=[f[j] for j in axes];idx=(p[0]*15+p[1])*15+p[2]
  ix=[idx,idx+s[axes[0]],idx+s[axes[0]]+s[axes[1]],idx+241];w=[255-fs[0],fs[0]-fs[1],fs[1]-fs[2],fs[2]]
  rgb=[(sum(lut[a*3+c]*b for a,b in zip(ix,w))+127)//255 for c in range(3)]
  out.append(rgb)
 yo=[clip(rq(19595*r+38470*g+7471*b,16)) for r,g,b in out];uo=[]
 for i in range(0,8,2):
  r,g,b=[out[i][c]+out[i+1][c] for c in range(3)]
  uo += [clip(128+rq(-11059*r-21709*g+32768*b,17)),clip(128+rq(32768*r-27439*g-5329*b,17))]
 return bytes(yo),bytes(uo)
class TextureTests(unittest.TestCase):
 def test_module_exists(self):self.assertTrue((ROOT/'native/gr3/m10v_texture_accel.c').exists())
 def test_exact_random_extreme_host_and_arm(self):
  from scripts.build_gr3_texture_accel import build
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn import arm_const as A
  class Params(C.Structure):_fields_=[('light',C.c_uint8*8),('grain',C.c_uint32),('hashes',C.c_uint32*8),('noise',C.c_int32*8)]
  with tempfile.TemporaryDirectory() as td:
   report=build(td);self.assertLess(report['code_bytes'],8192)
   lib=Path(td)/'a.dylib';subprocess.run(['clang','-O2','-dynamiclib',str(ROOT/'native/gr3/m10v_texture_accel.c'),'-o',str(lib)],check=True,capture_output=True);fn=C.CDLL(str(lib)).m10v_texture_block8
   fn.argtypes=[C.c_void_p]*4
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A9);u.mem_map(report['base'],0x10000);u.mem_write(report['base'],(Path(td)/'m10v-texture-arm.bin').read_bytes());u.mem_map(0x55000000,0x10000)
   u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
   rng=random.Random(5207)
   for it in range(350):
    y=bytes(rng.randrange(256) for _ in range(8));uv=bytes(rng.randrange(256) for _ in range(8));lut=rng.randbytes(10125)
    if it<8:y=bytes([it%2*255]*8);uv=bytes([it//2%2*255,it//4%2*255]*4)
    light=[rng.randrange(256) for _ in range(8)] if it%3 else [0]*8;grain=[0,256,768,rng.randrange(769)][it%4];hashes=[rng.getrandbits(32) for _ in range(8)];noise=[rng.randrange(-170,170) for _ in range(8)]
    p=Params((C.c_uint8*8)(*light),grain,(C.c_uint32*8)(*hashes),(C.c_int32*8)(*noise));expected=oracle(y,uv,lut,light,grain,hashes,noise)
    yy=C.create_string_buffer(y+b'GUARD');uu=C.create_string_buffer(uv+b'GUARD');ll=C.create_string_buffer(lut)
    self.assertEqual(fn(yy,uu,ll,C.byref(p)),0);self.assertEqual((yy.raw[:8],uu.raw[:8]),expected);self.assertEqual((yy.raw[8:13],uu.raw[8:13]),(b'GUARD',b'GUARD'))
    for addr,data in [(0x55000100,y+b'GUARD'),(0x55000200,uv+b'GUARD'),(0x55001000,lut),(0x55004000,bytes(p))]:u.mem_write(addr,data)
    for i,v in enumerate([0x55000100,0x55000200,0x55001000,0x55004000]):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
    saved=[rng.getrandbits(64) for _ in range(8)]
    for i,v in enumerate(saved):u.reg_write(getattr(A,f'UC_ARM_REG_D{i+8}'),v)
    u.reg_write(A.UC_ARM_REG_SP,0x5500e000);u.reg_write(A.UC_ARM_REG_LR,0x5500f000);u.emu_start(report['symbols']['m10v_texture_block8'],0x5500f000,count=30000)
    self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x5500f000);self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),0)
    self.assertEqual(tuple(bytes(u.mem_read(a,8)) for a in (0x55000100,0x55000200)),expected)
    self.assertEqual([u.reg_read(getattr(A,f'UC_ARM_REG_D{i+8}')) for i in range(8)],saved)
    self.assertEqual(tuple(bytes(u.mem_read(a+8,5)) for a in (0x55000100,0x55000200)),(b'GUARD',b'GUARD'))

 def test_invalid_params_leave_output_unchanged(self):
  with tempfile.TemporaryDirectory() as td:
   lib=Path(td)/'a.dylib';subprocess.run(['clang','-O2','-dynamiclib',str(ROOT/'native/gr3/m10v_texture_accel.c'),'-o',str(lib)],check=True,capture_output=True);fn=C.CDLL(str(lib)).m10v_texture_block8;fn.argtypes=[C.c_void_p]*4
   y=C.create_string_buffer(bytes(range(8)));uv=C.create_string_buffer(bytes(range(8)));lut=C.create_string_buffer(bytes(10125));p=(C.c_uint32*19)()
   before=bytes(y),bytes(uv)
   for args in [(None,uv,lut,p),(y,None,lut,p),(y,uv,None,p)]:
    self.assertEqual(fn(*args),-1);self.assertEqual((bytes(y),bytes(uv)),before)
   self.assertEqual(fn(y,uv,lut,None),-1);self.assertEqual((bytes(y),bytes(uv)),before)
 def test_cached_full_keys_collisions_and_repeat_hits_host_arm(self):
  import struct
  from scripts.build_gr3_texture_accel import build
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn import arm_const as A
  class Params(C.Structure):_fields_=[('light',C.c_uint8*8),('grain',C.c_uint32),('hashes',C.c_uint32*8),('noise',C.c_int32*8)]
  with tempfile.TemporaryDirectory() as td:
   report=build(td);lib=Path(td)/'a.dylib';subprocess.run(['clang','-O2','-dynamiclib',str(ROOT/'native/gr3/m10v_texture_accel.c'),'-o',str(lib)],check=True,capture_output=True);fn=C.CDLL(str(lib)).m10v_texture_block8_cached;fn.argtypes=[C.c_void_p]*5
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A9);u.mem_map(report['base'],65536);u.mem_write(report['base'],(Path(td)/'m10v-texture-arm.bin').read_bytes());u.mem_map(0x55000000,0x20000);u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
   rng=random.Random(91520);cache=(C.c_uint32*16384)();u.mem_write(0x55010000,bytes(65536))
   for it in range(90):
    # Neutral chroma makes grayscale RGB keys exact; equal fractions exercise ties.
    ys=[rng.randrange(256) for _ in range(8)];y=bytes(ys);uv=bytes([128]*8);lut=rng.randbytes(10125)
    light=[0]*8
    if it%2:
     uv=rng.randbytes(8);light=[rng.randrange(256) for _ in range(8)]
    keys8=[]
    for i in range(8):
     cb,cr=uv[i&~1]-128,uv[(i&~1)+1]-128
     rgb=[clip(ys[i]+rq(91881*cr,16)),clip(ys[i]-rq(22554*cb+46802*cr,16)),clip(ys[i]+rq(116130*cb,16))]
     keys8.append(rgb[0]|rgb[1]<<8|rgb[2]<<16)
    grain=[0,921,1024][it%3];hashes=[rng.getrandbits(32) for _ in range(8)];noise=[rng.randrange(-170,170) for _ in range(8)];p=Params((C.c_uint8*8)(*light),grain,(C.c_uint32*8)(*hashes),(C.c_int32*8)(*noise))
    # Reset because LUT/capture selection changed; poison all slots with valid
    # but incorrect full keys to exercise hash collisions instead of false hits.
    for j in range(0,16384,2):cache[j]=0x01abcdef;cache[j+1]=0x0000ff
    u.mem_write(0x55010000,bytes(cache));expected=oracle(y,uv,lut,light,grain,hashes,noise)
    for repeat in range(2):
     want_hits=0
     for half in range(2):
      keys=keys8[half*4:half*4+4]
      want_hits+=sum(cache[((key*0x9e3779b9)&0xffffffff)>>19<<1]==key|0x01000000 for key in keys)
      # Expected values are written by fn; simulate only keys on a separate copy below.
      for key in keys:cache[((key*0x9e3779b9)&0xffffffff)>>19<<1]=key|0x01000000
     # Restore actual cache key/value pairs from ARM state before running host.
     C.memmove(cache,bytes(u.mem_read(0x55010000,65536)),65536)
     yy=C.create_string_buffer(y+b'GUARD');uu=C.create_string_buffer(uv+b'GUARD');ll=C.create_string_buffer(lut)
     self.assertEqual(fn(yy,uu,ll,C.byref(p),cache),want_hits);self.assertEqual((yy.raw[:8],uu.raw[:8]),expected)
     for addr,data in [(0x55000100,y+b'GUARD'),(0x55000200,uv+b'GUARD'),(0x55001000,lut),(0x55004000,bytes(p))]:u.mem_write(addr,data)
     for i,v in enumerate([0x55000100,0x55000200,0x55001000,0x55004000]):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
     saved=[rng.getrandbits(64) for _ in range(8)]
     for i,v in enumerate(saved):u.reg_write(getattr(A,f'UC_ARM_REG_D{i+8}'),v)
     u.mem_write(0x5500e000,struct.pack('<I',0x55010000));u.reg_write(A.UC_ARM_REG_SP,0x5500e000);u.reg_write(A.UC_ARM_REG_LR,0x5500f000);u.emu_start(report['symbols']['m10v_texture_block8_cached'],0x5500f000,count=30000)
     self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),want_hits);self.assertEqual(tuple(bytes(u.mem_read(a,8)) for a in (0x55000100,0x55000200)),expected);self.assertEqual(bytes(u.mem_read(0x55010000,65536)),bytes(cache))

     self.assertEqual([u.reg_read(getattr(A,f'UC_ARM_REG_D{i+8}')) for i in range(8)],saved)
     self.assertEqual(tuple(bytes(u.mem_read(a+8,5)) for a in (0x55000100,0x55000200)),(b'GUARD',b'GUARD'))
