import struct,unittest
from pathlib import Path
from scripts.build_gr3_menu_patches import build_menu_patches

class MenuPatchTests(unittest.TestCase):
 def test_only_bleach_lists_grow_and_all_original_items_survive(self):
  rtos=Path('/tmp/m10v-800t-analysis/rtos.bin').read_bytes();extension,patches,report=build_menu_patches(rtos)
  table=report['tables']['items'];read=lambda a,n:extension[a-0x540be000:a-0x540be000+n] if a>=0x540be000 else rtos[a-0x53000000:a-0x53000000+n]
  for s in range(3):
   for k in range(12):
    orig=struct.unpack('<II',rtos[0xb3488c+(s*12+k)*8:0xb3488c+(s*12+k)*8+8]);new=struct.unpack('<II',read(table+(s*12+k)*8,8))
    if k!=8:self.assertEqual(new,orig);continue
    self.assertEqual(new[1],orig[1]+5)
    self.assertEqual(read(new[0],orig[1]*2),read(orig[0],orig[1]*2))
    self.assertEqual(read(new[0]+orig[1]*2,10),bytes(sum(([0,i] for i in range(18,23)),[])))
  for p in patches:self.assertEqual(rtos[p['address']-0x53000000:p['address']-0x53000000+len(bytes.fromhex(p['expected']))],bytes.fromhex(p['expected']))
  # Five old pipeline loads must remain exactly stock.
  self.assertFalse(any(0x536dbd00<=p['address']<=0x536dbd34 for p in patches))

class NativeMenuFlowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rtos=Path('/tmp/m10v-800t-analysis/rtos.bin').read_bytes()
  cls.extension,cls.patches,cls.report=build_menu_patches(cls.rtos)
 def run_flow(self,entry,field,value=None,allocation=True,private_value=None):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R5,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,n in ((0x53000000,0x1200000),(0x55000000,0x10000),(0x57000000,0x10000)):u.mem_map(a,n)
  u.mem_write(0x53000000,self.rtos);u.mem_write(0x540be000,self.extension)
  for p in self.patches:u.mem_write(p['address'],bytes.fromhex(p['replacement']))
  model=0x55004000;widget=0x55006000
  u.mem_write(0x55000004,struct.pack('<I',0x55001000))
  u.mem_write(model+0x199,bytes([0,8,0,0,0,1]))
  u.mem_write(model+0x164,struct.pack('<I',widget))
  u.mem_write(model+0x194,struct.pack('<I',0x55007000))
  if value is not None:u.mem_write(widget+0xf8,struct.pack('<I',value))
  if private_value is not None:u.mem_write(0x55001b28,struct.pack('<8I',0x38564d52,1,0,private_value,0x12345,0,32,0x43464738))
  calls=[]
  def hook(uc,a,n,data):
   args=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
   result=0
   if a==0x5320b31c:result=0x55000000
   elif a==0x535847d8:pass
   elif a==0x53394820:result=(10+field)
   elif a==0x536af2a8:result=0x55009000 if allocation else 0;calls.append(('alloc',args[0]))
   elif a==0x532c282c:calls.append(('stock_reset',args[0]))
   elif a==0x5339ee0c:calls.append(('current',args[1]))
   elif a==0x5339f194:calls.append(('range',args[1],args[2]))
   elif a==0x5339f1f0:calls.append(('default',args[1]))
   elif a==0x533abeb0:
    closure=struct.unpack('<III',uc.mem_read(struct.unpack('<I',uc.mem_read(args[1],4))[0],12));calls.append(('closure',closure))
   elif a in (0x5320ad88,0x5320ba9c,0x5339f210,0x5339f328,0x531ac95c,0x531b07c4):pass
   else:return
   uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  sp=0x5700fff0;u.reg_write(UC_ARM_REG_R5,model);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_R0,model);u.reg_write(UC_ARM_REG_LR,0x57000000)
  u.emu_start(entry,0x57000000,count=200000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x57000000)
  self.assertEqual(u.reg_read(UC_ARM_REG_SP),sp)
  return calls,bytes(u.mem_read(0x55001b28,32))
 def test_native_focused_values_for_all_five_new_rows(self):
  for field,value in enumerate((3,3,5,2,0)):
   with self.subTest(field=field):self.assertIn(('current',value),self.run_flow(0x531b03cc,field)[0])
 def test_native_setup_uses_correct_range_default_and_original_closure(self):
  for field,default in enumerate((3,3,5,2,0)):
   with self.subTest(field=field):
    calls,_=self.run_flow(0x531b05c4,field)
    self.assertIn(('range',0,8 if field<3 else 3),calls)
    self.assertIn(('default',default),calls)
    self.assertIn(('closure',(0x531b0fd0,0,0x55004000)),calls)
 def test_native_callback_reaches_private_record_without_stock_slider_writes(self):
  for field,value in enumerate((8,0,7,3,2)):
   with self.subTest(field=field):
    _,block=self.run_flow(0x531b0bac,field,value)
    packed=struct.unpack('<8I',block)[3]
    self.assertEqual((packed>>(field*4))&15,value)
 def test_caption_stubs_localize_new_ids_and_preserve_stock_invalid_routes(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R3,UC_ARM_REG_R7,UC_ARM_REG_R11,UC_ARM_REG_PC
  for kind,address,continuation,descriptor_reg,stock,invalid in [('A',0x540bf000,0x53396700,UC_ARM_REG_R7,0x533966e8,0x53396850),('B',0x540bf080,0x5339710c,UC_ARM_REG_R3,0x533970fc,0x533971e0)]:
   for language in (1,19,21):
    for sid in (0x119,0x312,0x316,0x317):
     with self.subTest(kind=kind,language=language,sid=sid):
      u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x1200000);u.mem_write(0x53000000,self.rtos);u.mem_write(0x540be000,self.extension)
      for reg,v in ((UC_ARM_REG_R0,language),(UC_ARM_REG_R3,0x311),(UC_ARM_REG_R7,sid),(UC_ARM_REG_R11,0x57001000)):u.reg_write(reg,v)
      target=continuation if language<=20 and 0x312<=sid<=0x316 else stock if language<=20 and sid<=0x311 else invalid
      u.emu_start(address,target,count=100)
      self.assertEqual(u.reg_read(UC_ARM_REG_PC),target)
      if target==continuation:
       n,ptr=struct.unpack('<II',u.mem_read(u.reg_read(descriptor_reg),8));caption=bytes(u.mem_read(ptr,(n&255)*2)).decode('utf-16le').rstrip('\0')
       self.assertEqual(caption,(['红晕强度','扩散范围','高光阈值','红晕档位','颗粒感'] if language==19 else self.report['fields'])[sid-0x312])
 def test_allocation_shim_preserves_prefix_and_only_clears_new_tail(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R4,UC_ARM_REG_R12,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_PC
  for allocation in (0,0x55001000):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   for a,n in ((0x53000000,0x1200000),(0x55000000,0x10000),(0x57000000,0x10000)):u.mem_map(a,n)
   u.mem_write(0x540be000,self.extension);u.mem_write(0x55001000,b'\xa5'*0xb60)
   def hook(uc,a,n,data):
    if a==0x53100000:
     self.assertEqual(uc.reg_read(UC_ARM_REG_R1),0xb48);self.assertEqual(uc.reg_read(UC_ARM_REG_SP)&7,0)
     uc.reg_write(UC_ARM_REG_R0,allocation);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook)
   for reg,v in ((UC_ARM_REG_R1,0xb48),(UC_ARM_REG_R4,0x12345678),(UC_ARM_REG_R12,0x53100000),(UC_ARM_REG_LR,0x57000000),(UC_ARM_REG_SP,0x5700fff0)):u.reg_write(reg,v)
   u.emu_start(0x540bf340,0x57000000,count=1000)
   self.assertEqual(u.reg_read(UC_ARM_REG_R0),allocation);self.assertEqual(u.reg_read(UC_ARM_REG_R4),0x12345678)
   self.assertEqual(bytes(u.mem_read(0x55001000,0xb60)),b'\xa5'*0xb28+(bytes(32) if allocation else b'\xa5'*32)+b'\xa5'*24)

 def test_new_slider_allocation_failure_returns_without_constructing_null_delegate(self):
  calls,_=self.run_flow(0x531b05c4,4,allocation=False)
  self.assertIn(('alloc',12),calls);self.assertFalse(any(c[0]=='closure' for c in calls))
 def test_stock_reset_is_preserved_and_new_defaults_reset_only_selected_set(self):
  calls,block=self.run_flow(0x540bf3a0,0,private_value=0x38888)
  self.assertEqual(sum(c[0]=='stock_reset' for c in calls),1)
  self.assertEqual(struct.unpack('<8I',block)[3:6],(0x2533,0x12345,0))
