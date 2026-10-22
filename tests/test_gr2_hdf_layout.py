"""Cold-source pool selector hook must retain live r3 and the stock ABI."""
import struct,tempfile,unittest
from pathlib import Path
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2HdfLayoutTests(unittest.TestCase):
    def test_cold_selector_hook_preserves_all_arguments_and_uses_nonblocking_pool_hint(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('buffer_layout_hook_patch_hex',runtime)
        patch=bytes.fromhex(runtime['buffer_layout_hook_patch_hex']);self.assertEqual(len(patch),14)
        self.assertEqual(patch[:10],bytes.fromhex('b4084b01471846c046c0'))
        self.assertEqual(struct.unpack('>I',patch[10:])[0],runtime['symbols']['gr2_hdf_layout_chain'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));site=0xa00e5d92;original=bytes(u.mem_read(site,14))
        properties={};kernel=[]
        def boundary(uc,address,size,unused):
            if address==0xa00e0e2e:value=properties.get(uc.reg_read(r.UC_ARM_REG_R0),0)
            elif address==0xa00665cc:kernel.append(address);value=17
            elif address in (0xa0066d94,0xa00671b8):kernel.append(address);value=0
            else:self.fail('unexpected selector kernel call')
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,boundary,begin=0xa00e0e2e,end=0xa00e0e2e)
        u.hook_add(UC_HOOK_CODE,boundary,begin=0xa0060000,end=0xa006ffff)
        saved=[0x74560000+i for i in range(8)]
        def call(entry,args):
            for i,value in enumerate(saved):u.reg_write(r.UC_ARM_REG_R4+i,value)
            result=runtime_tests.Gr2RuntimeBuildTests.call(self,u,entry,args)
            self.assertEqual([u.reg_read(r.UC_ARM_REG_R4+i) for i in range(8)],saved);self.assertEqual(u.reg_read(r.UC_ARM_REG_SP),0x50018000)
            return result
        cases=[(6,(0,0,0),1,{}),(6,(0,0,0x12345678),4,{0x2d:16}),(7,(0,0,1),1,{}),(7,(0,0,2),1,{}),(7,(7,0,3),1,{}),(7,(0,0,3),1,{}),(5,(0,0,0),0,{1:2}),(10,(0,0,0),0,{})]
        for mode,args,current,values in cases:
            properties.clear();properties.update(values);u.mem_write(0xa0129c20,bytes([current]));before=dict(properties)
            u.mem_write(site,original);u.ctl_remove_cache(site,site+14);expected=call(site|1,[mode,*args])
            u.mem_write(site,patch);u.ctl_remove_cache(site,site+14);actual=call(site|1,[mode,*args])
            self.assertEqual(actual,expected);self.assertEqual(properties,before)
            if mode==7 and args[2] in (1,2):self.assertEqual(actual,2)
        self.assertEqual(kernel,[])
        u.mem_write(0xa0129c20,b'\x00');self.assertEqual(call(runtime['symbols']['gr2_hdf_configuration_publish'],[3,7]),1)
        kernel.clear();u.mem_write(0xa0129c20,b'\x01');properties.clear()
        self.assertEqual(call(site|1,[6,0,0,0]),0)
        self.assertEqual(call(site|1,[7,0,0,1]),2);self.assertEqual(call(site|1,[10,0,0,0]),4)
        self.assertEqual(kernel,[]);self.assertEqual(u.mem_read(0xa0129c20,1),b'\x01')

    def test_native_hdf_admission_uses_original_busy_manager_before_publishing_effective_setting(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('gr2_hdf_prepare_pool',runtime['symbols'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_write(0xa00e5d92,bytes.fromhex(runtime['buffer_layout_hook_patch_hex']))
        properties={0:6,0x2d:0};transitions=[];behavior={'ready':1}
        def boundary(uc,address,size,unused):
            a,b=[uc.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1)]
            if address==runtime['symbols']['gr2_ui_storage_ready']:value=behavior['ready']
            elif address==0xa00e0e2e:value=properties.get(a,0)
            elif address==0xa00e0c94:properties[a]=b;value=0
            elif address==0xa00df846:transitions.append(a);uc.mem_write(0xa0129c20,bytes([a]));value=0
            else:self.fail('unexpected HDF pool admission call')
            uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        for address in (runtime['symbols']['gr2_ui_storage_ready'],0xa00e0e2e,0xa00e0c94,0xa00df846):u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        call=lambda entry,args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,entry,args)
        for busy in (False,True):
            properties.clear();properties.update({0:6,0x2d:0,0x344:int(busy)});transitions.clear();u.mem_write(0xa0129c20,b'\x01')
            self.assertEqual(call(runtime['symbols']['gr2_hdf_prepare_pool'],[3]),int(not busy))
            self.assertEqual(transitions,[] if busy else [0]);self.assertEqual(u.mem_read(0xa0129c20,1),b'\x01' if busy else b'\x00')
            self.assertEqual(properties[0x25d],int(busy));self.assertEqual(properties[0x2d],0)
            self.assertEqual(call(runtime['symbols']['gr2_hdf_configuration_needs_bank0'],[]),0)
            u.mem_write(0xa0129c20,b'\x01');self.assertEqual(call(0xa00e5d93,[6,0,0,0]),1)
        transitions.clear();behavior['ready']=0
        self.assertEqual(call(runtime['symbols']['gr2_hdf_prepare_pool'],[3]),0);self.assertEqual(transitions,[])
        behavior['ready']=1;self.assertEqual(call(runtime['symbols']['gr2_hdf_prepare_pool'],[0]),1);self.assertEqual(transitions,[])

    def test_native_hdf_admission_executes_original_idle_pool_rebuild_in_the_single_reserved_arena(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import probe_buffer_pool_transitions
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        result=probe_buffer_pool_transitions(code,(0,),initial=1,native_runtime=runtime)
        self.assertEqual(result['layouts'],[1,0]);self.assertEqual(result['native_admission_return'],1)
        self.assertEqual(result['native_effective_hint'],0);self.assertEqual(result['linear_allocation_count'],2)
        self.assertTrue(result['constant_pools_preserved']);self.assertTrue(result['live_pool_identities_match'])
        self.assertTrue(result['ring_metadata_reclaimed']);self.assertTrue(result['all_live_spans_bounded'])
        self.assertTrue(result['stack_preserved']);self.assertTrue(result['callee_saved_preserved'])

    def test_original_layout_policy_admits_every_layout_with_two_jpeg_blocks(self):
        from scripts.build_gr2_runtime import build_gr2_runtime
        from scripts.analyze_gr2_native_contract import runtime_machine
        code=component('gr2','b01firm8')
        with tempfile.TemporaryDirectory() as folder:runtime=build_gr2_runtime(code,{},Path(folder))
        self.assertIn('gr2_hdf_layout_supports_graph',runtime['symbols'])
        u=runtime_machine(code);u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        for bank,expected in ((0,1),(1,0),(2,1),(3,1),(4,1),(5,0),(255,0)):
            u.mem_write(0xa0129c20,bytes([bank]))
            self.assertEqual(runtime_tests.Gr2RuntimeBuildTests.call(self,u,runtime['symbols']['gr2_hdf_layout_supports_graph'],[]),expected)
