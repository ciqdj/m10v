"""Re-extract the delivered firmware and compare capture pixels with scalar.

This executes ARM with substituted camera services; it does not execute ISP
pixels, SD hardware or prove on-camera performance/save completion.
"""
import argparse,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests import test_gr3_capture_profile as profile
from tests import test_gr3_m10v_capture as capture
from tests import test_gr3_capture_released_raw as retired
from tests import test_gr3_native_recipe_handoff as native
from scripts.build_gr3_m10v_library import build
from unicorn.arm_const import UC_ARM_REG_C1_C0_2,UC_ARM_REG_FPEXC

def verify(folder):
 folder=Path(folder).resolve()
 class DeliveredTests(profile.CaptureProfileTests):
  @classmethod
  def setUpClass(cls):
   capture.M10VCaptureTests.setUpClass();cls.addClassCleanup(capture.M10VCaptureTests.doClassCleanups)
   cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
   manifest=json.loads((folder/'M10V-runtime-manifest.json').read_text())
   js="import {readFileSync} from 'node:fs';import {decodeFrameMap} from './node/gr3-frames.mjs';let b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
   rtos=subprocess.check_output(['node','--input-type=module','-e',js,str(folder/'fwdc239b.bin')],cwd=ROOT)
   start=manifest['base']-0x53000000;code=rtos[start:start+manifest['code_bytes']]
   assert hashlib.sha256(code).hexdigest()==manifest['code_sha256']
   experimental=manifest['experimental_capture']
   assert {k:experimental[k] for k in ('candidate_color','spatial_neon','full_isp_effects','save_chain_fixed')}=={'candidate_color':True,'spatial_neon':True,'full_isp_effects':False,'save_chain_fixed':False}
   assert set(experimental)<=set(('candidate_color','spatial_neon','full_isp_effects','save_chain_fixed','texture_neon','native_color','native_grain'))
   normaldir=Path(cls.tmp.name)/'scalar'
   normal=build(normaldir,base=manifest['base'],initial_state_hex=manifest['initial_state_hex'],sd_library=True,debug_mode=True,candidate_color=True)
   capture.M10VCaptureTests.manifest=normal;capture.M10VCaptureTests.code=(normaldir/'m10v-library-arm.bin').read_bytes()
   cls.manifest=manifest;cls.code=code
  def fixture(self,*a,**k):
   result=super().fixture(*a,**k);u=result[1]
   u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
   return result
 class DeliveredRetiredTests(retired.CaptureReleasedRawTests):
  @classmethod
  def setUpClass(cls):
   capture.M10VCaptureTests.setUpClass();cls.addClassCleanup(capture.M10VCaptureTests.doClassCleanups)
   cls.manifest=DeliveredTests.manifest;cls.code=DeliveredTests.code
  def fixture(self,*a,**k):
   result=super().fixture(*a,**k);u=result[1]
   u.reg_write(UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
   # Delivered firmware enables profiling. Keep the official clock facade
   # executable and substitute only its unavailable kernel SVC, just as the
   # delivered profile fixture does; effects and RAW token execute unchanged.
   import struct
   from unicorn import UC_HOOK_INTR
   from unicorn import arm_const as A
   page=0x53050000
   if not any(lo<=page<=hi for lo,hi,_ in u.mem_regions()):u.mem_map(page,4096)
   u.mem_write(page,capture.M10VCaptureTests.official[0x50000:0x51000])
   ticks=[0xffffff00]
   def clock(uc,number,data):
    self.assertEqual(uc.reg_read(A.UC_ARM_REG_PC),0x53050b90)
    self.assertEqual(uc.reg_read(A.UC_ARM_REG_R12),0x80510100)
    ticks[0]+=100
    uc.mem_write(uc.reg_read(A.UC_ARM_REG_R0),struct.pack('<II',ticks[0]>>32,ticks[0]&0xffffffff))
    uc.reg_write(A.UC_ARM_REG_R0,0)
   u.hook_add(UC_HOOK_INTR,clock)
   return result
 suite=unittest.TestSuite(DeliveredTests(name) for name in ('test_timing_is_stack_owned_and_flushes_once_after_pixels_changed','test_clock_failure_cannot_suppress_image_processing','test_profile_pixels_match_release_for_all_reported_films'))
 class DeliveredNativeTests(native.NativeRecipeHandoffTests):
  @classmethod
  def setUpClass(cls):
   manifest=json.loads((folder/'M10V-runtime-manifest.json').read_text())
   js="import {readFileSync} from 'node:fs';import {decodeFrameMap} from './node/gr3-frames.mjs';let b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
   cls.candidate=subprocess.check_output(['node','--input-type=module','-e',js,str(folder/'fwdc239b.bin')],cwd=ROOT)
   cls.manifest=manifest['capture_lifecycle']['snapshot']
 if json.loads((folder/'M10V-runtime-manifest.json').read_text()).get('experimental_capture',{}).get('native_color'):
  suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(DeliveredNativeTests))
 if json.loads((folder/'M10V-runtime-manifest.json').read_text()).get('capture_lifecycle',{}).get('raw_lifetime_attestation'):
  suite.addTests(DeliveredRetiredTests(name) for name in ('test_native_release_matches_every_live_capture_yuv_byte_without_raw_metadata_or_fallback_reads','test_unproved_null_failed_pool_foreign_si_and_new_setter_reject_without_pixel_changes'))
 return unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();raise SystemExit(not verify(a.folder))
