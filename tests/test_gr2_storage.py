"""Common SD bytes must remain little endian on the GR II big-endian CPU."""
import struct
import unittest
import zlib
from tests import test_gr2_runtime_build as runtime_tests

class Gr2StorageTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    call=runtime_tests.Gr2RuntimeBuildTests.call
    def test_state_codec_crosses_native_endian_and_refuses_corrupt_payload_atomically(self):
        report=self.build();self.assertIn('gr2_state_encode',report['symbols']);u=self.machine(report)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000])
        self.assertEqual(self.call(u,report['symbols']['gr2_state_encode'],[0x50001000,0x50002000]),1)
        expected=bytearray(104);struct.pack_into('<IHHI',expected,0,0x5630314d,4,104,0)
        for i in range(5):
            struct.pack_into('<H6B',expected,12+i*8,33 if i==4 else i+34,0,0,3,3,5,2)
            expected[56+i*8]=1;expected[59+i*8]=4
        struct.pack_into('<I',expected,100,zlib.crc32(expected[:100]))
        self.assertEqual(bytes(u.mem_read(0x50002000,104)),bytes(expected))
        self.assertEqual(self.call(u,report['symbols']['gr2_state_decode'],[0x50002000,0x50003000]),1)
        self.assertEqual(bytes(u.mem_read(0x50003000,104)),bytes(u.mem_read(0x50001000,104)))
        for offset,repair in ((12,False),(12,True),(96,True)):
            corrupt=bytearray(expected);corrupt[offset]=255
            if repair:struct.pack_into('<I',corrupt,100,zlib.crc32(corrupt[:100]))
            u.mem_write(0x50002000,bytes(corrupt));u.mem_write(0x50003000,b'\xa5'*104)
            self.assertEqual(self.call(u,report['symbols']['gr2_state_decode'],[0x50002000,0x50003000]),0)
            self.assertEqual(bytes(u.mem_read(0x50003000,104)),b'\xa5'*104)

    def test_existing_sd_pack_and_recipe_hashes_execute_on_big_endian_cpu(self):
        import subprocess
        from tests.test_unity_update import ROOT
        report=self.build();u=self.machine(report)
        pack=subprocess.check_output(['node','--input-type=module','-e',"import {buildSdFilmPack} from './node/gr3-sd-film-pack.mjs';process.stdout.write(buildSdFilmPack());"],cwd=ROOT)
        u.mem_write(0x50001000,pack[:4096])
        self.assertEqual(self.call(u,report['symbols']['m10v_sd_header'],[0x50001000,len(pack)]),46)
        for i in range(46):
            identity=struct.unpack_from('<I',pack,64+i*12)[0];record=pack[4096+i*12288:4096+(i+1)*12288]
            u.mem_write(0x50002000,record)
            with self.subTest(identity=identity):self.assertEqual(self.call(u,report['symbols']['m10v_sd_record'],[0x50002000,len(record),identity]),identity)
        corrupt=bytearray(pack[4096:4096+12288]);corrupt[80]^=1;struct.pack_into('<I',corrupt,12284,zlib.crc32(corrupt[:-4]));u.mem_write(0x50002000,bytes(corrupt))
        self.assertEqual(self.call(u,report['symbols']['m10v_sd_record'],[0x50002000,12288,33]),0)
