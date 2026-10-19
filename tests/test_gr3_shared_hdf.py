"""Delivered native color/live preview/HDF must share one allocator and hooks."""
import hashlib,json,os,struct,subprocess,unittest
from pathlib import Path
from tests import test_gr3_digital_hdf as prior
class SharedHdfTests(prior.HdfExecutionTests):
 @classmethod
 def setUpClass(cls):
  folder=Path(os.environ.get('M10V_SHARED_CANDIDATE','builds/gr3-v9-isp-hdf/final'))
  if not (folder/'fwdc239b.bin').exists():raise unittest.SkipTest('build combined candidate first')
  cls.manifest=json.loads((folder/'evidence/M10V-runtime-manifest.json').read_text())
  js="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';let b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
  rom=subprocess.check_output(['node','--input-type=module','-e',js,str(folder/'fwdc239b.bin')])
  start=cls.manifest['base']-0x53000000
  cls.runtime=rom[start:start+cls.manifest['code_bytes']]
  assert hashlib.sha256(cls.runtime).hexdigest()==cls.manifest['code_sha256']
 def test_official_preimage_and_native_hdf_are_installed_together(self):
  h=self.manifest['digital_hdf'];self.assertTrue(h['shared_recipe'])
  self.assertEqual(h['shared_offset'],0x50e4);self.assertEqual(len(h['patches']),3)
  self.assertEqual(self.manifest['hdf_menu']['owner_offset'],0x19bc)
  self.assertTrue(self.manifest['capture_lifecycle']['snapshot']['shared_hdf'])
  addresses=[p['address'] for p in h['patches']+self.manifest['capture_lifecycle']['patches']]
  self.assertEqual(len(addresses),len(set(addresses)))
 def test_hdf_snapshot_does_not_overwrite_raw_or_color_state(self):
  e=self.machine(3);u=e['u'];r=e['recipe']
  raw=bytes(u.mem_read(r+0x50c0,36));color=bytes(u.mem_read(r+0x4a08,1716))
  self.produce(e);self.gate(e);self.settings(e,False);self.settings(e,True)
  self.assertEqual(bytes(u.mem_read(r+0x50c0,36)),raw)
  self.assertEqual(bytes(u.mem_read(r+0x4a08,1716)),color)
  self.assertEqual(struct.unpack('<3I',u.mem_read(r+0x50e4,12)),(1,3,e['si']))
 def test_hdf_and_requested_native_grain_share_both_settings_stages(self):
  import zlib
  from tests.test_gr3_isp_recipe_color import state
  e=self.machine(2);u=e['u'];r=e['recipe'];data=bytearray(state((67,)*5));data[14]=2
  struct.pack_into('<I',data,100,zlib.crc32(data[:100]));at=0x57003000;u.mem_write(at,bytes(data))
  self.assertEqual(self.call(e,self.manifest['symbols']['m10v_isp_frame_recipe_snapshot'],r,at),1)
  self.produce(e);self.gate(e)
  # A rejected grain execution must still enable the valid independent HDF.
  self.assertEqual(self.settings(e,True)[1:3],(6,0))
  plan=self.settings(e,False);execution=self.settings(e,True)
  self.assertEqual(plan,execution);self.assertEqual(plan[1:3],(6,2))
