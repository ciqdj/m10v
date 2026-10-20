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

    def test_dual_journal_recovery_readback_and_sequence_wrap(self):
        from unicorn import UC_HOOK_CODE,arm_const as r
        report=self.build();self.assertIn('gr2_journal_load',report['symbols']);u=self.machine(report)
        files={};behavior={'short_write':False,'bad_readback':False};events=[]
        read_address=0x5001d000;write_address=0x5001d004
        u.mem_write(0x50000000,struct.pack('>2I',read_address,write_address))
        def io(uc,address,size,context):
            path=bytes(uc.mem_read(uc.reg_read(r.UC_ARM_REG_R0),32)).split(b'\0',1)[0].decode()
            buffer=uc.reg_read(r.UC_ARM_REG_R1);count=uc.reg_read(r.UC_ARM_REG_R2)
            if address==read_address:
                payload=files.get(path,b'')[:count]
                if behavior['bad_readback'] and payload:payload=bytes([payload[0]^1])+payload[1:]
                uc.mem_write(buffer,payload);value=len(payload);events.append(('read',path,count))
            else:
                payload=bytes(uc.mem_read(buffer,count));value=29 if behavior['short_write'] else count
                files[path]=payload[:value];events.append(('write',path,count))
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,io,begin=read_address,end=write_address)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000])
        self.call(u,report['symbols']['gr2_state_encode'],[0x50001000,0x50002000]);base=bytearray(u.mem_read(0x50002000,104))
        def wire(sequence):
            value=bytearray(base);struct.pack_into('<I',value,8,sequence);struct.pack_into('<I',value,100,zlib.crc32(value[:100]));return bytes(value)
        a='H:/M10V5A.bin';b='H:/M10V5B.bin';files[a]=wire(10);files[b]=wire(11)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50003000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50003008,4))[0],11)
        files[b]=wire(11)+b'!'
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50003000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50003008,4))[0],10)
        files[b]=wire(11);u.mem_write(0x50002000,wire(12));self.call(u,report['symbols']['gr2_state_decode'],[0x50002000,0x50003000])
        behavior['short_write']=True
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),0)
        self.assertEqual(files[b],wire(11))
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50004008,4))[0],11)
        behavior['short_write']=False
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),1)
        self.assertEqual(files[a],wire(12))
        behavior['bad_readback']=True
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_store'],[0x50000000,0x50003000]),0)
        behavior['bad_readback']=False
        files[a]=wire(0);files[b]=wire(0xffffffff)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),1)
        self.assertEqual(struct.unpack('>I',u.mem_read(0x50004008,4))[0],0)
        files.clear();u.mem_write(0x50004000,b'\xa5'*104)
        self.assertEqual(self.call(u,report['symbols']['gr2_journal_load'],[0x50000000,0x50004000]),0)
        self.assertEqual(bytes(u.mem_read(0x50004000,104)),b'\xa5'*104)

    def test_compiled_file_bridge_closes_and_frees_its_own_metadata_on_short_write_and_close_error(self):
        from scripts.analyze_gr2_native_contract import probe_sd_file_lifecycle
        from tests.test_unity_update import component
        report=self.build();self.assertIn('gr2_file_read',report['symbols'])
        for write_error,close_error,written,read in ((False,False,104,104),(True,False,0xffffffff,29),(False,True,0xffffffff,0xffffffff)):
            with self.subTest(write_error=write_error,close_error=close_error):
                result=probe_sd_file_lifecycle(component('gr2','b01firm8'),native_runtime=report,fail_write=write_error,fail_close=close_error)
                self.assertEqual(result['write_returned'],written);self.assertEqual(result['read_returned'],read)
                self.assertEqual(result['backend_close_calls'],2);self.assertEqual(result['metadata_free_calls'],2)
                self.assertTrue(result['magic_cleared_before_free'])
