"""Distinct-slot regression: committed backend tone can precede frame SI tone.
Original Make/packers execute; OS/FS boundary and backend config are fixtures.
"""
import struct,unittest
from unicorn import UC_HOOK_CODE
from unicorn import arm_const as A
from tests import test_gr3_live_color_preview as live
from tests.test_gr3_isp_base import StockISP
from tests.test_gr3_isp_recipe_color import state
FILMS=(33,66,67,68,69)
BANKS=((0x140,0x152),(0x1c0,0x12b2),(0x2688,0x5088))
class SlotSwitchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):live.LiveColorPreviewTests.setUpClass.__func__(cls)
 cache=live.LiveColorPreviewTests.cache
 fixture=live.LiveColorPreviewTests.fixture
 def backend(self,e,tone):
  backend=e.alloc(0x51c);config=e.alloc(8);current=e.alloc(0x1040)
  e.w32(0x553458ac,1);e.w32(0x553458b0,backend)
  e.w32(backend,0x53d1a528);e.w32(backend+0x518,config);e.w32(config,current)
  e.u.mem_write(current+0x77c,bytes([tone]));return current
 def distinct(self,e):e.u.mem_write(0x550d1944,state(FILMS))
 def banks(self,e,frame):return tuple(bytes(e.u.mem_read(frame+a,b-a))for a,b in BANKS)
 def test_live_switch_uses_current_slot_before_frame_si_catches_up(self):
  # Real stage-1 Live Make/packers; stage-0 device backend is not emulated.
  for previous,current in ((12,18),(18,19),(19,20),(20,21),(21,12),(12,255)):
   with self.subTest(previous=previous,current=current):
    e=StockISP(self.candidate);self.cache(e,33);self.distinct(e);e.make(previous,1,True,actual_live=True)
    obj,frame=0x60000000,0x60001400;si=struct.unpack('<I',e.u.mem_read(frame+0x82d0,4))[0]
    self.backend(e,current);before=bytes(e.u.mem_read(si,0x80000))
    e.call(self.entry,obj,frame)
    ref=StockISP(self.candidate);self.cache(ref,33);self.distinct(ref);ref.make(current if current!=255 else previous,1,True,actual_live=True)
    ref.call(self.entry,obj,frame)
    self.assertEqual(self.banks(e,frame),self.banks(ref,frame))
    self.assertEqual(bytes(e.u.mem_read(si,0x80000)),before)
 def test_first_still_freezes_selected_slot_at_ingress_not_old_frame_or_later_ui(self):
  e=StockISP(self.candidate);recipe=e.alloc(0x50f0);e.w32(recipe,0x53d0fc90);e.w32(recipe+0x4778,0x31545653)
  obj=e.cursor;e.make(12,1);frame=obj+0x1400;si=struct.unpack('<I',e.u.mem_read(frame+0x82d0,4))[0]
  context=recipe+0x96c;e.w32(context+0x30,recipe+0x1a8);e.w32(context+0x34,si)
  current=self.backend(e,18);load=self.manifest['symbols']['m10v_camera_library_load']
  def fs(u,at,size,data):
   if at==load:u.mem_write(u.reg_read(A.UC_ARM_REG_R0),state(FILMS));u.reg_write(A.UC_ARM_REG_R0,0);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
  hook=e.u.hook_add(UC_HOOK_CODE,fs)
  exports=self.snapshot['exports'];e.call(exports['m10v_isp_frame_recipe_producer'],recipe);e.u.hook_del(hook)
  base=bytes(e.u.mem_read(frame,0x9000));e.u.mem_write(current+0x77c,bytes([21]))
  e.call(exports['m10v_isp_frame_recipe_producer'],recipe) # Re-entry cannot retarget an already queued shot.
  e.call(exports['m10v_isp_frame_recipe_begin'],context,obj,frame);e.call(0x536dd8f0,obj,frame);e.call(exports['m10v_isp_frame_recipe_finish'],context)
  st=e.alloc(104);e.u.mem_write(st,state(FILMS))
  e.call(exports['m10v_isp_frame_recipe_completed'],recipe,si,12,st);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),1)
  e.call(exports['m10v_isp_frame_recipe_completed'],recipe,si,18,st);self.assertEqual(e.u.reg_read(A.UC_ARM_REG_R0),0)
  actual=self.banks(e,frame);e.u.mem_write(frame,base)
  target=e.alloc(1600);gamma=struct.unpack('<I',e.u.mem_read(obj+0x17c,4))[0]
  e.call(exports['m10v_isp_native_look_prepare'],target,66,0,9);e.call(exports['m10v_isp_native_look_apply'],target,gamma,frame,0)
  self.assertEqual(actual,self.banks(e,frame))
  self.assertEqual(e.u.mem_read(si+0x71248+0x77c,1),bytes([12]))
 def test_cpu_fallback_uses_frozen_slot_when_native_color_is_unavailable(self):
  capture=live.capture
  capture.M10VCaptureTests.setUpClass();self.addCleanup(capture.M10VCaptureTests.doClassCleanups)
  c=capture.M10VCaptureTests();c.manifest=self.manifest;c.code=self.code;c.debug_manifest=self.manifest;c.debug_code=self.code
  results=[]
  for raw_tone,selected in ((12,18),(18,0)):
   h,u,context,y,uv,*_=c.fixture(tone=raw_tone,film=33,stamp=0,debug=True)
   recipe=context-0x9b8;u.mem_write(recipe,struct.pack('<I',0x53d0fc90));u.mem_write(recipe+0x4778,struct.pack('<I',0x31545653))
   u.mem_write(0x55002000,state(FILMS))
   h.manifest={**h.manifest,'symbols':{**h.manifest['symbols'],**self.snapshot['exports']}}
   self.assertEqual(h.call(u,'m10v_isp_frame_recipe_snapshot',recipe,0x55002000),1)
   u.mem_write(recipe+0x4a08+22,struct.pack('<H',selected))
   self.assertEqual(h.call(u,'m10v_capture_library',context),0)
   self.assertTrue(any(event[0]==110 and event[2]==1 and event[3]==66 for event in h.capture_events))
   results.append((bytes(u.mem_read(0x55010000,len(y))),bytes(u.mem_read(0x55020000,len(uv)))))
  self.assertEqual(*results)
