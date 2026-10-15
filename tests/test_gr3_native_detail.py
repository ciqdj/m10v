"""Execute new controls through stock ARM detail selector/setup/callback paths."""
import json, struct, tempfile, unittest, subprocess
from pathlib import Path
from scripts.build_gr3_m10v_library import build

class NativeDetailTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=tempfile.TemporaryDirectory(); build(cls.folder.name)
  cls.manifest=json.loads((Path(cls.folder.name)/'m10v-library-arm.json').read_text())
  cls.runtime=(Path(cls.folder.name)/'m10v-library-arm.bin').read_bytes()
 def test_five_controls_integrated_with_unified_runtime(self):
  self.assertIn('detail',self.manifest,'native runtime has no stock five-control detail integration')
  self.assertEqual(self.manifest['detail']['fields'],['Halation Gain','Halation Spread','Highlight Gate','Film Grain','Soft Diffusion'])
  self.assertEqual(self.manifest['detail']['ids'],[18,19,20,21,22])
  self.assertEqual(self.manifest['detail']['backend'],'m10v_camera_library_detail')


 def test_caption_pairs_resolve_actual_runtime_resources(self):
  base=self.manifest['base'];at=self.manifest['detail']['captions']-base
  ids=[struct.unpack_from('<H',self.runtime,at+72+i*4)[0] for i in range(5)]
  labels=[]
  resources=self.manifest['resources']
  for resource_id in ids:
   descriptor=resources['descriptors'][resource_id-resources['first_id']]-base
   length,flags,reserved,pointer=struct.unpack_from('<BBHI',self.runtime,descriptor)
   labels.append(self.runtime[pointer-base:pointer-base+(length-1)*2].decode('utf-16le'))
  self.assertEqual(labels,['Halation Gain','Halation Spread','Highlight Gate','Grain','Soft Diffusion'])

