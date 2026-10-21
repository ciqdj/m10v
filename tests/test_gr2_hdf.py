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

    def test_independent_hdf_frame_snapshot_preserves_film_state_and_rejects_stale_or_corrupt_owners(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        from tests import test_gr2_capture as capture_tests
        import zlib
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('gr2_hdf_frame_freeze',runtime['symbols']);self.assertIn('gr2_hdf_frame_read',runtime['symbols'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x51000000,0x20000)
        context=0x51000008;offset=0x12b8c;body=offset+16;out=0x50003000
        capture_tests.Gr2CaptureTests.owner_pool(self,u,extra=128+12288+16)
        u.mem_write(context-8,b'IMG '+bytes(4));u.mem_write(context,b'\xa5'*offset+bytes(16));prefix=bytes(u.mem_read(context,offset))
        call=lambda name,args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,runtime['symbols'][name],args)
        for strength in range(4):
            u.mem_write(context+offset,bytes(16));sequence=0x12345678+strength
            self.assertEqual(call('gr2_hdf_frame_freeze',[context,strength,sequence]),1)
            self.assertEqual(bytes(u.mem_read(context,offset)),prefix)
            self.assertEqual(call('gr2_hdf_frame_read',[context,out]),1)
            raw=bytes(u.mem_read(out,16));self.assertEqual(struct.unpack('>4I',raw),(0x47324844,0x10000|strength,sequence,zlib.crc32(raw[:12])))
            self.assertEqual(call('gr2_hdf_frame_freeze',[context,(strength+1)%4,sequence+1]),0)
            self.assertEqual(bytes(u.mem_read(context+offset,16)),raw)
        before=bytes(u.mem_read(context,body))
        self.assertEqual(call('gr2_hdf_frame_freeze',[context,4,0]),0);self.assertEqual(bytes(u.mem_read(context,body)),before)
        self.assertEqual(call('gr2_hdf_frame_read',[context,context+offset]),0);self.assertEqual(bytes(u.mem_read(context,body)),before)
        u.mem_write(out,b'\xa5'*16);u.mem_write(context+offset+12,bytes(4))
        self.assertEqual(call('gr2_hdf_frame_read',[context,out]),0);self.assertEqual(bytes(u.mem_read(out,16)),b'\xa5'*16)
        u.mem_write(context+offset,bytes(16));u.mem_write(context-8,b'void')
        self.assertEqual(call('gr2_hdf_frame_freeze',[context,1,1]),0);self.assertEqual(bytes(u.mem_read(context+offset,16)),bytes(16))

    def test_original_image_factory_clones_and_retires_independent_hdf_snapshot_without_extra_references(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import probe_image_object_pools
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        result=probe_image_object_pools(code,extra=128+12288+16,native_runtime=runtime,hdf_snapshot=(3,7))
        self.assertEqual(result['native_owner_live'],[0x12b9c]*2)
        self.assertEqual(result['native_hdf_clone'],dict(freeze=1,read=1,matches=True))
        self.assertEqual(result['native_hdf_retired'],[0,0])
        self.assertTrue(result['constructor_zeroed']);self.assertTrue(result['all_blocks_released'])
        self.assertTrue(result['pools_within_linear_region']);self.assertTrue(result['pools_exclude_runtime'])
        self.assertEqual(result['pool_counts'],[60,91]);self.assertEqual(result['pool_block_bytes'],[0x12ba4,0x7f00])

    def test_original_clone_preserves_custom_lut_and_independent_hdf_in_the_same_image_owner(self):
        import subprocess
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import probe_image_object_pools
        record=subprocess.check_output(['node','--input-type=module','-e',"import {customFilmRecord} from './node/gr3-sd-film-pack.mjs';process.stdout.write(customFilmRecord({name:'HDF LUT',rgb:Buffer.from(Array.from({length:6591},(_,i)=>(i*7+83)%256))},79));"],cwd=ROOT)
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        result=probe_image_object_pools(code,extra=128+12288+16,native_runtime=runtime,custom_record=record,hdf_snapshot=(2,9))
        self.assertEqual(result['native_frame_clone'],dict(freeze=1,read=1,matches=True,custom_record_matches=True))
        self.assertEqual(result['native_hdf_clone'],dict(freeze=1,read=1,matches=True))
        self.assertEqual(result['native_hdf_retired'],[0,0]);self.assertTrue(result['all_blocks_released'])
