"""ARM ABI checks for custom crop controls; no firmware or camera required."""
import importlib.util, pathlib, shutil, struct, subprocess, tempfile, unittest
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=0x540bc000; RAM=0x60000000; STOP=RAM+0xff000
EXTERNAL={'m10v_zoom_camera_bits':RAM+0xf1000,'m10v_zoom_camera_slot':RAM+0xf1010,'m10v_zoom_camera_select':RAM+0xf1020,'m10v_zoom_caption':RAM+0xf1030}
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def bits(mm):return struct.unpack('<I',struct.pack('<f',mm/28))[0]
class ZoomLive(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  spec=importlib.util.spec_from_file_location('zoom_build',ROOT/'scripts/gr3_aspect_overlay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as tmp:
   tmp=pathlib.Path(tmp);objects=[]
   for suffix in ['c','S']:
    obj=tmp/(suffix+'.o');subprocess.run([shutil.which('clang'),*m.FLAGS,'-c',str(ROOT/'native/gr3'/('m10v_zoom_live.'+suffix)),'-o',str(obj)],check=True,capture_output=True);objects.append(str(obj))
   script=tmp/'link.ld';script.write_text('SECTIONS { . = 0x540bc000; .text : { *(.text*) } .rodata : { *(.rodata*) } /DISCARD/ : { *(.ARM.exidx*) } }')
   elf=tmp/'test.elf';ld=shutil.which('ld.lld') or '/opt/homebrew/opt/lld/bin/ld.lld'
   subprocess.run([ld,'-T',str(script),*objects,*[f'--defsym={k}={v}' for k,v in EXTERNAL.items()],'-o',str(elf)],check=True,capture_output=True)
   data=elf.read_bytes();offset=struct.unpack_from('<I',data,32)[0];stride,count,_=struct.unpack_from('<HHH',data,46);sections=[struct.unpack_from('<10I',data,offset+i*stride) for i in range(count)];cls.code=bytearray(0x2000);cls.symbols={}
   for row in sections:
    if row[2]&2 and row[1]==1:cls.code[row[3]-BASE:row[3]-BASE+row[5]]=data[row[4]:row[4]+row[5]]
    if row[1]==2:
     st=sections[row[6]];strings=data[st[4]:st[4]+st[5]]
     for pos in range(row[4],row[4]+row[5],16):
      name,value,size,info,other,index=struct.unpack_from('<IIIBBH',data,pos);name=strings[name:].split(b'\0',1)[0].decode()
      if index:cls.symbols[name]=value
 def machine(self,values=(36,49),slot=2,reject=0):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(BASE,bytes(self.code));u.mem_map(RAM,0x100000)
  u.reg_write(UC_ARM_REG_SP,RAM+0xe0000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
  mags=[bits(values[0]),bits(values[1]),bits(28)];state={'slot':slot,'front':mags[slot],'back':mags[slot],'sets':[],'selected':[],'reject':reject,'setup':0,'assert':None}
  u.mem_write(RAM+0x100,struct.pack('<I',RAM+0x200))
  def hook(uc,a,size,data):
   x=uc.reg_read(UC_ARM_REG_R0);ret=0
   if a==EXTERNAL['m10v_zoom_camera_bits']:ret=mags[x]
   elif a==EXTERNAL['m10v_zoom_camera_slot']:
    ret=state['slot'] if mags[state['slot']]==x else next((i for i,v in enumerate(mags) if v==x),2)
   elif a==EXTERNAL['m10v_zoom_camera_select']:state['slot']=x;state['selected'].append(x);ret=1
   elif a==EXTERNAL['m10v_zoom_caption']:ret=1000+round(struct.unpack('<f',struct.pack('<I',x))[0]*28)
   elif a==0x5320ad88:ret=RAM+0x80
   elif a==0x5320b31c:ret=RAM+0x300
   elif a==0x53525d5c:ret=RAM+0x100
   elif a in (0x5324526c,0x5354a7bc):uc.reg_write(UC_ARM_REG_S0,state['front' if a==0x5324526c else 'back'])
   elif a==0x53252684:
    v=uc.reg_read(UC_ARM_REG_S0);state['sets'].append(v);state['front']=v
    if state['reject']:state['reject']-=1
    else:state['back']=v
    ret=1
   elif a==0x5320b7fc:state['setup']+=1
   elif a==0x53243e40:ret=0
   elif a==0x536b93d0:state['assert']=[uc.reg_read(r) for r in REGS]
   else:return
   uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);return u,state
 def call(self,u,name,*args):
  for reg,val in zip(REGS,args):u.reg_write(reg,val)
  u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(self.symbols['m10v_zoom_'+name],STOP,count=10000);return u.reg_read(UC_ARM_REG_R0)
 def test_set_readback_and_rejection(self):
  for reject in (0,1):
   u,s=self.machine(reject=reject);self.call(u,'set',0,0);self.assertEqual(s['sets'],[bits(36)]);self.assertEqual(s['selected'],[] if reject else [0])
 def test_active_edit_reports_backend_acceptance(self):
  for reject in (0,1):
   u,s=self.machine(reject=reject);self.assertEqual(self.call(u,'live_apply',0),0xffffffff if reject else 0);self.assertEqual(s['selected'],[] if reject else [0])
 def test_cycle_duplicates_and_reverse(self):
  for vals in [(36,49),(49,36),(41,41),(28,28)]:
   u,s=self.machine(values=vals)
   for slot in [0,1,2,0]:self.call(u,'cycle');self.assertEqual(s['slot'],slot)
   self.assertEqual(s['setup'],4);self.assertEqual(s['assert'],[1,0x53b21184,0x53b21164,0x64b])
 def test_cycle_retry_bound(self):
  u,s=self.machine(reject=3);self.call(u,'cycle');self.assertEqual(len(s['sets']),3);self.assertEqual(s['setup'],3)
 def test_predicates_use_identity(self):
  u,s=self.machine(values=(41,41),slot=1)
  self.assertEqual([self.call(u,'selected',0,i) for i in range(3)],[0,1,0])
 def test_labels_preserve_registers(self):
  for name,reg in [('label_menu',UC_ARM_REG_R5),('label_adj',UC_ARM_REG_R4)]:
   for slot in range(3):
    u,s=self.machine();u.reg_write(reg,slot);self.assertEqual(self.call(u,name),[1036,1049,2][slot]);self.assertEqual(u.reg_read(reg),slot)
  u,s=self.machine();u.reg_write(UC_ARM_REG_S0,bits(49));self.assertEqual(self.call(u,'label_live'),1049)
  for slot in [0,2]:
   u,s=self.machine(values=(28,49),slot=slot);u.reg_write(UC_ARM_REG_S0,bits(28));self.assertEqual(self.call(u,'label_live'),1028 if slot==0 else 2)
   u.reg_write(UC_ARM_REG_R5,0);self.assertEqual(self.call(u,'label_menu'),1028)
if __name__=='__main__':unittest.main()
