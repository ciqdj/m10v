"""Residual no-LUT effects must match the frozen original scalar renderer."""
import ctypes as C
import json,random,struct,shutil,subprocess,tempfile,unittest
from pathlib import Path
from tests.test_gr3_m10v_library import Image,ROOT
class NativeResidualTextureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup);cls.libs=[]
  for baseline in (True,False):
   output=Path(cls.temp.name)/('baseline.dylib' if baseline else 'native.dylib')
   sources=[str(ROOT/('tests/fixtures/gr3_texture_reference.c' if baseline else 'native/gr3/film_5207.c')),str(ROOT/'native/gr3/film_harman.c'),str(ROOT/'native/gr3/film_curated.c'),str(ROOT/'native/gr3/film_newstocks.c'),str(ROOT/'native/gr3/film_style_filters_0.c'),str(ROOT/'native/gr3/film_style_filters_1.c')]
   if not baseline:sources.extend(str(ROOT/'native/gr3'/n) for n in ('m10v_spatial_accel.c','m10v_texture_accel.c'))
   subprocess.run([shutil.which('clang'),'-O2','-dynamiclib','-DM10V_SPATIAL_NEON='+str(int(not baseline)),'-DM10V_TEXTURE_NEON='+str(int(not baseline)),'-I',str(ROOT/'native/gr3'),*sources,'-o',str(output)],check=True,capture_output=True)
   lib=C.CDLL(str(output));lib.m10v_5207_texture_q8.argtypes=[C.POINTER(Image),C.c_void_p,C.c_uint32,C.c_uint32,C.c_uint32];cls.libs.append(lib)
 @classmethod
 def arm_module(cls,baseline,base):
  from scripts.build_gr3_texture_accel import FLAGS
  from scripts.build_gr3_save_trace import sections
  frozen=baseline is True;vector=baseline is False
  folder=Path(cls.temp.name)/('arm-baseline' if frozen else 'arm-native' if vector else 'arm-current-scalar');folder.mkdir(exist_ok=True);objects=[]
  sources=[ROOT/('tests/fixtures/gr3_texture_reference.c' if frozen else 'native/gr3/film_5207.c'),ROOT/'native/gr3/film_harman.c',ROOT/'native/gr3/film_curated.c',ROOT/'native/gr3/film_newstocks.c',ROOT/'native/gr3/film_style_filters_0.c',ROOT/'native/gr3/film_style_filters_1.c']
  if not frozen:sources.extend(ROOT/'native/gr3'/n for n in ('m10v_spatial_accel.c','m10v_texture_accel.c'))
  for i,source in enumerate(sources):
   obj=folder/(str(i)+'.o');subprocess.run(['clang',*FLAGS,'-ffunction-sections','-fdata-sections','-DM10V_SPATIAL_NEON='+str(int(not frozen)),'-DM10V_TEXTURE_NEON='+str(int(vector)),'-I',str(ROOT/'native/gr3'),'-c',str(source),'-o',str(obj)],check=True,capture_output=True);objects.append(str(obj))
  script=folder/'link.ld';script.write_text('SECTIONS { . = '+hex(base)+'; .text : { *(.text*) } .rodata : { *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) } }');elf=folder/'module.elf'
  subprocess.run(['ld.lld','--gc-sections','-u','m10v_5207_texture_q8','-T',str(script),*objects,'-o',str(elf)],check=True,capture_output=True)
  data=elf.read_bytes();rows=sections(data);image=bytearray();symbols={}
  for name,row in rows:
   if row[2]&2 and row[5]:
    offset=row[3]-base;image.extend(bytes(max(0,offset+row[5]-len(image))));image[offset:offset+row[5]]=data[row[4]:row[4]+row[5]]
   if row[1]==2:
    sr=rows[row[6]][1];strings=data[sr[4]:sr[4]+sr[5]]
    for pos in range(row[4],row[4]+row[5],16):
     n,v,_,info,_,_=struct.unpack_from('<IIIBBH',data,pos);symbol=strings[n:].split(b'\0',1)[0].decode()
     if symbol.startswith('m10v_') and info&15==2:symbols[symbol]=v
  return base,bytes(image),symbols
 def arm_emulator(self,module):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn import arm_const as A
  base,code,_=module;u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_CORTEX_A9);u.mem_map(base,(len(code)+65535)&~65535);u.mem_write(base,code);u.mem_map(0x55000000,0x1000000);u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000);return u
 def arm_run(self,u,module,width,height,size,grain,gain,seed,initial,count=False):
  from unicorn import arm_const as A
  from unicorn import UC_HOOK_CODE
  stride=width+8;n=stride*height;y=0x55010000;uv=0x55030000;im=0x55000100;e=0x55000200
  u.mem_write(y,initial[0]);u.mem_write(uv,initial[1]);u.mem_write(im,struct.pack('<7I',y,uv,n,n,width,height,stride));u.mem_write(e,bytes([size,gain,5,8,1,0,0,0]))
  for i,v in enumerate((im,e,grain,seed)):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(i)),v)
  u.reg_write(A.UC_ARM_REG_SP,0x55fff000);u.mem_write(0x55fff000,bytes(4));u.reg_write(A.UC_ARM_REG_LR,0x55ffff00)
  calls=[0]
  def instruction(u,at,size,data):calls[0]+=1
  hook=u.hook_add(UC_HOOK_CODE,instruction) if count else None
  if count:u.ctl_flush_tb()
  u.emu_start(module[2]['m10v_5207_texture_q8'],0x55ffff00,count=15000000)
  if hook:u.hook_del(hook);u.ctl_flush_tb()
  self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x55ffff00)
  return (bytes(u.mem_read(y,len(initial[0]))),bytes(u.mem_read(uv,len(initial[1])))),calls[0]
 def test_arm_images_match_frozen_scalar_and_instruction_work_reduces(self):
  baseline=self.arm_module(True,0x54200000);native=self.arm_module(False,0x54300000);modules=[baseline,native];ems=[self.arm_emulator(m) for m in modules];work=[]
  for width,height in ((2,1),(6,3),(8,3),(10,5),(18,7),(6000,2)):
   for size in range(3):
    for grain in (0,768,921):
     for gain in (0,6):
      for seed in (0,0xffffffff):
       rng=random.Random(width+grain+size+gain+seed);n=(width+8)*height;initial=(rng.randbytes(n+32),rng.randbytes(n+32));outputs=[];counts=[]
       measure=width==6000 and size==1 and grain==0 and gain==6 and seed==0
       for u,module in zip(ems,modules):
        result,instructions=self.arm_run(u,module,width,height,size,grain,gain,seed,initial,measure);outputs.append(result);counts.append(instructions)
       self.assertEqual(*outputs,(width,size,grain,gain,seed))
       if measure:work=counts
  self.assertEqual(len(work),2);self.assertLess(work[1],work[0]*.65)
  current_scalar=self.arm_module('current-scalar',0x54400000);u=self.arm_emulator(current_scalar)
  width=6000;height=2;size=1;grain=0;gain=6;seed=0;n=(width+8)*height;rng=random.Random(width+grain+size+gain+seed);initial=(rng.randbytes(n+32),rng.randbytes(n+32))
  scalar_output,scalar_work=self.arm_run(u,current_scalar,width,height,size,grain,gain,seed,initial,True)
  native_output,native_work=self.arm_run(ems[1],native,width,height,size,grain,gain,seed,initial,True)
  self.assertEqual(scalar_output,native_output);self.assertLess(native_work,scalar_work*.8)
  out=ROOT/'builds/gr3-native-residual-texture-v7';out.mkdir(parents=True,exist_ok=True);(out/'work-report.json').write_text(json.dumps({'width':6000,'height':2,'grain_q8':0,'leak_gain':6,'baseline_scalar_instructions':work[0],'native_instructions':work[1],'ratio':work[1]/work[0],'current_scalar_instructions':scalar_work,'current_scalar_ratio':native_work/scalar_work,'camera_timing_measured':False},indent=2)+'\n')
 def test_no_lut_api_exists_and_old_null_lut_rejects(self):
  lib=self.libs[1];fn=lib.m10v_texture_effects_block8;fn.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint32]
  y=C.create_string_buffer(bytes(range(8)));uv=C.create_string_buffer(bytes(range(8)));p=(C.c_uint32*19)()
  old=lib.m10v_texture_block8;old.argtypes=[C.c_void_p]*4
  self.assertEqual(old(y,uv,None,p),-1)
  before=(bytes(y),bytes(uv));self.assertEqual(fn(y,uv,p,0),0);self.assertEqual((bytes(y),bytes(uv)),before)
 def test_effects_block_host_arm_extremes_and_invalid_params(self):
  from scripts.build_gr3_texture_accel import build
  from tests.test_gr3_texture_accel import clip,rq,trunc
  from unicorn import arm_const as A
  class Params(C.Structure):_fields_=[('light',C.c_uint8*8),('grain',C.c_uint32),('hashes',C.c_uint32*8),('noise',C.c_int32*8)]
  report=build(Path(self.temp.name)/'effects-block');module=(report['base'],(Path(self.temp.name)/'effects-block/m10v-texture-arm.bin').read_bytes(),report['symbols']);u=self.arm_emulator(module)
  fn=self.libs[1].m10v_texture_effects_block8;fn.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint32];rng=random.Random(520706)
  for trial in range(128):
   y=bytes([255*(trial&1)]*8) if trial<16 else rng.randbytes(8);uv=bytes([255*((trial>>1)&1),255*((trial>>2)&1)]*4) if trial<16 else rng.randbytes(8)
   light=[255 if trial&8 else 0]*8 if trial<16 else [rng.randrange(256) for _ in range(8)];grain=(0,768,921,1024)[trial%4];hashes=[rng.getrandbits(32) for _ in range(8)];noise=[rng.choice((-170,169)) for _ in range(8)];chroma=trial&1;delta=[]
   for i in range(8):
    cb=uv[i&~1]-128;cr=uv[(i&~1)+1]-128;original=[clip(y[i]+rq(91881*cr,16)),clip(y[i]-rq(22554*cb+46802*cr,16)),clip(y[i]+rq(116130*cb,16))]
    rgb=[clip(v+(light[i]*t*(255-v)>>16)) for v,t in zip(original,(256,112,36))];lum=(54*rgb[0]+183*rgb[1]+19*rgb[2])>>8;weight=32+min(lum,255-lum);d=trunc(noise[i]*grain*weight,128*24*256)
    rgb=[clip(v+d+trunc(((hashes[i]>>(c*8)&255)-128)*grain,192*256)) for c,v in enumerate(rgb)];delta.append([v-o for v,o in zip(rgb,original)])
   ey=bytes(clip(y[i]+rq(19595*d[0]+38470*d[1]+7471*d[2],16)) for i,d in enumerate(delta));eu=bytearray(uv)
   if chroma:
    for i in range(0,8,2):
     r,g,b=[delta[i][c]+delta[i+1][c] for c in range(3)];eu[i]=clip(uv[i]+rq(-11059*r-21709*g+32768*b,17));eu[i+1]=clip(uv[i+1]+rq(32768*r-27439*g-5329*b,17))
   p=Params((C.c_uint8*8)(*light),grain,(C.c_uint32*8)(*hashes),(C.c_int32*8)(*noise));yy=C.create_string_buffer(y+b'GUARD');uu=C.create_string_buffer(uv+b'GUARD')
   self.assertEqual(fn(yy,uu,C.byref(p),chroma),0);self.assertEqual((yy.raw[:13],uu.raw[:13]),(ey+b'GUARD',bytes(eu)+b'GUARD'))
   for address,data in ((0x55000100,y+b'GUARD'),(0x55000200,uv+b'GUARD'),(0x55000400,bytes(p))):u.mem_write(address,data)
   for i,v in enumerate((0x55000100,0x55000200,0x55000400,chroma)):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(i)),v)
   saved=[rng.getrandbits(64) for _ in range(8)]
   for i,v in enumerate(saved):u.reg_write(getattr(A,'UC_ARM_REG_D'+str(i+8)),v)
   u.reg_write(A.UC_ARM_REG_SP,0x55fff000);u.reg_write(A.UC_ARM_REG_LR,0x55ffff00);u.emu_start(report['symbols']['m10v_texture_effects_block8'],0x55ffff00,count=30000)
   self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),0);self.assertEqual(tuple(bytes(u.mem_read(a,13)) for a in (0x55000100,0x55000200)),(ey+b'GUARD',bytes(eu)+b'GUARD'));self.assertEqual([u.reg_read(getattr(A,'UC_ARM_REG_D'+str(i+8))) for i in range(8)],saved)
  before=(bytes(yy),bytes(uu))
  for bad_grain,bad_noise,bad_chroma in ((1025,0,0),(0,170,0),(0,-171,0),(0,0,2)):
   p.grain=bad_grain;p.noise[0]=bad_noise;self.assertEqual(fn(yy,uu,C.byref(p),bad_chroma),-1);self.assertEqual((bytes(yy),bytes(uu)),before)
 def test_all_residual_effects_match_fixed_scalar_with_padding_and_tails(self):
  for width,height in ((2,1),(6,3),(8,3),(10,5),(18,7),(6000,2)):
   for size in range(3):
    for grain in (0,768,921):
     for gain in (0,6):
      for seed in (0,0xffffffff):
       with self.subTest(width=width,size=size,grain=grain,gain=gain,seed=seed):
        stride=width+8;n=stride*height;rng=random.Random(width+grain+size+gain+seed);initial=(rng.randbytes(n+32),rng.randbytes(n+32));outputs=[]
        for lib in self.libs:
         y=C.create_string_buffer(initial[0]);uv=C.create_string_buffer(initial[1]);im=Image(C.cast(y,C.POINTER(C.c_uint8)),C.cast(uv,C.POINTER(C.c_uint8)),n,n,width,height,stride);e=(C.c_uint8*8)(size,gain,5,8,1,0,0,0)
         lib.m10v_5207_texture_q8(C.byref(im),e,grain,seed,0);outputs.append((y.raw,uv.raw))
        self.assertEqual(*outputs)
        if not gain:self.assertEqual(outputs[1][1],initial[1]+b'\0')
