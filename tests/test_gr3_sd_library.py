"""Shared Node-produced bytes tested against independent native C validator."""
import ctypes as C
import json,subprocess,tempfile,unittest,zlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SdLibraryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
  out=Path(cls.tmp.name)/'sd.dylib'
  subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'native/gr3/m10v_sd_library.c'),'-o',str(out)],check=True,capture_output=True)
  cls.lib=C.CDLL(str(out));cls.lib.m10v_sd_header.argtypes=[C.c_void_p,C.c_uint32];cls.lib.m10v_sd_record.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32]
  cls.pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack());"],cwd=ROOT)
 def test_all_current_recipes_and_indices(self):
  self.assertEqual(self.lib.m10v_sd_header(self.pack[:4096],len(self.pack)),46)
  for i in range(46):
   id=struct.unpack_from('<I',self.pack,64+i*12)[0]
   r=self.pack[4096+i*12288:4096+(i+1)*12288]
   self.assertEqual(self.lib.m10v_sd_record(r,len(r),id),id)
   self.assertEqual(self.lib.m10v_sd_record(r,len(r),id+1),0)
 def test_repaired_crc_cannot_authorize_changed_recipe(self):
  for at in (16,64,80,116,1652,2048,9000):
   r=bytearray(self.pack[4096:4096+12288]);r[at]^=1;struct.pack_into('<I',r,12284,zlib.crc32(r[:-4]));self.assertEqual(self.lib.m10v_sd_record(bytes(r),len(r),33),0)
 def test_header_rejects_duplicates_reserved_fields_lengths_and_models(self):
  for at,val in [(8,2),(12,1),(16,0),(16,257),(20,1),(24,243),(28,2),(32,1),(64+12,33),(72,2)]:
   h=bytearray(self.pack[:4096]);struct.pack_into('<I',h,at,val);struct.pack_into('<I',h,4092,zlib.crc32(h[:-4]));self.assertEqual(self.lib.m10v_sd_header(bytes(h),len(self.pack)),0)
  self.assertEqual(self.lib.m10v_sd_header(self.pack[:4096],len(self.pack)-1),0)
 def test_null_and_short_record_inputs_rejected(self):
  self.assertEqual(self.lib.m10v_sd_header(None,0),0)
  for n in (0,1,12287,12289):self.assertEqual(self.lib.m10v_sd_record(None,n,33),0)
 def test_named_custom_lut_record_crosses_node_c_boundary(self):
  cube='LUT_3D_SIZE 2\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n0 0 1\n1 0 1\n0 1 1\n1 1 1\n'
  source="import {parseCustomCube} from './node/gr3-custom-lut.mjs';import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';const c=parseCustomCube(Buffer.from("+json.dumps(cube)+"),'identity.cube','My Film');process.stdout.write(buildSdFilmPack([],[c]));"
  pack=subprocess.check_output(['node','--input-type=module','-e',source],cwd=ROOT)
  record=pack[4096:]
  self.assertEqual(self.lib.m10v_sd_header(pack[:4096],len(pack)),1)
  self.assertEqual(self.lib.m10v_sd_record(record,len(record),79),79)
  damaged=bytearray(record);damaged[7000]^=1;struct.pack_into('<I',damaged,12284,zlib.crc32(damaged[:-4]))
  self.assertEqual(self.lib.m10v_sd_record(bytes(damaged),len(damaged),79),0)
 def test_previous_v1_builtin_record_remains_accepted(self):
  record=bytearray(self.pack[4096:4096+12288])
  record[8448:8480]=bytes.fromhex('52c0e9f5e8bc84b0430702ecd187c0a9dc816822f20ec8d5de670b9e97276d59')
  struct.pack_into('<I',record,12284,zlib.crc32(record[:-4]))
  self.assertEqual(self.lib.m10v_sd_record(bytes(record),len(record),33),33)
if __name__=='__main__':unittest.main()
