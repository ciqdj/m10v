"""Execute linked ARM SD adapter with explicit filesystem substitutes."""
import hashlib,os,struct,subprocess,tempfile,unittest
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_EXEC
from unicorn.arm_const import *
from scripts.build_gr3_m10v_library import build
ROOT=Path(__file__).resolve().parents[1]
class SdCameraTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.manifest=build(Path(cls.tmp.name),sd_library=True)
  cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
  cls.pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack());"],cwd=ROOT)
 def setUp(self):
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u=self.u;u.mem_map(0x53000000,0x1200000);u.mem_map(0x55000000,0x100000)
  u.mem_write(self.manifest['base'],self.code);u.mem_protect(self.manifest['base'],(len(self.code)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
  self.position=0;self.card=self.pack;self.short=False;self.fail_save=False;self.fail_close=False;self.fail_allocate=False;self.fail_open=False;self.fail_stat=False;self.fail_state=False;self.bad_snapshot=False;self.raw_loads=0;self.calls=[];self.files={};self.opened=0;self.allocated=0
  self.w(0x55001014,0x55002000);self.w(0x55002000,0x53900000)
  for i in [7,8,9,11,12,13]:self.w(0x53900000+4*i,0x53900100+i*16)
  self.w(0x55003008,0x55004000);self.w(0x55004000,0x55005000);self.w(0x55005000,0x55006000);u.mem_write(0x55005020,b'\1')
  u.hook_add(UC_HOOK_CODE,self.hook)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def n(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,a):return bytes(self.u.mem_read(a,64)).split(b'\0')[0].decode()
 def hook(self,u,pc,size,data):
  a=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];extra=self.n(u.reg_read(UC_ARM_REG_SP));ret=None
  if pc==0x535847d8:ret=0x55001000
  elif pc==0x536af2a8:
   ret=0 if self.fail_allocate else 0x55020000
   if ret:self.allocated+=1
  elif pc==0x536af2e4:self.allocated-=1;ret=0
  elif pc==0x53900170:
   self.assertEqual(self.string(a[1]),'C:\\M10V\\FILMS.M10');self.assertEqual(a[2],1);self.opened+=1;self.position=0;self.w(a[3],0x55009000);self.w(extra,int(self.fail_open));ret=int(not self.fail_open)
  elif pc==0x53900180:self.opened-=1;self.w(a[2],int(self.fail_close));ret=int(not self.fail_close)
  elif pc==0x53900190:
   length=min(a[3],len(self.card)-self.position);length=max(0,length-1) if self.short else length
   u.mem_write(a[2],self.card[self.position:self.position+length]);self.position+=length;self.w(extra,0);ret=1
  elif pc==0x539001b0:self.assertEqual(a[3],0);self.position=a[2];self.w(extra,0);ret=1
  elif pc==0x539001c0:self.assertEqual(a[1],0x55009000);self.assertEqual(self.opened,1);self.w(a[2],len(self.card));self.w(a[3],int(self.fail_stat));ret=int(not self.fail_stat)
  elif pc==0x539001d0:self.w(a[2],self.position);self.w(a[3],0);ret=1
  elif pc==0x53828014:ret=0x55003000
  elif pc==0x53825fa8:
   name=self.string(a[1]);self.calls.append(('save',name,a[2]));ret=int(not self.fail_save and not (self.fail_state and name.startswith('M10V5')))
   if ret:self.files[name]=bytes(u.mem_read(a[3],a[2]))
  elif pc==0x53825648:
   name=self.string(a[1]);value=self.files.get(name);ret=int(value is not None)
   if value:u.mem_write(a[3],value[:a[2]])
  elif pc==0x5362e160:
   name=self.string(a[1]).split('\\')[-1];value=self.files.get(name);ret=len(value)+8 if value is not None else 0
  elif pc==0x5362e294:
   self.raw_loads+=1
   name=self.string(a[1]).split('\\')[-1];value=self.files.get(name);ret=0
   if value:
    raw=struct.pack('<II',0xa55a5aa5,0)+value
    if self.bad_snapshot:raw=raw[:-1]
    u.mem_write(0x55040000,raw);self.w(a[2],len(raw));ret=0x55040000
  elif pc==0x538253e8:self.w(a[3],a[1]-8);self.w(extra,a[2]+8);ret=1
  elif pc==0x5362d478:ret=1
  elif pc==0x5383c8a8:ret=0
  if ret is not None:u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def call(self,name,*args):
  u=self.u;sp=0x550fe000;u.reg_write(UC_ARM_REG_SP,sp)
  for r,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):u.reg_write(r,v)
  for i,value in enumerate(args[4:]):self.w(sp+4*i,value)
  u.reg_write(UC_ARM_REG_LR,0x550ff000);u.emu_start(self.manifest['symbols'][name],0x550ff000,count=10000000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x550ff000);return u.reg_read(UC_ARM_REG_R0)
 def test_pages_and_final_record(self):
  for page,row,expected in [(0,0,33),(1,0,41),(4,0,65),(4,1,66),(4,2,67),(4,3,68),(4,4,0),(32,0,0),(0,8,0)]:self.assertEqual(self.call('m10v_sd_camera_item',page,row),expected)
  self.assertEqual((self.opened,self.allocated),(0,0));self.assertEqual(self.calls,[])
 def test_install_persists_complete_recipe_before_slot_and_survives_no_card(self):
  self.assertEqual(self.call('m10v_sd_camera_install',4,0,65,2),0)
  self.assertEqual(self.calls[0],('save','M10VS65.bin',12288));self.assertEqual(self.files['M10VS65.bin'],self.pack[4096+32*12288:4096+33*12288])
  self.card=b'';self.assertEqual(self.call('m10v_camera_library_load',0x5500a000),0)
  state=bytes(self.u.mem_read(0x5500a000,104));self.assertEqual(struct.unpack_from('<H',state,28)[0],65)
  self.assertEqual((self.opened,self.allocated),(0,0))
 def test_new_films_keep_effects_and_timestamp_in_v5_journal(self):
  state=0x5500a000
  self.assertGreaterEqual(self.call('m10v_camera_library_load',state),0)
  for field,value in [(0,2),(1,8),(2,4),(3,7),(4,1)]:
   self.assertEqual(self.call('m10v_camera_library_effects',state,1,field,value),0)
  effects=bytes(self.u.mem_read(state+56,16))+bytes(self.u.mem_read(state+80,16))
  for film in (66,67,68):
   self.assertEqual(self.call('m10v_sd_camera_install',4,film-65,film,2),0)
   self.assertEqual(self.files[f'M10VS{film}.bin'],self.pack[4096+(film-33)*12288:4096+(film-32)*12288])
   self.assertEqual(self.call('m10v_camera_library_load',state),0)
   self.assertEqual(bytes(self.u.mem_read(state+56,16))+bytes(self.u.mem_read(state+80,16)),effects)
  self.assertEqual(self.call('m10v_camera_library_effects',state,2,1,8),0)
  effects=bytes(self.u.mem_read(state+56,40))
  self.assertEqual(self.call('m10v_sd_camera_install',4,3,68,2),0)
  self.assertEqual(self.call('m10v_camera_library_load',state),0)
  self.assertEqual(bytes(self.u.mem_read(state+56,40)),effects)
  self.assertEqual(self.call('m10v_camera_library_stamp',state,2,3,2,1),0)
  self.card=b''
  self.assertEqual(self.call('m10v_camera_library_load',state),0)
  self.assertEqual(bytes(self.u.mem_read(state+56,40)),effects)
  self.assertEqual(bytes(self.u.mem_read(state+52,4)),bytes([2,3,2,1]))
  self.assertEqual(struct.unpack('<HH',self.u.mem_read(state+4,4)),(4,104))
  self.assertEqual(struct.unpack('<H',self.u.mem_read(state+28,2))[0],68)

 def test_short_read_bad_record_wrong_identity_and_failed_save_never_commit(self):
  self.short=True;self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,0),0);self.assertEqual(self.calls,[])
  self.short=False;self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,34,0),0);self.assertEqual(self.calls,[])
  self.card=bytearray(self.pack);self.card[4096+64]^=1;self.card=bytes(self.card)
  self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,0),0);self.assertEqual(self.calls,[])
  self.card=self.pack;self.fail_save=True;self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,0),0)
  self.assertEqual(self.files,{});self.assertEqual((self.opened,self.allocated),(0,0))
 def test_close_failure_and_invalid_slot_never_save(self):
  self.fail_close=True;self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,0),0)
  self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,5),0);self.assertEqual(self.calls,[]);self.assertEqual((self.opened,self.allocated),(0,0))

 def test_allocation_open_stat_and_truncated_snapshot_fail_without_slot_write(self):
  for flag in ['fail_allocate','fail_open','fail_stat','bad_snapshot']:
   with self.subTest(flag=flag):
    setattr(self,flag,True)
    self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,0),0)
    self.assertFalse(any(name.startswith('M10V5') for _,name,_ in self.calls))
    self.assertEqual((self.opened,self.allocated),(0,0))
    setattr(self,flag,False)
 def test_state_write_failure_preserves_previous_slots_and_reuses_verified_snapshot(self):
  self.assertEqual(self.call('m10v_sd_camera_install',0,1,34,1),0)
  self.assertEqual(self.call('m10v_camera_library_load',0x5500a000),0)
  before=bytes(self.u.mem_read(0x5500a000,104))
  self.fail_state=True
  self.assertNotEqual(self.call('m10v_sd_camera_install',4,0,65,4),0)
  self.assertEqual(self.call('m10v_camera_library_load',0x5500a000),0)
  self.assertEqual(bytes(self.u.mem_read(0x5500a000,104)),before)
  self.assertIn('M10VS65.bin',self.files)
  self.fail_state=False;self.calls=[]
  self.assertEqual(self.call('m10v_sd_camera_install',4,0,65,4),0)
  self.assertFalse(any(name=='M10VS65.bin' for _,name,_ in self.calls))
  self.assertEqual(self.call('m10v_camera_library_load',0x5500a000),0)
  after=bytes(self.u.mem_read(0x5500a000,104))
  self.assertEqual(after[12:44],before[12:44])
  self.assertEqual(struct.unpack_from('<H',after,44)[0],65)
  self.assertEqual(after[46:100],before[46:100])
  self.assertEqual((self.opened,self.allocated),(0,0))

 def test_oversized_snapshot_is_not_loaded_before_replacement(self):
  self.files['M10VS33.bin']=b'X'*20000;self.fail_save=True
  self.assertNotEqual(self.call('m10v_sd_camera_install',0,0,33,0),0)
  self.assertEqual(self.raw_loads,0)
  self.assertEqual((self.opened,self.allocated),(0,0))

 def test_sd_replacement_changes_actual_saved_jpeg_pixels_without_sd_during_capture(self):
  u=self.u;recipe=0x55070000;shooting=0x55078000;request=0x55076000;context=recipe+0x9b8
  for offset,value in [(0x18,0),(0x5c,request),(0x60,0xa3000000),(0x230,0x55075000),(0x44c8,shooting)]:self.w(recipe+offset,value)
  u.mem_write(0x55075000,struct.pack('<HH',6112,4064));self.w(request,0x53d0fe60)
  u.mem_write(request+12,b'\1\1');u.mem_write(shooting+0x77c,bytes([18]));u.mem_write(recipe+0x140,b'\1')
  self.w(context,0x53d0fbe0)
  for offset,value in [(0x30,recipe+0x1a8),(0x34,shooting),(0x38,request),(0x3c,recipe+0xb0),(0x48,recipe+0x110),(0x4c,recipe+0x130)]:self.w(context+offset,value)
  for offset,y,c in [(0xb0,0x55060000,0x55062000),(0x110,0x55090000,0x550a0000)]:
   u.mem_write(recipe+offset,struct.pack('<4I8H',1,y,c,0,64,32,64,32,0,0,2,0))
  outputs=[]
  for page,row,film in [(0,1,34),(4,0,65)]:
   self.card=self.pack;self.assertEqual(self.call('m10v_sd_camera_install',page,row,film,1),0)
   self.card=b'';u.mem_write(0x55060000,bytes([64])*2048);u.mem_write(0x55062000,bytes([128])*2048)
   self.assertEqual(self.call('m10v_capture_library',context),0)
   outputs.append(bytes(u.mem_read(0x55060000,2048))+bytes(u.mem_read(0x55062000,2048)))
  self.assertNotEqual(outputs[0],outputs[1]);self.assertEqual((self.opened,self.allocated),(0,0))

 def test_original_size_wrapper_receives_open_handle_not_path(self):
  # Execute both original size and metadata dispatch. Only the metadata
  # constructor, mutex and device leaf are substitutes; actual SD is untested.
  path=Path(os.environ.get('M10V_GR3_ORIGINAL_RTOS','/tmp/m10v-sd-research/rtos.bin'))
  if not path.exists():self.skipTest('set M10V_GR3_ORIGINAL_RTOS')
  code=path.read_bytes()
  self.assertEqual(hashlib.sha256(code).hexdigest(),'8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67')
  u=self.u
  for start,end in [(0x5359312c,0x5359320c),(0x535948c4,0x53594974)]:
   u.mem_write(start,code[start-0x53000000:end-0x53000000])
  self.w(0x53900000+12*4,0x535948c4);self.w(0x53900000+21*4,0x5359312c)
  self.w(0x55002018,0x5500b000);self.w(0x5500b000,0x5500b100)
  self.w(0x5500b100,0x53900500);self.w(0x53900500+0x48,0x53900400)
  self.w(0x55009000,7);self.w(0x55009004,0)
  def original_leaves(uc,pc,size,data):
   a=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]]
   ret=None
   if pc==0x53594990:uc.mem_write(a[0],bytes(64));ret=a[0]
   elif pc==0x53592738:ret=0x55007000
   elif pc in [0x536ae71c,0x536ae870]:ret=1
   elif pc==0x53900400:
    self.assertEqual(a[1],7);self.assertEqual(self.opened,1)
    self.w(a[2]+24,len(self.card));self.w(a[3],int(self.fail_stat));ret=int(not self.fail_stat)
   if ret is not None:uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,original_leaves)
  self.assertEqual(self.call('m10v_sd_camera_item',0,0),33)
  self.fail_stat=True
  self.assertEqual(self.call('m10v_sd_camera_item',0,0),0)
  self.assertEqual((self.opened,self.allocated),(0,0))
  self.fail_stat=False;self.card=b''
  self.assertEqual(self.call('m10v_sd_camera_item',0,0),0)
  self.assertEqual((self.opened,self.allocated),(0,0))
