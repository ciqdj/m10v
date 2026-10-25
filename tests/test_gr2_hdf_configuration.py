"""UI-published HDF values are frozen without SD reads in capture workers."""
import struct,tempfile,unittest
from pathlib import Path
from tests import test_gr2_runtime_build as runtime_tests
from tests import test_gr2_capture as capture_tests
from tests.test_unity_update import component

class Gr2HdfConfigurationTests(unittest.TestCase):
    def test_ui_publishes_owned_values_only_after_pool_admission_and_each_frame_keeps_its_snapshot(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('gr2_hdf_configuration_publish',runtime['symbols']);self.assertIn('gr2_hdf_configuration_freeze',runtime['symbols'])
        self.assertIn('gr2_hdf_configuration_needs_bank0',runtime['symbols'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x51000000,0x60000)
        capture_tests.Gr2CaptureTests.owner_pool(self,u,extra=128+12288+16)
        contexts=[0x51000008+i*0x12ba4 for i in range(3)];out=0x50003000
        for context in contexts:u.mem_write(context-8,b'IMG '+bytes(4));u.mem_write(context,b'\xa5'*0x12b8c+bytes(16))
        calls=[];behavior={'busy':False}
        def kernel(uc,address,size,unused):
            calls.append(address)
            if address==0xa00665cc:
                self.assertEqual(bytes(uc.mem_read(uc.reg_read(r.UC_ARM_REG_R0),8)),bytes.fromhex('0002000000000000'));value=17
            elif address==0xa0066d94:
                self.assertEqual(uc.reg_read(r.UC_ARM_REG_R0),17);self.assertEqual(uc.reg_read(r.UC_ARM_REG_R1),0);value=-1 if behavior['busy'] else 0
            elif address==0xa00671b8:value=0
            else:self.fail('unexpected capture kernel or filesystem operation '+hex(address))
            uc.reg_write(r.UC_ARM_REG_R0,value&0xffffffff);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,kernel,begin=0xa0060000,end=0xa006ffff)
        call=lambda name,args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,runtime['symbols'][name],args)
        u.mem_write(out,b'\xa5'*8);self.assertEqual(call('gr2_hdf_configuration_read',[out,out+4]),0);self.assertEqual(calls,[])
        self.assertEqual(call('gr2_hdf_configuration_needs_bank0',[]),0)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[0]]),0);self.assertEqual(calls,[])
        u.mem_write(0xa0129c20,b'\x01');self.assertEqual(call('gr2_hdf_configuration_publish',[3,7]),0);self.assertEqual(calls,[])
        u.mem_write(0xa0129c20,b'\x00');self.assertEqual(call('gr2_hdf_configuration_publish',[3,7]),1)
        self.assertEqual(call('gr2_hdf_configuration_needs_bank0',[]),1)
        prefix=bytes(u.mem_read(contexts[0],0x12b8c));self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[0]]),1)
        first=bytes(u.mem_read(contexts[0]+0x12b8c,16));self.assertEqual(bytes(u.mem_read(contexts[0],0x12b8c)),prefix)
        self.assertEqual(call('gr2_hdf_configuration_publish',[1,8]),1)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[0]]),1);self.assertEqual(bytes(u.mem_read(contexts[0]+0x12b8c,16)),first)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[1]]),1)
        self.assertEqual(call('gr2_hdf_frame_read',[contexts[1],out]),1);self.assertEqual(struct.unpack('>2I',u.mem_read(out+4,8)),(0x10001,8))
        behavior['busy']=True;self.assertEqual(call('gr2_hdf_configuration_publish',[2,9]),0)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[0]]),1)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[2]]),0);self.assertEqual(bytes(u.mem_read(contexts[2]+0x12b8c,16)),bytes(16))
        behavior['busy']=False;u.mem_write(0xa0129c20,b'\x01')
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[2]]),0)
        self.assertEqual(call('gr2_hdf_configuration_publish',[0,10]),1);self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[2]]),1)
        self.assertEqual(call('gr2_hdf_configuration_needs_bank0',[]),0)
        self.assertEqual(call('gr2_hdf_frame_read',[contexts[2],out]),1);self.assertEqual(struct.unpack('>2I',u.mem_read(out+4,8)),(0x10000,10))
        self.assertEqual(call('gr2_hdf_configuration_publish',[4,11]),0)
        self.assertEqual(call('gr2_hdf_configuration_clear',[]),1)
        self.assertEqual(call('gr2_hdf_configuration_read',[out,out+4]),0)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[contexts[0]]),1)
        self.assertEqual(calls.count(0xa00665cc),1)

    def test_original_producer_freezes_hdf_independently_of_film_carriers_and_without_sd_reads(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import probe_producer_iq
        code=component('gr2','b01firm8');disk=component('gr2','b01firm6')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        for tone in (0,9):
            with self.subTest(tone=tone):
                result=probe_producer_iq(code,disk,native_runtime=runtime,tone=tone,active_configuration=True,hdf_configuration=(3,77))
                self.assertEqual(result['hdf_snapshot_valid'],1);self.assertEqual(result['hdf_snapshot_values'],[3,77])
                self.assertEqual(result['engine_mode'],0);self.assertEqual(result['restored_mode'],tone)
                self.assertEqual(result['hdf_filesystem_calls'],[]);self.assertTrue(result['stack_preserved'])
                self.assertEqual(result['snapshot_valid'],int(tone==9))

    def test_new_producer_epoch_refreshes_hdf_while_worker_freeze_keeps_queued_snapshot(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('gr2_hdf_configuration_begin',runtime['symbols'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x51000000,0x20000)
        capture_tests.Gr2CaptureTests.owner_pool(self,u,extra=128+12288+16);context=0x51000008
        u.mem_write(context-8,b'IMG '+bytes(4));u.mem_write(context,b'\xa5'*0x12b8c+bytes(16));prefix=bytes(u.mem_read(context,0x12b8c))
        def kernel(machine,address,size,unused):
            machine.reg_write(r.UC_ARM_REG_R0,17 if address==0xa00665cc else 0);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in (0xa00665cc,0xa0066d94,0xa00671b8):u.hook_add(UC_HOOK_CODE,kernel,begin=address,end=address)
        call=lambda name,args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,runtime['symbols'][name],args)
        for bank in (0,2,3,4):
            u.mem_write(0xa0129c20,bytes([bank]));self.assertEqual(call('gr2_hdf_configuration_publish',[1,10]),1)
            self.assertEqual(call('gr2_hdf_configuration_begin',[context]),1)
            self.assertEqual(call('gr2_hdf_configuration_publish',[3,11]),1)
            self.assertEqual(call('gr2_hdf_configuration_freeze',[context]),1)
            self.assertEqual(call('gr2_hdf_frame_read',[context,0x50003000]),1)
            self.assertEqual(struct.unpack('>2I',u.mem_read(0x50003004,8)),(0x10001,10))
            self.assertEqual(call('gr2_hdf_configuration_begin',[context]),1)
            self.assertEqual(call('gr2_hdf_frame_read',[context,0x50003000]),1)
            self.assertEqual(struct.unpack('>2I',u.mem_read(0x50003004,8)),(0x10003,11))
        self.assertEqual(call('gr2_hdf_configuration_clear',[]),1)
        self.assertEqual(call('gr2_hdf_configuration_begin',[context]),0)
        self.assertEqual(call('gr2_hdf_frame_read',[context,0x50003000]),1)
        self.assertEqual(struct.unpack('>2I',u.mem_read(0x50003004,8)),(0x10000,0))
        self.assertEqual(call('gr2_hdf_configuration_publish',[3,12]),1)
        self.assertEqual(call('gr2_hdf_configuration_freeze',[context]),1)
        self.assertEqual(call('gr2_hdf_frame_read',[context,0x50003000]),1)
        self.assertEqual(struct.unpack('>2I',u.mem_read(0x50003004,8)),(0x10000,0))
        self.assertEqual(bytes(u.mem_read(context,0x12b8c)),prefix)
