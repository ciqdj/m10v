"""GR II HDF coefficient preparation; not capture or pixel/DMA validation."""
import struct,tempfile,unittest
from pathlib import Path
from tests.test_unity_update import ROOT,component
from tests import test_gr2_runtime_build as runtime_tests

class Gr2HdfTests(unittest.TestCase):
    def test_native_coefficients_preserve_original_identity_and_apply_all_gr3_detail_gains_in_owned_scratch(self):
        self.assertTrue((ROOT/'native/gr2/m10v_hdf.c').is_file())
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        from scripts.build_gr3_digital_hdf import ROWS
        from unicorn import arm_const as r
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('gr2_hdf_prepare_bands',runtime['symbols'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x60000000,0x100000)
        base=0x60000020;capacity=0xe5800;start=0xe040;end=start+11*8192
        u.mem_write(base-32,b'\xa5'*(capacity+64));u.mem_write(0x50001000,struct.pack('>4I',*(base+8192*i for i in range(4))))
        call=lambda entry,args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,entry,args)
        call(0xa014d461,[0x50001000,0x50002000,0]);original=bytes(u.mem_read(base,capacity))
        identity=original[3*8192:4*8192];forward=struct.unpack('>2048H',identity[4096:])
        saved=[0x74560000+i for i in range(8)]
        for strength,row in enumerate(ROWS,1):
            with self.subTest(strength=strength):
                u.mem_write(base,original)
                for i,value in enumerate(saved):u.reg_write(r.UC_ARM_REG_R4+i,value)
                self.assertEqual(call(runtime['symbols']['gr2_hdf_prepare_bands'],[base,capacity,strength]),1)
                self.assertEqual([u.reg_read(r.UC_ARM_REG_R4+i) for i in range(8)],saved)
                self.assertEqual(u.reg_read(r.UC_ARM_REG_SP),0x50018000)
                result=bytes(u.mem_read(base,capacity))
                self.assertEqual(result[:start],original[:start]);self.assertEqual(result[end:],original[end:])
                for band,gain in enumerate(row):
                    expected=[0]*4096
                    for i,value in enumerate(forward):
                        value=value*gain//1024;expected[2048+i]=value
                        if i:expected[2048-i]=4096-value
                    expected[0]=expected[1]
                    self.assertEqual(result[start+band*8192:start+(band+1)*8192],struct.pack('>4096H',*expected))
                    if gain==1024:self.assertEqual(result[start+band*8192:start+(band+1)*8192],identity)
                self.assertEqual(bytes(u.mem_read(base-32,32))+bytes(u.mem_read(base+capacity,32)),b'\xa5'*64)
        for address,bytes_available,strength,result in ((0,0,0,0),(base,capacity,4,0xffffffff),(base+2,capacity,1,0xffffffff),(base,end-1,1,0xffffffff),(0xffffffe0,capacity,1,0xffffffff),(base,capacity+1,1,0xffffffff)):
            before=bytes(u.mem_read(base,capacity));self.assertEqual(call(runtime['symbols']['gr2_hdf_prepare_bands'],[address,bytes_available,strength]),result)
            self.assertEqual(bytes(u.mem_read(base,capacity)),before)
        for offset in (3*8192,3*8192+100,3*8192+4096,4*8192-2):
            u.mem_write(base,original);u.mem_write(base+offset,bytes([original[offset]^1]));before=bytes(u.mem_read(base,capacity))
            self.assertEqual(call(runtime['symbols']['gr2_hdf_prepare_bands'],[base,capacity,1]),0xffffffff)
            self.assertEqual(bytes(u.mem_read(base,capacity)),before)
