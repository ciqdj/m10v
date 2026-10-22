"""Queued capture consumes its own validated snapshot, not a later UI edit."""
import struct,tempfile,unittest
from pathlib import Path
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_capture as capture

class CaptureSnapshotTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  capture.M10VCaptureTests.setUpClass();cls.addClassCleanup(capture.M10VCaptureTests.doClassCleanups)
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  cls.manifest=build(Path(cls.tmp.name),debug_mode=True,lifecycle_trace=True,recipe_snapshot=True)
  cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()
 def run_capture(self,queued,matching=True):
  fixture=capture.M10VCaptureTests()
  if queued:fixture.debug_manifest=self.manifest;fixture.debug_code=self.code
  h,u,context,y,uv,*_=fixture.fixture(film=35,raw=1,raw_bank=0xa3000000,debug=True,stamp=0)
  if queued:
   recipe=context-0x9b8;u.mem_write(recipe,struct.pack('<I',0x53d0fc90))
   h.call(u,'m10v_save_trace_init',recipe+0x4778)
   self.assertEqual(h.call(u,'m10v_isp_frame_recipe_snapshot',recipe,0x55001000),1)
   u.mem_write(recipe+0x4a08+12,struct.pack('<I',7))
   u.mem_write(recipe+0x4a08+20,struct.pack('<II',18,0x55078000 if matching else 0x55078100))
   self.assertEqual(h.call(u,'m10v_camera_library_select',0x55001000,1,66),0)
   h.file_calls.clear()
  self.assertEqual(h.call(u,'m10v_capture_library',context),0)
  return bytes(u.mem_read(0x55010000,len(y))),bytes(u.mem_read(0x55020000,len(uv))),h.capture_events,h.file_calls
 def test_owned_selection_survives_stock_carrier_lag_at_encoder(self):
  fixture=capture.M10VCaptureTests();fixture.debug_manifest=self.manifest;fixture.debug_code=self.code
  h,u,context,y,uv,*_=fixture.fixture(film=35,raw=1,raw_bank=0xa3000000,debug=True,stamp=0)
  recipe=context-0x9b8;u.mem_write(recipe,struct.pack('<I',0x53d0fc90))
  h.call(u,'m10v_save_trace_init',recipe+0x4778)
  self.assertEqual(h.call(u,'m10v_isp_frame_recipe_snapshot',recipe,0x55001000),1)
  # UI film was committed for this exposure, but the backend SI still says Standard.
  u.mem_write(recipe+0x4a08+22,struct.pack('<H',18))
  u.mem_write(0x55078000+0x77c,b'\x0b');h.file_calls.clear()
  self.assertEqual(h.call(u,'m10v_capture_library',context),0)
  self.assertEqual(h.file_calls,[])
  self.assertEqual((bytes(u.mem_read(0x55010000,len(y))),bytes(u.mem_read(0x55020000,len(uv)))),self.run_capture(False)[:2])

 def test_stock_carrier_without_valid_owned_custom_selection_stays_untouched(self):
  for bad in ('vptr','trace','crc','stock_selection','missing_selection'):
   fixture=capture.M10VCaptureTests();fixture.debug_manifest=self.manifest;fixture.debug_code=self.code
   h,u,context,y,uv,*_=fixture.fixture(film=35,raw=1,raw_bank=0xa3000000,debug=True,stamp=0)
   recipe=context-0x9b8;u.mem_write(recipe,struct.pack('<I',0x53d0fc90));h.call(u,'m10v_save_trace_init',recipe+0x4778)
   self.assertEqual(h.call(u,'m10v_isp_frame_recipe_snapshot',recipe,0x55001000),1)
   u.mem_write(recipe+0x4a08+22,struct.pack('<H',18));u.mem_write(0x55078000+0x77c,b'\x0b')
   if bad=='vptr':u.mem_write(recipe,bytes(4))
   elif bad=='trace':u.mem_write(recipe+0x4778,bytes(4))
   elif bad=='crc':
    at=recipe+0x4a08+1712;u.mem_write(at,bytes([u.mem_read(at,1)[0]^1]))
   else:u.mem_write(recipe+0x4a08+22,struct.pack('<H',11 if bad=='stock_selection' else 0))
   h.file_calls.clear();self.assertEqual(h.call(u,'m10v_capture_library',context)&0xffffffff,0xfffffffc,bad)
   self.assertEqual(h.file_calls,[],bad);self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(y),bad)

 def test_later_selected_film_cannot_change_already_queued_frame(self):
  baseline=self.run_capture(False);queued=self.run_capture(True)
  self.assertEqual(queued[:2],baseline[:2])
  self.assertEqual([e[2] for e in queued[2]if e[0]==113],[4])
  self.assertEqual(queued[3],[])
 def test_foreign_shooting_identity_uses_own_snapshot_and_full_software_fallback(self):
  result=self.run_capture(True,matching=False)
  # Native completion identity can fail without invalidating the queued
  # configuration. Loading the newer UI choice here would color the old shot
  # with the next shot's film. Render its original film entirely in software.
  self.assertEqual(result[:2],self.run_capture(False)[:2])
  self.assertEqual([e[2] for e in result[2]if e[0]==113],[4])
  self.assertEqual(result[3],[])
