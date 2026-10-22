"""Early reservation veneers retain live registers and replay stock branches."""
import struct,unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2HdfPreparationTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    def test_preparation_replays_all_displaced_instructions_after_clobbering_cache_call(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();u=runtime_machine(component('gr2','b01firm8'))
        u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x51000000,0x2000)
        context=0x51000000;u.mem_write(context+0x1e0,struct.pack('>I',0x12345678))
        site=0xa02ae7f6;row=next(row for row in runtime['hdf_graph_hooks'] if row['address']==site)
        original=bytes.fromhex(row['expected_hex']);calls=[]
        def cache(machine,address,size,unused):
            calls.append(machine.reg_read(r.UC_ARM_REG_R0));self.assertEqual(machine.reg_read(r.UC_ARM_REG_SP)&7,0)
            for index in (0,1,2,3,12):machine.reg_write(r.UC_ARM_REG_R0+index,0xdead0000+index)
            machine.reg_write(r.UC_ARM_REG_CPSR,(machine.reg_read(r.UC_ARM_REG_CPSR)&0x0fffffff)|0x90000000)
            machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        address=runtime['symbols']['gr2_hdf_configuration_begin'];u.hook_add(UC_HOOK_CODE,cache,begin=address,end=address)
        def execute(patch):
            u.mem_write(site,patch);u.ctl_remove_cache(site,site+14)
            u.reg_write(r.UC_ARM_REG_CPSR,0x60000233)
            for index in range(13):u.reg_write(r.UC_ARM_REG_R0+index,0x76540000+index)
            u.reg_write(r.UC_ARM_REG_R4,context);u.reg_write(r.UC_ARM_REG_SP,0x50018000);u.reg_write(r.UC_ARM_REG_LR,0x5001f001)
            u.emu_start(site|1,0xa02ae804,count=10000)
            self.assertEqual(u.reg_read(r.UC_ARM_REG_PC),0xa02ae804)
            return [u.reg_read(r.UC_ARM_REG_R0+i) for i in range(13)]+[u.reg_read(r.UC_ARM_REG_SP),u.reg_read(r.UC_ARM_REG_CPSR)]
        expected=execute(original);actual=execute(bytes.fromhex(row['patch_hex']))
        self.assertEqual(actual,expected);self.assertEqual(calls,[context])

    def test_reservation_dispatch_changes_only_r5_and_replays_original_compare(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();u=runtime_machine(component('gr2','b01firm8'))
        u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        for row in runtime['hdf_graph_hooks']:u.mem_write(row['address'],bytes.fromhex(row['patch_hex']))
        required=[0];calls=[]
        def admission(machine,address,size,unused):
            calls.append(machine.reg_read(r.UC_ARM_REG_R0))
            self.assertEqual(machine.reg_read(r.UC_ARM_REG_SP)&7,0)
            for index in (1,2,3,12):machine.reg_write(r.UC_ARM_REG_R0+index,0xdead0000+index)
            machine.reg_write(r.UC_ARM_REG_R0,required[0]);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        address=runtime['symbols']['gr2_hdf_reservation_required'];u.hook_add(UC_HOOK_CODE,admission,begin=address,end=address)
        def stop(machine,address,size,unused):
            if address in (0xa02ae842,0xa02ae87e):machine.emu_stop()
        u.hook_add(UC_HOOK_CODE,stop,begin=0xa02ae842,end=0xa02ae87e)
        for old in (0,1,7):
            for requested in (0,1):
                with self.subTest(old=old,requested=requested):
                    required[0]=requested;values=[0x76540000+i for i in range(13)];values[5]=old
                    u.reg_write(r.UC_ARM_REG_CPSR,0x60000233)
                    for index,value in enumerate(values):u.reg_write(r.UC_ARM_REG_R0+index,value)
                    u.reg_write(r.UC_ARM_REG_SP,0x50018000);u.reg_write(r.UC_ARM_REG_LR,0x5001f001)
                    u.emu_start(0xa02ae83f,0x5001f000,count=10000)
                    values[5]=1 if requested else old
                    self.assertEqual([u.reg_read(r.UC_ARM_REG_R0+i) for i in range(13)],values)
                    self.assertEqual(u.reg_read(r.UC_ARM_REG_PC),0xa02ae842 if values[5] else 0xa02ae87e)
                    self.assertEqual(u.reg_read(r.UC_ARM_REG_SP),0x50018000)
                    self.assertEqual(u.reg_read(r.UC_ARM_REG_CPSR)&0xf0000000,0x20000000 if values[5] else 0x60000000)
        self.assertEqual(calls,[0x76540004]*6)
