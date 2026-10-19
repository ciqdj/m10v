"""Execute delivered view with all firmware ROM RX, actual bitmap resource lookup and heap lifecycle."""
import hashlib,json,os,struct,subprocess,unittest
from pathlib import Path
from unicorn import UC_PROT_READ,UC_PROT_EXEC
from unicorn import arm_const as A
from tests.test_gr3_settings_view import SettingsViewTests
ROOT=Path(__file__).resolve().parents[1]
class MenuReadonlyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  os.environ['M10V_GR3_ORIGINAL_RTOS']=str(ROOT/'builds/gr3-extension-validation/official-rtos.bin')
  SettingsViewTests.setUpClass();cls.addClassCleanup(SettingsViewTests.doClassCleanups)
  cls.folder=Path(os.environ.get('M10V_MENU_CANDIDATE',str(ROOT/'builds/gr3-v8-menu-fix/candidate')))
  cls.manifest=json.loads((cls.folder/'evidence/M10V-runtime-manifest.json').read_text())
  js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';let b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
  cls.rom=subprocess.check_output(['node','--input-type=module','-e',js,str(cls.folder/'fwdc239b.bin')],cwd=ROOT)
 def fixture(self,fail=False):
  h=SettingsViewTests();u=h.machine(native_accessor=True,fail_cards=fail);u.mem_write(0x53000000,self.rom);u.mem_protect(0x53000000,0x2000000,UC_PROT_READ|UC_PROT_EXEC)
  h.heap=0x55800000;h.symbols=self.manifest['symbols'];owner=0x550a0000;p=owner+0x13bc;view=p+0x158
  u.mem_write(p,struct.pack('<I',self.manifest['settings_menu']['vtable']));u.mem_write(0x55063910,struct.pack('<I',1));u.mem_write(0x55063988,struct.pack('<I',owner))
  return h,u,view
 def call(self,u,address,*args):
  for i in range(4):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(i)),args[i]if i<len(args)else 0)
  u.reg_write(A.UC_ARM_REG_SP,0x100f0000);u.reg_write(A.UC_ARM_REG_LR,0x10000000);u.emu_start(address,0x10000000,count=10000000)
  self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),0x10000000);return u.reg_read(A.UC_ARM_REG_R0)
 def test_repeated_film_view_entry_and_exit_never_write_rom_or_leak(self):
  h,u,view=self.fixture();before=hashlib.sha256(bytes(u.mem_read(0x53000000,len(self.rom)))).digest()
  for repeat in range(3):
   self.assertEqual(h.call(u,'create',view),0);h.state(u)
   h.call(u,'draw',view,0x10002000,0)
   heap=struct.unpack('<I',u.mem_read(view+39*4,4))[0]
   for i in range(5):
    w,ht,p=struct.unpack('<HHI',u.mem_read(heap+470400+i*8,8));self.assertEqual((w,ht,p*4),(120,196,heap+i*94080))
    self.assertEqual(self.call(u,0x53209fb8,0,739+i),120)
    self.assertEqual(self.call(u,0x53209fec,0,739+i),196)
   h.call(u,'destroy',view);self.assertFalse(h.live)
   self.assertEqual(self.call(u,0x53209fb8,0,739),40) # Safe immutable fallback after owner releases RAM.
  self.assertEqual(hashlib.sha256(bytes(u.mem_read(0x53000000,len(self.rom)))).digest(),before)
 def test_timestamp_view_never_allocates_card_metadata(self):
  h,u,view=self.fixture();h.call(u,'create',view);h.state(u,3,0);h.call(u,'draw',view,0x10002000,0)
  self.assertEqual(struct.unpack('<I',u.mem_read(view+39*4,4))[0],0);h.call(u,'destroy',view);self.assertFalse(h.live)

 def test_dynamic_directory_adapters_preserve_registers_stack_and_flags(self):
  h,u,view=self.fixture();h.call(u,'create',view);h.state(u);h.call(u,'draw',view,0x10002000,0)
  heap=struct.unpack('<I',u.mem_read(view+39*4,4))[0]
  registers=[getattr(A,'UC_ARM_REG_R'+str(i))for i in range(13)]+[A.UC_ARM_REG_LR,A.UC_ARM_REG_SP]
  for name,outreg,idreg,end in [('width',3,1,0x53209fd4),('height',3,1,0x5320a008),('draw',2,3,0x5320a80c)]:
   for icon in (671,739,743):
    for i,reg in enumerate(registers):u.reg_write(reg,0x12340000+i*256)
    u.reg_write(registers[idreg],icon);u.reg_write(A.UC_ARM_REG_SP,0x100f0000)
    flags=(u.reg_read(A.UC_ARM_REG_CPSR)&0x0fffffff)|0xa0000000;u.reg_write(A.UC_ARM_REG_CPSR,flags)
    expected=[u.reg_read(reg)for reg in registers];expected[outreg]=heap+470440-739*4 if icon>=739 else self.manifest['icons']['table']
    u.emu_start(self.manifest['film_cards']['directory_hooks'][name],end,count=100000)
    self.assertEqual(u.reg_read(A.UC_ARM_REG_PC),end)
    self.assertEqual([u.reg_read(reg)for reg in registers],expected)
    self.assertEqual(u.reg_read(A.UC_ARM_REG_CPSR)&0xf0000000,flags&0xf0000000)

 def test_large_card_oom_keeps_original_icons_and_tears_down_cleanly(self):
  h,u,view=self.fixture(fail=True);h.call(u,'create',view);h.state(u);h.call(u,'draw',view,0x10002000,0)
  self.assertEqual(struct.unpack('<I',u.mem_read(view+39*4,4))[0],0)
  self.assertEqual(self.call(u,0x53209fb8,0,739),40)
  h.call(u,'destroy',view);self.assertFalse(h.live)
