"""Execute the real ARM SD adapter against subset cards and exact directory IDs."""
import struct,subprocess,unittest,gzip
import tests.test_gr3_sd_camera as support
ROOT=support.ROOT

class DirectorySDTests(unittest.TestCase):
 setUpClass=classmethod(support.SdCameraTests.setUpClass.__func__)
 setUp=support.SdCameraTests.setUp
 w=support.SdCameraTests.w
 n=support.SdCameraTests.n
 string=support.SdCameraTests.string
 hook=support.SdCameraTests.hook
 call=support.SdCameraTests.call

 def test_directory_mapping_uses_stock_identity_in_a_subset_card(self):
  self.card=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack([290,37,298]));"],cwd=ROOT)
  for index,expected in [(4,298),(7,37),(25,290),(0,0),(30,0),(255,0)]:
   self.assertEqual(self.call('m10v_sd_camera_directory_item',index),expected)
  self.assertEqual(self.call('m10v_sd_camera_item',32,0),0)
  self.assertEqual((self.opened,self.allocated),(0,0));self.assertEqual(self.calls,[])

 def test_5213_snapshot_and_journal_never_alias_another_sparse_film(self):
  self.assertEqual(self.call('m10v_sd_camera_directory_install',4,298,2),0)
  self.assertEqual(self.calls[0],('save','M10VS09.bin',12288))
  self.assertEqual(struct.unpack_from('<I',self.files['M10VS09.bin'],8)[0],298)
  self.card=b'';self.assertEqual(self.call('m10v_camera_library_load',0x5500a000),0)
  self.assertEqual(struct.unpack_from('<H',self.u.mem_read(0x5500a000,184),28)[0],298)
  self.assertEqual((self.opened,self.allocated),(0,0))

 def test_authentic_old_full_card_maps_only_requested_identities(self):
  self.card=gzip.decompress((ROOT/'tests/fixtures/gr3-pre-directory-films.m10.gz').read_bytes())
  for index,expected in [(0,33),(4,0),(5,77),(7,37),(25,290),(29,65)]:
   self.assertEqual(self.call('m10v_sd_camera_directory_item',index),expected)
  self.assertEqual(self.call('m10v_sd_camera_directory_install',4,298,2),0xffffffff)
  self.assertEqual(self.calls,[]);self.assertEqual((self.opened,self.allocated),(0,0))

 def test_stale_identity_corrupt_record_and_close_failure_do_not_save(self):
  self.assertEqual(self.call('m10v_sd_camera_directory_install',4,77,2),0xffffffff)
  card=bytearray(self.pack);card[4096+4*12288+80]^=1;self.card=bytes(card)
  self.assertEqual(self.call('m10v_sd_camera_directory_install',4,298,2),0xffffffff)
  self.card=self.pack;self.fail_close=True
  self.assertEqual(self.call('m10v_sd_camera_directory_install',4,298,2),0xffffffff)
  self.assertEqual((self.opened,self.allocated),(0,0));self.assertEqual(self.calls,[])

if __name__=='__main__':unittest.main()
