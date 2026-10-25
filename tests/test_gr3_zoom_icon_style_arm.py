"""Native focal artwork parity, executing compiled decoder with owned heap."""
import hashlib,pathlib,struct,subprocess,tempfile,unittest
from unicorn import UC_HOOK_CODE,arm_const as A
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
RAM=0x60000000;STOP=RAM+0xff000
def machine(rom):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x2000000);u.mem_write(0x53000000,rom);u.mem_map(RAM,0x100000)
 u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000);u.reg_write(A.UC_ARM_REG_SP,RAM+0xe0000);return u
def call(u,entry,*args):
 for i,v in enumerate(args):u.reg_write(getattr(A,'UC_ARM_REG_R'+str(i)),v)
 u.reg_write(A.UC_ARM_REG_LR,STOP);u.emu_start(entry,STOP,count=200000);assert u.reg_read(A.UC_ARM_REG_PC)==STOP
from scripts.build_gr3_m10v_library import FLAGS,link_object
ROOT=pathlib.Path(__file__).resolve().parents[1]
def native_tables(r,d,b):
 def sprite(id):
  a=struct.unpack_from('<I',d,id*4)[0]-0x53000000;w,h,o=struct.unpack_from('<HHI',r,a);return w,h,[tuple(b[j:j+4])for j in range(o*4,o*4+w*h*4,4)]
 refs={id:sprite(id)for id in(46,88,89,452)};pal=sorted(set(p for _,_,ps in refs.values()for p in ps));opaque=[p for p in pal if p[3]==255];bg=(53,53,54,255)
 def crop(id,x,y,w,h):
  sw,sh,p=refs.get(id,sprite(id));return [p[(y+yy)*sw+x+xx]for yy in range(h)for xx in range(w)]
 glyph={0:crop(89,16,3,11,14),1:crop(46,16,3,11,14),2:crop(88,5,3,11,14),3:crop(452,5,3,11,14),5:crop(89,5,3,11,14),7:crop(46,5,3,11,14),8:crop(88,16,3,11,14)}
 # Source native numbered-icon glyphs, excluding their enclosing key borders.
 for digit,id,box in((4,607,(9,5,22,25)),(6,609,(9,5,21,26)),(9,612,(9,4,21,25))):
  x0,y0,x1,y1=box;sw=x1-x0;sh=y1-y0;src=crop(id,x0,y0,sw,sh);out=[]
  for y in range(14):
   for x in range(11):
    if x in(0,10):out.append(bg);continue
    # Exact integer area average from sw*sh into9*14, no font dependency.
    total=0
    for sy in range(sh):
     wy=max(0,min((sy+1)*14,(y+1)*sh)-max(sy*14,y*sh))
     for sx in range(sw):
      wx=max(0,min((sx+1)*9,x*sw)-max(sx*9,(x-1)*sw))
      total+=src[sy*sw+sx][0]*wx*wy
    coverage=(total+(sw*sh)//2)//(sw*sh)
    target=tuple(c+((255-c)*coverage+127)//255 for c in bg[:3])+(255,)
    out.append(min(opaque,key=lambda p:sum((p[k]-target[k])**2 for k in range(3))))
  glyph[digit]=out
 idx=lambda p:pal.index(p)
 def arr(name,pixels):
  values=[idx(p)for p in pixels];data=bytearray((len(values)*7+7)//8+1)
  for i,value in enumerate(values):
   bit=i*7;data[bit//8]|=(value<<(bit%8))&255
   data[bit//8+1]|=value>>(8-bit%8)
  return 'static const uint8_t '+name+'['+str(len(data))+']={\n'+''.join(' '+','.join(map(str,data[i:i+22]))+',\n'for i in range(0,len(data),22))+'};\n'
 s='/* Exact original focal35/50/28 glyphs, original71 suffix and mm suffix.\n * Native4/6/9 numbered-icon glyphs area-sampled9x14 within11px cells.\n * Source official GR III2.10 ICONBIN; no runtime filesystem/font dependency. */\n'
 s+='/* ROM SHA256 '+hashlib.sha256(r).hexdigest()+'; ICONBIN SHA256 '+hashlib.sha256(b).hexdigest()+' */\n'
 s+='static const uint32_t native_palette['+str(len(pal))+']={'+','.join(hex(int.from_bytes(bytes(p),'little'))+'u'for p in pal)+'};\n'
 s+=arr('native_digits',sum([glyph[i]for i in range(10)],[]));s+=arr('native_mm',crop(89,28,9,27,8));s+=arr('native_mm71',crop(46,28,9,27,8))
 return s

class IconStyle(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from scripts.build_gr3_m10v_library import capture_stock_rtos
  cls.rom=capture_stock_rtos()
  script="import{readFileSync}from'node:fs';import{officialResources}from'./node/gr3-stock-presets.mjs';const{decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.ICONBIN.offset,s.ICONBIN.offset+s.ICONBIN.size));"
  cls.icons=subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT)
  cls.directory=(ROOT/'native/gr3/m10v_stock_icon_directory.bin').read_bytes()
  with tempfile.TemporaryDirectory()as d:
   o=pathlib.Path(d)/'icon.o';subprocess.run(['clang',*FLAGS,'-c',str(ROOT/'native/gr3/m10v_zoom_icon.c'),'-o',str(o)],check=True,capture_output=True)
   cls.code,cls.symbols=link_object(o.read_bytes(),0x54c00000,{'m10v_zoom_native_icon_alloc':0x536af2a8,'m10v_zoom_mm':0x550f0000},prefix='m10v_zoom_',additional_exports=('m10v_zoom_icon_id','m10v_zoom_icon_decode'))
 def native(self,id):
  at=struct.unpack_from('<I',self.directory,id*4)[0]-0x53000000;w,h,off=struct.unpack_from('<HHI',self.rom,at)
  return self.icons[off*4:off*4+w*h*4]
 def decode(self,mm,oom=False):
  u=machine(self.rom);u.mem_write(0x54c00000,self.code);out=RAM+0x10000;u.mem_write(out-16,b'\xa5'*4832);alloc=[]
  def hook(m,a,s,d):
   if a!=0x536af2a8:return
   alloc.append(m.reg_read(A.UC_ARM_REG_R0));m.reg_write(A.UC_ARM_REG_R0,0 if oom else out);m.reg_write(A.UC_ARM_REG_PC,m.reg_read(A.UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);call(u,self.symbols['m10v_zoom_icon_decode'],782+mm-28)
  self.assertEqual(alloc,[4800]);self.assertEqual(u.reg_read(A.UC_ARM_REG_R0),0 if oom else out)
  self.assertEqual(bytes(u.mem_read(out-16,16)),b'\xa5'*16);self.assertEqual(bytes(u.mem_read(out+4800,16)),b'\xa5'*16)
  return bytes(u.mem_read(out,4800))
 def test_tables_reproduce_from_original_native_assets(self):
  self.assertIn(native_tables(self.rom,self.directory,self.icons),(ROOT/'native/gr3/m10v_zoom_icon.c').read_text())
 def test_known_focal_art_matches_original_native_pixels(self):
  for mm,id in((28,88),(35,452),(50,89)):
   with self.subTest(mm=mm):self.assertEqual(self.decode(mm),self.native(id))
 def test_forty_uses_native_zero_suffix_border_and_background(self):
  p=self.decode(40);native=self.native(89)
  for y in range(20):
   for x in range(60):
    if not(5<=x<16 and 3<=y<17):self.assertEqual(p[(y*60+x)*4:(y*60+x+1)*4],native[(y*60+x)*4:(y*60+x+1)*4],(x,y))
 def test_all_focals_bounded_distinct_and_oom_safe(self):
  pixels=[self.decode(mm)for mm in range(28,51)];self.assertEqual(len(set(pixels)),23)
  self.assertEqual(self.decode(40,True),b'\xa5'*4800)

