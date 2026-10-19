"""Actual packaged BIN, stock setup instructions, native completion and Live Make."""
import hashlib,json,os,subprocess,unittest
from pathlib import Path
from tests import test_gr3_native_recipe_handoff as native
from tests import test_gr3_live_color_preview as live

def delivered(cls):
 folder=Path(os.environ.get('M10V_SHARED_CANDIDATE','builds/gr3-v9-isp-hdf/final'))
 if not (folder/'fwdc239b.bin').exists():raise unittest.SkipTest('build combined candidate first')
 cls.manifest=json.loads((folder/'evidence/M10V-runtime-manifest.json').read_text())
 js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';let b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
 cls.candidate=subprocess.check_output(['node','--input-type=module','-e',js,str(folder/'fwdc239b.bin')])
 start=cls.manifest['base']-0x53000000;cls.code=cls.candidate[start:start+cls.manifest['code_bytes']]
 assert hashlib.sha256(cls.code).hexdigest()==cls.manifest['code_sha256']
 cls.rom=Path('builds/gr3-extension-validation/official-rtos.bin').read_bytes()
 cls.snapshot_manifest=cls.manifest['capture_lifecycle']['snapshot']

class DeliveredNativeTests(native.NativeRecipeHandoffTests):
 @classmethod
 def setUpClass(cls):
  delivered(cls);cls.manifest=cls.snapshot_manifest

class DeliveredLiveTests(live.LiveColorPreviewTests):
 @classmethod
 def setUpClass(cls):
  delivered(cls);cls.snapshot=cls.snapshot_manifest;cls.entry=cls.snapshot['patches'][3]['entry']

from tests import test_gr3_hdf_menu as hdfmenu
class DeliveredHdfMenuTests(hdfmenu.HdfMenuTests):
 @classmethod
 def setUpClass(cls):
  delivered(cls);cls.m=cls.manifest;cls.b=cls.code;cls.rom=cls.candidate
 def setUp(self):
  super().setUp();self.page=self.owner+self.m['hdf_menu']['owner_offset']
 def test_hdf_constructor_preserves_live_cache_and_film_page_ownership(self):
  self.call('m10v_hdf_menu_top_ctor',self.owner)
  self.assertEqual(self.get(self.owner+0x193c),0x3856504d)
  before=bytes(self.u.mem_read(self.owner+0x13bc,0x600+0x80))
  self.assertEqual(self.call('m10v_hdf_menu_ready',self.page,0),1)
  self.key(0xcf);self.key(0xd8)
  self.assertEqual(bytes(self.u.mem_read(self.owner+0x13bc,0x680)),before)
