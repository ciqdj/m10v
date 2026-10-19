"""Cortex-A9 NEON grain-size differential tests against the scalar creative model."""
import ctypes as C,random,struct,subprocess,tempfile,unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn import arm_const as A
ROOT=Path(__file__).resolve().parents[1]
class NoiseNeonTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();tmp=Path(cls.temp.name);src=str(ROOT/'native/gr3/m10v_isp_native_effects.c');so=tmp/'reference.dylib'
  subprocess.run(['clang','-shared','-O2','-DM10V_NATIVE_NOISE_ONLY',src,'-o',str(so)],check=True,capture_output=True)
  cls.library=C.CDLL(str(so));cls.reference=cls.library.m10v_isp_native_effects_noise_shape;cls.reference.argtypes=[C.c_void_p]+[C.c_uint32]*5
  obj=tmp/'neon.o';elf=tmp/'neon.elf'
  subprocess.run(['clang','--target=armv7-none-eabi','-mcpu=cortex-a9','-marm','-mfpu=neon','-mfloat-abi=softfp','-O2','-ffreestanding','-fno-builtin','-Wall','-Wextra','-Werror','-DM10V_NATIVE_NOISE_ONLY','-DM10V_NOISE_NEON','-c',src,'-o',str(obj)],check=True,capture_output=True)
  subprocess.run(['ld.lld','--entry=m10v_isp_native_effects_noise_shape','-Ttext=0x54160000',str(obj),'-o',str(elf)],check=True,capture_output=True)
  data=elf.read_bytes();cls.entry=struct.unpack_from('<I',data,24)[0];u=cls.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A9)
  ph=struct.unpack_from('<I',data,28)[0];psz,pnum=struct.unpack_from('<HH',data,42);mapped=set()
  for i in range(pnum):
   kind,off,va,_,sz,mem,_,_=struct.unpack_from('<8I',data,ph+i*psz)
   if kind!=1 or not mem:continue
   for page in range(va&~4095,(va+mem+4095)&~4095,4096):
    if page not in mapped:u.mem_map(page,4096);mapped.add(page)
   u.mem_write(va,data[off:off+sz])
  u.mem_map(0x55000000,0x2000000);u.mem_map(0x58000000,0x10000)
  u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def run_case(self,w,h,stride,size,initial):
  buf=(C.c_uint8*len(initial)).from_buffer_copy(initial);expected_result=self.reference(buf,len(initial),w,h,stride,size)
  u=self.u;plane=0x55001000;sp=0x5800f000;stop=0x5800ff00;u.mem_write(plane,initial)
  for n,v in enumerate((plane,len(initial),w,h)):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(n)),v)
  u.mem_write(sp,struct.pack('<II',stride,size));u.reg_write(A.UC_ARM_REG_SP,sp);u.reg_write(A.UC_ARM_REG_LR,stop)
  guards={getattr(A,'UC_ARM_REG_R'+str(n)):0x65430000+n for n in range(4,12)}
  guards.update({getattr(A,'UC_ARM_REG_D'+str(n)):0xaabbccdd00000000+n for n in range(8,16)})
  for reg,v in guards.items():u.reg_write(reg,v)
  u.emu_start(self.entry,stop,count=1000000000)
  self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),stop);self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),expected_result&0xffffffff)
  self.assertEqual(bytes(u.mem_read(plane,len(initial))),bytes(buf))
  self.assertEqual(u.reg_read(A.UC_ARM_REG_SP),sp)
  for reg,v in guards.items():self.assertEqual(u.reg_read(reg),v,'AAPCS callee-saved register changed')
 def test_all_sizes_skinny_tails_padding_and_callee_saved_d8_d15(self):
  rng=random.Random(429)
  for w in (1,2,3,7,15,16,17,18,19,31,32,33,63,64,65,127,128,129,6000):
   for h in (1,2,3,7):
    stride=w+5;initial=rng.randbytes(stride*h)
    for size in (0,1,2):self.run_case(w,h,stride,size,initial)
 def test_full_24mp_all_sizes_against_scalar_creative_model(self):
  rng=random.Random(101);initial=rng.randbytes(6000*4000)
  for size in (0,1,2):self.run_case(6000,4000,6000,size,initial)
 def test_invalid_preflight_leaves_plane_untouched(self):
  for size in (0,1,2,3):self.run_case(10,2,9,size,bytes(range(18)))
if __name__=='__main__':unittest.main()
