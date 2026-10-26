"""Current-main SD record preservation through the actual C authenticator."""
import ctypes as C
import json
import subprocess
import tempfile
import unittest
import zlib
import struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UniversalHalationSdTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        out=Path(cls.tmp.name)/'sd.dylib'
        subprocess.run(['clang','-O2','-Wall','-Wextra','-Werror','-dynamiclib',str(ROOT/'native/gr3/m10v_sd_library.c'),'-o',str(out)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(out));cls.lib.m10v_sd_record.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32]
        cls.contract=json.loads((ROOT/'node/gr3-sd-pre-universal-halation-contract.json').read_text())
        js="import{sdFilmRecord}from'./node/gr3-sd-film-pack.mjs';import{readFileSync}from'node:fs';const c=JSON.parse(readFileSync('node/gr3-sd-pre-universal-halation-contract.json'));process.stdout.write(Buffer.concat(c.ids.map(sdFilmRecord)));"
        cls.records=subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT)
    def test_all_current_and_pre_feature_builtin_records_are_authenticated(self):
        import hashlib
        for i,id in enumerate(self.contract['ids']):
            r=bytearray(self.records[i*12288:(i+1)*12288]);self.assertEqual(self.lib.m10v_sd_record(bytes(r),12288,id),id)
            r[8448:8480]=bytes.fromhex(self.contract['renderer']);struct.pack_into('<I',r,12284,zlib.crc32(r[:-4]))
            self.assertEqual(hashlib.sha256(r).hexdigest(),self.contract['hashes'][i]);self.assertEqual(self.lib.m10v_sd_record(bytes(r),12288,id),id)
            r[64]^=1;struct.pack_into('<I',r,12284,zlib.crc32(r[:-4]));self.assertEqual(self.lib.m10v_sd_record(bytes(r),12288,id),0)
if __name__=='__main__':unittest.main()