class StockDetailArmTests(NativeDetailTests):
 @classmethod
 def setUpClass(cls):
  super().setUpClass()
  script="""
import {readFileSync,writeFileSync} from 'node:fs';
import {decodeFrameMap} from './node/gr3-frames.mjs';
const source=readFileSync('bin/fwdc239b-gr3-official.bin'),d=decodeFrameMap(source).decoded;
let at=0;while(d.toString('ascii',at,at+4)!=='RTOS')at+=16+d.readUInt32LE(at+12);
writeFileSync(process.argv[1]+'/official-rtos.bin',d.subarray(at+16,at+16+d.readUInt32LE(at+12)));
"""
  subprocess.run(['node','--input-type=module','-e',script,cls.folder.name],cwd=Path(__file__).resolve().parents[1],check=True)
  cls.rtos=(Path(cls.folder.name)/'official-rtos.bin').read_bytes()
 def machine(self,tone=21,film=33,field=0,allocation=True,save_ok=True):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_PC,UC_ARM_REG_LR
  from scripts.build_gr3_native_detail import branch,movw
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,n in ((0x53000000,0x1400000),(0x55000000,0x10000),(0x57000000,0x10000)):u.mem_map(a,n)
  u.mem_write(0x53000000,self.rtos);u.mem_write(self.manifest['base'],self.runtime)
  d=self.manifest['detail'];e=d['entries']
  for a,name,link in [(0x531afc20,'capacity',True),(0x531afa24,'table_ip',True),(0x531afacc,'table_r3',True),(0x531affa8,'table_ip',True),(0x531b01f8,'table_selected',True),(0x531b000c,'row',False),(0x531b03f8,'current',False),(0x531b05e4,'setup',False),(0x531b0bf4,'callback',False),(0x531acd24,'reset',True)]:u.mem_write(a,struct.pack('<I',branch(a,e[name],link)))
  for a,w in [(0x531b0248,movw(3,d['captions']&65535)),(0x531b024c,movw(3,d['captions']>>16,True))]:u.mem_write(a,struct.pack('<I',w))
  ui=0x55004000;slider=0x55006000
  u.mem_write(ui+0x198,bytes([tone,0,8,0,0,0,1]))
  u.mem_write(ui+0x164,struct.pack('<I',slider));u.mem_write(ui+0x160,struct.pack('<I',0x55008000));u.mem_write(ui+0x194,struct.pack('<I',0x55007000))
  state=bytearray.fromhex(self.manifest['initial_state_hex']);slots=[12,18,19,20,21]
  for i in range(5):struct.pack_into('<H6B',state,12+i*8,film,1,2,3,4,5,2)
  calls=[]
  def hook(uc,a,n,data):
   args=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)];result=0
   if a==self.manifest['symbols']['m10v_camera_library_load']:uc.mem_write(args[0],bytes(state))
   elif a==self.manifest['symbols']['m10v_library_valid']:result=1
   elif a==self.manifest['symbols']['m10v_camera_library_detail']:
    from unicorn.arm_const import UC_ARM_REG_SP
    extra=struct.unpack('<4I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),16));calls.append(('save',args[1],args[2],args[3],*extra))
    if save_ok:
     i=args[1];v=list(state[14+i*8:20+i*8]);v[2]=args[2];v[3]=args[3];v[4]=extra[0];v[0]=extra[1];v[1]=extra[2];state[14+i*8:20+i*8]=bytes(v)
    else:result=0xfffffffe
   elif a==0x536b93d0:result=0
   elif a==0x5320b31c:result=0x55000000
   elif a==0x53394820:
    # Match the real selected private list row, including each stock prefix.
    kind=uc.mem_read(ui+0x19a,1)[0];setting=uc.mem_read(ui+0x199,1)[0]
    p,n=struct.unpack_from('<II',self.rtos,0xb3488c+(setting*12+kind)*8);result=n+field
   elif a==0x536af2a8:result=0x55009000 if allocation else 0;calls.append(('alloc',args[0]))
   elif a==0x532c282c:calls.append(('stock_reset',))
   elif a==0x5339ee0c:calls.append(('current',args[1]))
   elif a==0x5339f194:calls.append(('range',args[1],args[2]))
   elif a==0x5339f1f0:calls.append(('default',args[1]))
   elif a==0x533abeb0:
    ptr=struct.unpack('<I',uc.mem_read(args[1],4))[0];calls.append(('closure',struct.unpack('<III',uc.mem_read(ptr,12))))
   elif a==0x53396f80:calls.append(('caption',args[1]))
   elif a==0x53394758:result=0x5500a000
   elif a==0x5339e2f8:calls.append(('row',args[1],bytes(uc.mem_read(args[2],16)).decode('utf-16le').rstrip('\0')))
   elif a==0x531b07c4:calls.append(('redraw',))
   elif a in (0x532bd5fc,0x532c34a8,0x532c2834,0x5316ca28,0x532c34e4):calls.append(('stock_exit',a))
   elif a in (0x5320ad88,0x5320ba9c,0x5339f210,0x5339f328,0x531ac95c,0x531b07c4):pass
   else:return
   uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  kind=self.execute(u,0x531aca98,ui,tone)
  u.mem_write(ui+0x19a,bytes([kind]))
  return u,ui,slider,calls,state
 def execute(self,u,entry,*args):
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R5,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
  sp=0x5700fff0
  for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,v)
  u.reg_write(UC_ARM_REG_R5,0x55004000);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,0x57000000)
  u.emu_start(entry,0x57000000,count=300000)
  self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x57000000);self.assertEqual(u.reg_read(UC_ARM_REG_SP),sp)
  return u.reg_read(UC_ARM_REG_R0)
 def test_real_detail_list_constructor_enumerates_all_settings_before_tone_selection(self):
  # FN constructs the page with stock tone11 before reading the actual tone.
  # Its list initializer enumerates 3 settings x12 kinds, not just setting0.
  from unicorn import UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R2,UC_ARM_REG_PC,UC_ARM_REG_LR
  for tone in (11,12,18,21):
   u,ui,slider,calls,state=self.machine(tone=tone)
   observed=[]
   def services(uc,a,n,data):
    if a==0x536af31c:
     observed.append(('allocate',uc.reg_read(UC_ARM_REG_R0)));uc.reg_write(UC_ARM_REG_R0,0x5500c000)
    elif a==0x53394610:observed.append(('rows',uc.reg_read(UC_ARM_REG_R2)))
    elif a in (0x536af358,0x533958a8,0x533958b4,0x53394b38,0x531ac8d8):pass
    elif a==0x53820074:raise AssertionError('stock stack canary failed')
    else:return
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,services)
   self.execute(u,0x531afbe0,ui)
   expected=16
   self.assertEqual(observed,[('allocate',expected),('rows',expected)])

 def test_visibility_index_uses_stock_lr_stride_in_all_three_settings(self):
  for setting in range(3):
   for kind in range(12):
    u,ui,slider,calls,state=self.machine(tone=11)
    p,n=struct.unpack_from('<II',self.rtos,0xb3488c+(setting*12+kind)*8)
    expected=sum(self.rtos[p-0x53000000+i*2]!=1 for i in range(n))
    self.assertEqual(self.execute(u,0x531afab8,ui,setting,kind),expected)

 def test_whole_row_dispatcher_in_all_settings_preserves_private_and_stock_rows(self):
  from unicorn import UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_LR
  handlers=set(struct.unpack_from('<18I',self.rtos,0x1b0010))
  for tone in (11,12,18,19,20,21):
   for setting in range(3):
    u,ui,slider,calls,state=self.machine(tone=tone)
    u.mem_write(ui+0x199,bytes([setting]));u.mem_write(ui+0x19e,bytes([16]))
    def widgets(uc,a,n,data):
     if a in handlers:uc.reg_write(UC_ARM_REG_PC,0x531b0064)
     elif a==0x5339e274:uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,widgets);self.execute(u,0x531aff84,ui)
    self.assertEqual(len([c for c in calls if c[0]=='row']),0 if tone==11 else 5)

 def test_stock_count_and_selector_resolve_each_carrier_dynamically(self):
  for tone in (12,18,19,20,21):
   for film in (33,34):
    u,ui,slider,calls,state=self.machine(tone,film)
    kind=u.mem_read(ui+0x19a,1)[0]
    p,n=struct.unpack_from('<II',self.rtos,0xb3488c+kind*8)
    original=sum(self.rtos[p-0x53000000+i*2]!=1 for i in range(n))
    self.assertEqual(self.execute(u,0x531afab8,ui,0,kind),original+(5 if film==33 else 0))
    if film==33:
     for field in range(5):
      # machine's external widget-index stub supplies last field selection.
      u,ui,slider,calls,state=self.machine(tone,film,field)
      self.assertEqual(self.execute(u,0x531b01d0,ui),18+field)
 def test_actual_setup_retains_stock_closure_and_distinct_ranges(self):
  for tone in (12,18,19,20,21):
   for field in range(5):
    u,ui,slider,calls,state=self.machine(tone,33,field)
    self.execute(u,0x531b05c4,ui)
    self.assertIn(('range',0,8 if field<3 else 3),calls)
    self.assertIn(('closure',(0x531b0fd0,0,ui)),calls)
 def test_stock_current_reads_five_independent_fields(self):
  for field,expected in enumerate((3,4,5,1,2)):
   u,ui,slider,calls,state=self.machine(field=field);self.execute(u,0x531b03cc,ui)
   self.assertIn(('current',expected),calls)
 def test_real_callback_persists_selected_slot_and_failure_restores_slider(self):
  for tone in (12,18,19,20,21):
   for field in range(5):
    for ok in (True,False):
     u,ui,slider,calls,state=self.machine(tone,33,field,save_ok=ok);before=bytes(state)
     u.mem_write(slider+0xf8,struct.pack('<I',2));self.execute(u,0x531b0fd0,ui)
     self.assertEqual(sum(c[0]=='save' for c in calls),1)
     if not ok:
      self.assertEqual(bytes(state),before);self.assertNotIn(('redraw',),calls,'stock redraw would overwrite the save-failure caption');self.assertIn(('caption',824),calls);self.assertIn(('current',(3,4,5,1,2)[field]),calls)
     else:
      i=(12,18,19,20,21).index(tone);self.assertEqual(state[12+i*8+(4,5,6,2,3)[field]],2)
 def test_invalid_values_and_non800t_never_write(self):
  for film in (33,34):
   for arg in (0x009,0x308,0x403,0x503,0xffff):
    u,ui,slider,calls,state=self.machine(film=film)
    result=self.execute(u,self.manifest['symbols']['m10v_detail_control'],2,ui,arg)
    if film==34 or arg!=0x403:self.assertFalse(any(c[0]=='save' for c in calls))
 def test_slider_allocation_failure_retains_stock_null_guard(self):
  u,ui,slider,calls,state=self.machine(allocation=False);self.execute(u,0x531b05c4,ui)
  self.assertIn(('alloc',12),calls);self.assertFalse(any(c[0]=='closure' for c in calls))
 def test_reset_uses_one_atomic_journal_write_after_stock_reset(self):
  for tone in (12,18,19,20,21):
   u,ui,slider,calls,state=self.machine(tone);self.execute(u,self.manifest['detail']['entries']['reset'],ui)
   self.assertEqual(sum(c[0]=='stock_reset' for c in calls),1);self.assertEqual(sum(c[0]=='save' for c in calls),1)

 def test_stock_row_render_uses_private_values_without_stock_tone_writes(self):
  # Real row dispatcher loops through all stock rows, so start at the private
  # branch with its original saved-frame contract and a sentinel continuation.
  from unicorn.arm_const import UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
  for field,text in enumerate(('3/8','4/8','5/8','Weak','Mid')):
   u,ui,slider,calls,state=self.machine(field=field)
   u.reg_write(UC_ARM_REG_R3,18+field);u.reg_write(UC_ARM_REG_R4,10+field);u.reg_write(UC_ARM_REG_R5,ui)
   u.reg_write(UC_ARM_REG_SP,0x5700fff0);u.reg_write(UC_ARM_REG_LR,0x57000000)
   u.emu_start(self.manifest['detail']['entries']['row'],0x531b0064,count=10000)
   self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x531b0064);self.assertIn(('row',0x1e3,text),calls)
   self.assertFalse(any(c[0]=='save' for c in calls))
 def test_private_profile_menu_is_unreachable(self):
  # Group10 is the existing private halation submenu, now only three controls.
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_PC,UC_ARM_REG_LR,UC_ARM_REG_SP
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  u.mem_map(0x54000000,0x200000);u.mem_write(self.manifest['base'],self.runtime);u.mem_map(0x55068000,0x1000);u.mem_map(0x57000000,0x10000)
  u.mem_write(0x55068200+0x1d,b'\x0a')
  u.reg_write(UC_ARM_REG_R0,0x55068200);u.reg_write(UC_ARM_REG_LR,0x57000000);u.reg_write(UC_ARM_REG_SP,0x5700fff0)
  u.emu_start(self.manifest['symbols']['m10v_menu_count'],0x57000000,count=1000)
  self.assertEqual(u.reg_read(UC_ARM_REG_R0),3)

 def test_original_confirm_and_cancel_exit_without_extra_private_write(self):
  for entry in (0x531b0aa4,0x531b0aec):
   for field in range(5):
    u,ui,slider,calls,state=self.machine(field=field)
    u.mem_write(slider+0xf8,struct.pack('<I',2));self.execute(u,0x531b0fd0,ui)
    before=bytes(state);calls.clear();self.execute(u,entry,ui)
    self.assertEqual(bytes(state),before);self.assertFalse(any(c[0]=='save' for c in calls))
    self.assertIn(('stock_exit',0x5316ca28),calls)

 def test_dynamic_table_shims_preserve_registers_stack_and_flags(self):
  from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12,UC_ARM_REG_LR,UC_ARM_REG_SP,UC_ARM_REG_CPSR
  registers=(UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12)
  for name,output in [('table_ip',12),('table_r3',3),('table_selected',3)]:
   u,ui,slider,calls,state=self.machine()
   expected=[0x12340000+i for i in range(13)];expected[4 if name=='table_selected' else 0]=ui
   for reg,value in zip(registers,expected):u.reg_write(reg,value)
   u.reg_write(UC_ARM_REG_SP,0x5700fff0);u.reg_write(UC_ARM_REG_LR,0x57000000);u.reg_write(UC_ARM_REG_CPSR,0xa0000013)
   u.emu_start(self.manifest['detail']['entries'][name],0x57000000,count=20000)
   expected[output]=self.manifest['detail']['tables']
   self.assertEqual([u.reg_read(reg) for reg in registers],expected)
   self.assertEqual(u.reg_read(UC_ARM_REG_SP),0x5700fff0);self.assertEqual(u.reg_read(UC_ARM_REG_CPSR)&0xf0000000,0xa0000000)
 def test_invalid_models_and_nonshooting_route_to_unchanged_stock_table(self):
  for pointer in (0,0x54000000,0xffffffff):
   u,ui,slider,calls,state=self.machine()
   self.assertEqual(self.execute(u,self.manifest['symbols']['m10v_detail_table'],pointer),0x53b3488c)
  for offset,value in ((0x198,11),(0x199,3),(0x19a,12),(0x19b,1),(0x19d,1)):
   u,ui,slider,calls,state=self.machine();u.mem_write(ui+offset,bytes([value]))
   self.assertEqual(self.execute(u,self.manifest['symbols']['m10v_detail_table'],ui),0x53b3488c)

if __name__=='__main__':unittest.main()
