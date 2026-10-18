"""Execute linked GR IV capture code with explicit camera-service boundaries.
CPU pixel parity and untouched protected regions are not on-device evidence.
"""
import ctypes as C
import struct,tempfile,unittest,zlib
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
from scripts.build_gr4_m10v_library import build
from tests import test_gr3_m10v_library as host
ROOT=Path(__file__).resolve().parents[1]

class Gr4NativeCaptureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  cls.manifest=build(Path(cls.tmp.name),0x54400000,rtos=(ROOT/'data/research/gr4/RTOS.bin').read_bytes())
  cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
  host.NativeFilmLibraryTests.setUpClass();cls.addClassCleanup(host.NativeFilmLibraryTests.doClassCleanups)
 def fixture(self,film=33,stamp=0,grain=1,soft=2,width=32,height=24,stride=None,tone=37,allocation=True,scratch=None,mode=0,effects=None,date=(2026,10,18,6,7,8),ui_date=None,raw=1,raw_bank=0xa3000000):
  stride=stride or width+8;allocated=min(height+2,4176);capacity=stride*allocated
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x2000000);u.mem_map(0x55000000,0x200000);u.mem_map(raw_bank,4096)
  u.mem_write(self.manifest['base'],self.code)
  state=host.State();host.NativeFilmLibraryTests.lib.m10v_library_init(C.byref(state));state.sequence=7
  for slot in state.slots:slot.film=film;slot.grain=grain;slot.soft=soft;slot.halo_gain=3 if film in (33,67) else 0;slot.halo_spread=3;slot.halo_threshold=5;slot.halo_profile=2
  if effects:
   for i,v in enumerate(effects):state.effects[1][i]=v
  state.stamp=stamp;state.format=2;state.corner=3;state.color=1;state.crc=zlib.crc32(bytes(state)[:-4])
  recipe=0x55070000;req=0x55076000;shot=0x55078000;context=recipe+0xb60
  ybase=0x55010000;cbase=0x55030000;scratchbase=scratch or 0x55100000
  def w(a,v):u.mem_write(a,struct.pack('<I',v))
  for off,val in [(0x18,mode),(0x5c,req),(0x60,raw_bank),(0x230,0x55075000),(0x4688,shot)]:w(recipe+off,val)
  u.mem_write(0x55075000,struct.pack('<HH',16,16));raw_bytes=bytes((i*23+9)&255 for i in range(512));u.mem_write(raw_bank,raw_bytes)
  ctx=bytearray(0x60);struct.pack_into('<I',ctx,0,0x53f84fa0)
  for off,val in [(0x30,recipe+0x1a8),(0x34,shot),(0x38,req),(0x3c,recipe+0xb0),(0x48,recipe+0x110),(0x4c,recipe+0x130)]:struct.pack_into('<I',ctx,off,val)
  u.mem_write(context,bytes(ctx));w(req,0x53f85258);u.mem_write(req+12,bytes([1,raw]));u.mem_write(shot+0x79c,bytes([tone]));u.mem_write(recipe+0x140,b'\1')
  if date:
   year,month,day,hour,minute,second=date;u.mem_write(shot+0x96c,struct.pack('<H6B',year,month,day,4,hour,minute,second))
  for at,y,c in [(recipe+0xb0,ybase,cbase),(recipe+0x110,0x55090000,0x550b0000)]:u.mem_write(at,struct.pack('<4I8H',1,y,c,0,width,height,stride,allocated,0,0,2,0))
  y=bytearray([173]*capacity+[211]*32);uv=bytearray([197]*capacity+[219]*32)
  for row in range(height):
   for x in range(width):y[row*stride+x]=(row*11+x*3+40)&255;uv[row*stride+x]=100+((row+x)%50)
  u.mem_write(ybase,bytes(y));u.mem_write(cbase,bytes(uv));u.mem_write(0x55090000,bytes([123])*capacity);u.mem_write(0x550b0000,bytes([127])*capacity)
  calls=[]
  def external(uc,pc,size,data):
   a=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];ret=0
   if pc==self.manifest['symbols']['m10v_camera_library_load']:uc.mem_write(a[0],bytes(state))
   elif pc==0x538e09b0:calls.append(('allocate',a[0]));ret=scratchbase if allocation else 0
   elif pc==0x538e09ec:calls.append(('free',a[0]))
   elif pc==0x538f0448:ret=0x55006000
   elif pc in [0x538f04d8,0x538f04c4]:calls.append(('clean' if pc==0x538f04c4 else 'invalidate',a[1],a[2]))
   elif pc==0x538f21a0:
    calls.append(('clock',));ret=0x55006100 if ui_date else 0
    if ui_date:w(0x55006104,0x55006200)
   elif pc==0x538ea9b0:uc.mem_write(a[1],struct.pack('<H6B',*ui_date,0))
   uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  for addr in [self.manifest['symbols']['m10v_camera_library_load'],0x538e09b0,0x538e09ec,0x538f0448,0x538f04d8,0x538f04c4,0x538f21a0,0x538ea9b0]:u.hook_add(UC_HOOK_CODE,external,begin=addr,end=addr)
  def protect(uc,access,address,size,value,data):raise AssertionError(f'capture accessed CFA {address:#x}')
  u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,protect,begin=raw_bank,end=raw_bank+511)
  return dict(u=u,state=state,context=context,recipe=recipe,req=req,shot=shot,y=y,uv=uv,ybase=ybase,cbase=cbase,width=width,height=height,stride=stride,capacity=capacity,calls=calls,date=date,raw=raw_bytes,raw_bank=raw_bank)
 def run_capture(self,f):
  u=f['u'];sp=0x551ff000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_R0,f['context']);u.reg_write(UC_ARM_REG_LR,0x551fff00)
  u.emu_start(self.manifest['symbols']['m10v_capture_library'],0x551fff00,count=100000000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x551fff00);self.assertEqual(u.reg_read(UC_ARM_REG_SP),sp)
  return C.c_int32(u.reg_read(UC_ARM_REG_R0)).value
 def assert_unchanged(self,f):
  self.assertEqual(bytes(f['u'].mem_read(f['ybase'],len(f['y']))),bytes(f['y']));self.assertEqual(bytes(f['u'].mem_read(f['cbase'],len(f['uv']))),bytes(f['uv']))
 def assert_host_parity(self,f,stamp=None,date=None):
  state=host.State.from_buffer_copy(bytes(f['state']))
  if stamp is not None:state.stamp=stamp;state.crc=zlib.crc32(bytes(state)[:-4])
  d=date or f['date'];dateptr=C.byref(host.Date(*d[:5])) if d else None
  seed=state.sequence^f['ybase']
  if d and (state.stamp or state.slots[1].grain or state.effects[1][4]):seed^=(d[0]<<16)^(d[1]<<8)^d[2]^(d[3]<<24)^(d[4]<<16)^(d[5]<<8)
  if state.slots[1].film==66 or state.effects[1][4]:
   for yy in range(0,f['height'],f['height']//16+1):
    for xx in range(0,f['width'],f['width']//16+1):seed=((seed^f['y'][yy*f['stride']+xx])*16777619)&0xffffffff
  y=(C.c_uint8*len(f['y'])).from_buffer_copy(f['y']);uv=(C.c_uint8*len(f['uv'])).from_buffer_copy(f['uv']);image=host.Image(y,uv,f['capacity'],f['capacity'],f['width'],f['height'],f['stride']);scratch=(C.c_uint8*(6*f['width']*f['height']))()
  self.assertEqual(host.NativeFilmLibraryTests.lib.m10v_library_render(C.byref(image),C.byref(state),1,dateptr,seed,scratch,len(scratch)),0)
  self.assertEqual(bytes(f['u'].mem_read(f['ybase'],len(y))),bytes(y));self.assertEqual(bytes(f['u'].mem_read(f['cbase'],len(uv))),bytes(uv))
 def test_jpeg_and_raw_jpeg_match_shared_host_renderer_and_preserve_padding(self):
  for raw in [0,1]:
   with self.subTest(raw=raw):
    f=self.fixture(raw=raw,stamp=2,width=128,height=96);self.assertEqual(self.run_capture(f),0);self.assert_host_parity(f)
    self.assertEqual(len([x for x in f['calls'] if x[0]=='invalidate']),2);self.assertEqual(len([x for x in f['calls'] if x[0]=='clean']),2)
    self.assertEqual(len([x for x in f['calls'] if x[0]=='free']),1)
    self.assertEqual(bytes(f['u'].mem_read(f['raw_bank'],512)),f['raw'])
    for base,original in [(f['ybase'],f['y']),(f['cbase'],f['uv'])]:
     actual=bytes(f['u'].mem_read(base,len(original)))
     for row in range(f['height']):self.assertEqual(actual[row*f['stride']+f['width']:(row+1)*f['stride']],original[row*f['stride']+f['width']:(row+1)*f['stride']])
     self.assertEqual(actual[f['height']*f['stride']:],original[f['height']*f['stride']:])
 def test_shared_film_and_leak_semantics_match_for_representative_catalog_familms(self):
  for film in [2,35,40,66,67,68]:
   with self.subTest(film=film):
    f=self.fixture(film=film,effects=[2,8,5,8,1,2 if film==68 else 0]);self.assertEqual(self.run_capture(f),0);self.assert_host_parity(f)
 def test_all_proven_still_sequence_modes_are_accepted(self):
  for mode in [0,1,5,6,7,8,12,13,16]:
   with self.subTest(mode=mode):
    f=self.fixture(mode=mode,width=8,height=4,soft=0,grain=0,film=2);self.assertEqual(self.run_capture(f),0)
 def test_unavailable_date_skips_only_stamp_and_preserves_saved_state(self):
  f=self.fixture(date=None,stamp=2,width=128,height=96);before=bytes(f['state']);self.assertEqual(self.run_capture(f),0);self.assert_host_parity(f,stamp=0);self.assertEqual(bytes(f['state']),before)
 def test_capture_date_wins_and_ui_fallback_uses_proven_service(self):
  f=self.fixture(stamp=2,width=128,height=96,ui_date=(2024,2,29,1,2,3));self.assertEqual(self.run_capture(f),0);self.assertNotIn(('clock',),f['calls']);self.assert_host_parity(f)
  f=self.fixture(stamp=2,width=128,height=96,date=None,ui_date=(2024,2,29,1,2,3));self.assertEqual(self.run_capture(f),0);self.assertIn(('clock',),f['calls']);self.assert_host_parity(f,date=(2024,2,29,1,2,3))
 def test_noncarrier_invalid_request_and_unsafe_sequence_leave_pixels_unchanged(self):
  for options,change in [({'tone':35},None),({'mode':2},None),({},'request'),({},'jpeg')]:
   with self.subTest(options=options,change=change):
    f=self.fixture(**options)
    if change=='request':f['u'].mem_write(f['req'],bytes(4))
    if change=='jpeg':f['u'].mem_write(f['req']+12,b'\0')
    self.assertLess(self.run_capture(f),0);self.assert_unchanged(f);self.assertFalse(f['calls'])
 def test_plane_raw_and_preview_aliases_are_rejected(self):
  for alias in ['chroma','raw','preview']:
   with self.subTest(alias=alias):
    f=self.fixture();where=f['recipe']+(0x60 if alias=='raw' else 0xb8 if alias=='chroma' else 0x114)
    f['u'].mem_write(where,struct.pack('<I',f['ybase']))
    self.assertEqual(self.run_capture(f),-3);self.assert_unchanged(f)
 def test_allocator_failure_and_scratch_alias_leave_pixels_unchanged(self):
  for options in [{'allocation':False},{'scratch':0x55010000},{'scratch':0xa3000000}]:
   with self.subTest(options=options):
    f=self.fixture(**options);self.assertEqual(self.run_capture(f),-6);self.assert_unchanged(f)
 def test_maximum_gr4_dimensions_are_accepted_and_excess_rejected(self):
  for width,height in [(6256,2),(2,4176)]:
   with self.subTest(width=width,height=height):
    f=self.fixture(width=width,height=height,grain=0,soft=0,film=2);self.assertEqual(self.run_capture(f),0)
  for width,height in [(6258,2),(2,4177)]:
   f=self.fixture(width=width,height=height,grain=0,soft=0,film=2);self.assertEqual(self.run_capture(f),-3);self.assert_unchanged(f)
 def test_observed_high_ram_bank_is_accepted(self):
  f=self.fixture(soft=0,grain=0,film=2);high=0xb1069cc0;f['u'].mem_map(high&~4095,0x4000);f['u'].mem_write(high,bytes(f['y']));f['u'].mem_write(f['recipe']+0xb4,struct.pack('<I',high));f['ybase']=high
  self.assertEqual(self.run_capture(f),0);self.assert_host_parity(f)
