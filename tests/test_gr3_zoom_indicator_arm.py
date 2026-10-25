"""Execute the installed live widget updater and synchronous native icon renderer.

M10V_ZOOM_RTOS=/abs/final-rtos.bin M10V_ZOOM_MANIFEST=/abs/manifest.json
Native model/heap/framebuffer services are isolated; UI selection, visibility,
compact glyph decoder, descriptor lookup and stock RGBA blitter execute as ARM.
"""
import json,os,struct,unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
from unicorn import arm_const as A
BASE=0x53000000;RAM=0x55000000;STOP=RAM+0xf0000
bits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
class ZoomIndicatorArmTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not os.environ.get('M10V_ZOOM_RTOS') or not os.environ.get('M10V_ZOOM_MANIFEST'):
   raise unittest.SkipTest('Set M10V_ZOOM_RTOS and M10V_ZOOM_MANIFEST to a built final RTOS and manifest')
  cls.rom=Path(os.environ['M10V_ZOOM_RTOS']).read_bytes();cls.m=json.loads(Path(os.environ['M10V_ZOOM_MANIFEST']).read_text())
  for p in cls.m['zoom']['patches']:assert struct.unpack_from('<I',cls.rom,p['address']-BASE)[0]==p['replacement']
  def symbols(node):
   if isinstance(node,dict):
    if 'm10v_zoom_live_indicator_icon' in node:return node
    for value in node.values():
     found=symbols(value)
     if found:return found
   elif isinstance(node,list):
    for value in node:
     found=symbols(value)
     if found:return found
   return None
  cls.core=symbols(cls.m)
  if not cls.core:return # production legacy manifest retains its separate legacy contract
  assert all('m10v_zoom_'+n in cls.core for n in ('backend_init','backend_publish','live_indicator_icon')), 'installed owned indicator/backend symbols required'
  from scripts.build_gr3_menu_patches import branch
  assert struct.unpack_from('<I',cls.rom,0x53171968-BASE)[0]==branch(0x53171968,cls.core['m10v_zoom_live_indicator_icon'],link=True), 'native live widget must invoke owned indicator adapter'

 def machine(self,oom=False):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);extent=(len(self.rom)+4095)&~4095
  u.mem_map(BASE,extent);u.mem_write(BASE,self.rom);u.mem_protect(BASE,extent,UC_PROT_READ|UC_PROT_EXEC);u.mem_map(RAM,0x100000)
  u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000);u.reg_write(A.UC_ARM_REG_SP,RAM+0xd0000);u.reg_write(A.UC_ARM_REG_LR,STOP)
  self.allocs=[];self.frees=[];self.asserts=[];self.blit=[]
  def service(m,a,size,user):
   if a==0x5320a020:self.blit.append(a);return
   if a not in (0x5320ad88,0x5320b67c,0x5320b91c,0x532b2970,0x53153074,0x533ad308,0x533ad2c8,0x536af2a8,0x536af2e4,0x536c7520,0x536b93d0,0x53525d5c,0x536ae71c,0x536ae870):return
   val=0
   if a==0x53525d5c:val=RAM+0x6000
   elif a in (0x536ae71c,0x536ae870):val=1
   elif a==0x532b2970:m.reg_write(A.UC_ARM_REG_S0,bits(18.3))
   elif a==0x53153074:m.reg_write(A.UC_ARM_REG_S0,m.reg_read(A.UC_ARM_REG_S0)&0x7fffffff)
   elif a==0x536af2a8:
    self.allocs.append(m.reg_read(A.UC_ARM_REG_R0));val=0 if oom else RAM+0x60000
   elif a==0x536af2e4:self.frees.append(m.reg_read(A.UC_ARM_REG_R0))
   elif a==0x536c7520:val=RAM+0x70000
   elif a==0x536b93d0:self.asserts.append(m.reg_read(A.UC_ARM_REG_R0))
   m.reg_write(A.UC_ARM_REG_R0,val);m.reg_write(A.UC_ARM_REG_PC,m.reg_read(A.UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,service);return u
 def execute(self,u,entry,*args):
  for i,v in enumerate(args):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(i)),v)
  u.reg_write(A.UC_ARM_REG_LR,STOP);u.emu_start(entry,STOP,count=500000)
  self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),STOP)
  self.assertEqual(u.reg_read(A.UC_ARM_REG_SP),RAM+0xd0000)
 def test_legacy_manifest_retains_original_numeric_state_contract(self):
  if self.core:self.skipTest('owned pipeline uses native carrier plus private backend pair')
  for mm in range(28,51):
   u=self.machine();ctl,widget,state,vt=RAM+0x10000,RAM+0x20000,RAM+0x30000,RAM+0x40000
   for address,value in [(ctl+0x15c,widget),(ctl+0x4e8,state),(state+0xaf0,bits(mm/28)),(widget,vt),(vt+0x20,RAM+0x50000)]:u.mem_write(address,struct.pack('<I',value))
   u.mem_write(RAM+0x50000,struct.pack('<I',0xe12fff1e));self.execute(u,0x53171904,ctl,0,1)
   self.assertEqual(struct.unpack('<H',u.mem_read(widget+0xea,2))[0],{28:0,35:452,50:89}.get(mm,762+mm-28));self.assertEqual(u.mem_read(widget+0x9e,1)[0],int(mm!=28))
 def draw(self,mm,oom=False,angle=0):
  u=self.machine(oom);ctx,draw,surface=RAM+0x1000,RAM+0x2000,RAM+0x3000
  u.mem_write(ctx,struct.pack('<I',0x57000000));u.mem_write(surface+2,b'\x05');u.mem_write(surface+0x18,struct.pack('<H',60))
  u.mem_write(draw,struct.pack('<I',surface));u.mem_write(draw+4,struct.pack('<4I',0,0,60,20));u.mem_write(draw+0x14,struct.pack('<4I',0,0,60,20));u.mem_write(draw+0x24,struct.pack('<Hi',762+mm-28,0))
  u.mem_write(draw+0x28,struct.pack('<i',angle));u.mem_write(RAM+0x70000,b'\x33'*4800)
  saved={getattr(A,'UC_ARM_REG_R'+str(i)):0x10203040+i for i in range(4,12)}
  for reg,value in saved.items():u.reg_write(reg,value)
  self.execute(u,0x5320a7a8,ctx,draw)
  for reg,value in saved.items():self.assertEqual(u.reg_read(reg),value)
  self.assertFalse([c for c in self.asserts if not c]);self.assertEqual(self.allocs,[4800]);self.assertEqual(self.frees,[] if oom else [RAM+0x60000])
  pixels=bytes(u.mem_read(RAM+0x70000,4800))
  if oom:self.assertFalse(self.blit);self.assertEqual(pixels,b'\x33'*4800)
  else:self.assertIn(b'\xff\xff\xff\xff',pixels);self.assertNotEqual(pixels,b'\x33'*4800)
  return pixels
 def test_native_blitter_consumes_generated_pixels_and_releases_each_draw(self):
  signatures=set()
  for mm in range(29,51):
   if mm not in (35,50):signatures.add(self.draw(mm))
  self.assertEqual(len(signatures),20)
 def test_native_rotation_paths_release_the_same_owned_bitmap(self):
  for angle in (-180,-90,90,180):
   with self.subTest(angle=angle):self.draw(40,angle=angle)
 def test_allocation_failure_skips_drawing_and_native_assertions(self):self.draw(40,True)
if __name__=='__main__':unittest.main()
