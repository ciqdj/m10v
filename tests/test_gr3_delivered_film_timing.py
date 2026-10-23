"""Execute the delivered BIN, including shared HDF and appended five-slot ABI.
UI/FS and ISP hardware remain explicit boundaries; this is not camera approval.
"""
import hashlib,json,os,struct,subprocess,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import arm_const as A
from tests import test_gr3_live_color_preview as live
from tests.test_gr3_isp_base import StockISP,ROOT
from tests import test_gr3_isp_recipe_color as recipe_fixture


class DeliveredFilmTimingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.folder=Path(os.environ.get('M10V_FILM_TIMING_CANDIDATE',
      'builds/m10v-gr3-film-timing-r1-20261021'))
  binary=cls.folder/'gr3/fwdc239b.bin'
  if not binary.exists():raise unittest.SkipTest('build the film timing candidate first')
  cls.manifest=json.loads((cls.folder/'gr3/manifest.json').read_text())
  receipt=json.loads((cls.folder/'gr3/receipt.json').read_text())
  assert hashlib.sha256(binary.read_bytes()).hexdigest()==receipt['candidate_sha256']
  js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
  cls.candidate=subprocess.check_output(['node','--input-type=module','-e',js,str(binary)],cwd=ROOT)
  at=cls.manifest['base']-0x53000000
  cls.code=cls.candidate[at:at+cls.manifest['code_bytes']]
  assert hashlib.sha256(cls.code).hexdigest()==cls.manifest['code_sha256']
  cls.snapshot=cls.manifest['capture_lifecycle']['snapshot']
  assert cls.snapshot['shared_hdf'] and cls.snapshot['producer_sites']==[0x5351ae44]
  cls.entry=next(p['entry']for p in cls.snapshot['patches']if p['address']==0x53dbd954)

 cache=live.LiveColorPreviewTests.cache
 test_live_enter_initializes_and_reloads_preview_without_opening_film_library=live.LiveColorPreviewTests.test_live_enter_initializes_and_reloads_preview_without_opening_film_library

 def test_actual_five_slot_bin_freezes_at_submission_and_not_at_either_reservation(self):
  for reserve in (0x5351aed4,0x5351b068):
   for tone in self.manifest['appended_slots']['tones']:
    e=StockISP(self.candidate);self.cache(e,33)
    recipe=e.alloc(0x50f0);owner=e.alloc(0xb00);data=e.alloc(0xb28)
    e.w32(recipe,0x53d0fc90);e.w32(recipe+0x4778,0x31545653)
    e.w32(owner+0xf0,recipe);e.w32(0x55063ed0,1);e.w32(0x55063f34,data)
    e.u.mem_write(data+0x1c2,bytes([25]))
    def unavailable_fs(u,at,n,_):
     if at==0x53828014:
      u.reg_write(A.UC_ARM_REG_R0,0);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
    e.u.hook_add(UC_HOOK_CODE,unavailable_fs)
    e.u.reg_write(A.UC_ARM_REG_R4,owner);e.u.reg_write(A.UC_ARM_REG_SP,0x5effff00)
    e.u.emu_start(reserve,reserve+4,count=100000)
    self.assertEqual(bytes(e.u.mem_read(recipe+0x4a08,4)),bytes(4))
    self.cache(e,66,version=4);e.u.mem_write(data+0x1c2,bytes([tone]))
    e.u.reg_write(A.UC_ARM_REG_R0,owner);e.u.reg_write(A.UC_ARM_REG_SP,0x5effff00)
    e.u.emu_start(0x5351ae2c,0x5351ae64,count=100000)
    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_PC),0x5351ae64)
    out=e.alloc(104);e.call(self.snapshot['exports']['m10v_isp_frame_recipe_state'],recipe,out)
    self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
    self.assertEqual(struct.unpack('<H',e.u.mem_read(out+12,2))[0],66)
    self.assertEqual(struct.unpack('<H',e.u.mem_read(recipe+0x4a08+22,2))[0],tone)
    before=bytes(e.u.mem_read(recipe+0x4a08,1716))
    self.cache(e,68,version=6);e.u.mem_write(data+0x1c2,bytes([29]))
    e.u.reg_write(A.UC_ARM_REG_R0,owner)
    e.u.emu_start(0x5351ae44,0x5351ae48,count=100000)
    self.assertEqual(bytes(e.u.mem_read(recipe+0x4a08,1716)),before)

 def test_delivered_null_current_recipe_returns_to_startup_branch_without_io(self):
  e=StockISP(self.candidate);owner=e.alloc(0xb00);accesses=[]
  watch={self.manifest['symbols']['m10v_camera_library_load'],0x53828014,0x53825648,0x53825fa8}
  e.u.hook_add(UC_HOOK_CODE,lambda u,at,n,d:accesses.append(at)if at in watch else None)
  e.u.reg_write(A.UC_ARM_REG_R0,owner);e.u.reg_write(A.UC_ARM_REG_SP,0x5effff00)
  e.u.emu_start(0x5351ae2c,0x5351b038,count=100000)
  self.assertEqual(e.u.reg_read(A.UC_ARM_REG_PC),0x5351b038)
  self.assertEqual(accesses,[])

 def test_installed_still_make_uses_the_film_frozen_by_actual_submission(self):
  films=(33,66,67,68,69);tones=self.manifest['appended_slots']['tones']
  for slot,tone in enumerate(tones):
   e=StockISP(self.candidate);self.cache(e,33)
   e.u.mem_write(0x550d1944,recipe_fixture.state(films))
   recipe=e.alloc(0x50f0);owner=e.alloc(0xb00);data=e.alloc(0xb28)
   e.w32(recipe,0x53d0fc90);e.w32(recipe+0x4778,0x31545653);e.w32(owner+0xf0,recipe)
   obj=e.cursor;e.make(tones[(slot+4)%5],1);frame=obj+0x1400
   si=struct.unpack('<I',e.u.mem_read(frame+0x82d0,4))[0]
   shooting=bytes(e.u.mem_read(si,0x80000));base=bytes(e.u.mem_read(frame,0x9000))
   context=recipe+0x96c;e.w32(context+0x30,recipe+0x1a8);e.w32(context+0x34,si)
   e.w32(0x55063ed0,1);e.w32(0x55063f34,data);e.u.mem_write(data+0x1c2,bytes([tone]))
   e.u.reg_write(A.UC_ARM_REG_R0,owner);e.u.reg_write(A.UC_ARM_REG_SP,0x5effff00)
   e.u.emu_start(0x5351ae44,0x5351ae48,count=100000)
   e.u.mem_write(data+0x1c2,bytes([tones[(slot+1)%5]]))
   recipe_fixture.RecipeColorTests.callback(self,e,obj,frame,context)
   self.assertEqual(struct.unpack('<I',e.u.mem_read(recipe+0x4a08+12,4))[0],2)
   actual=bytes(e.u.mem_read(frame,0x9000))
   e.u.mem_write(frame,base);target=e.alloc(1600)
   gamma=struct.unpack('<I',e.u.mem_read(obj+0x17c,4))[0];exports=self.snapshot['exports']
   e.call(exports['m10v_isp_native_look_prepare'],target,films[slot],0,9)
   e.call(exports['m10v_isp_native_look_apply'],target,gamma,frame,0)
   self.assertEqual(actual,bytes(e.u.mem_read(frame,0x9000)))
   self.assertEqual(bytes(e.u.mem_read(si,0x80000)),shooting)

 def test_independent_auditor_rejects_tampered_submission_even_with_repaired_hash(self):
  js="""import{readFileSync}from'node:fs';import{createHash}from'node:crypto';
import assert from'node:assert/strict';import{buildNativeLibrary}from'./node/gr3-m10v-native-build.mjs';
const folder=process.argv[1],m=JSON.parse(readFileSync(folder+'/gr3/manifest.json')),
 r=readFileSync(folder+'/evidence/runtime.bin'),s=readFileSync('bin/fwdc239b-gr3-official.bin');
const at=m.capture_lifecycle.snapshot.patches[1].entry-m.base;r[at+24]^=1;
m.code_sha256=createHash('sha256').update(r).digest('hex');
assert.throws(()=>buildNativeLibrary(s,r,m),/snapshot submission wrapper instruction differs/);
console.log('tampered current-recipe wrapper rejected');"""
  output=subprocess.check_output(['node','--input-type=module','-e',js,str(self.folder)],cwd=ROOT,text=True)
  self.assertIn('wrapper rejected',output)
