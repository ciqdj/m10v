"""UI-only HDF transactions reconcile journals before publishing capture state."""
import struct,unittest
from tests import test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import component

class Gr2HdfControlTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    def fixture(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();self.assertIn('gr2_hdf_reload',runtime['symbols']);self.assertIn('gr2_hdf_update',runtime['symbols'])
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        symbols=runtime['symbols'];events=[]
        behavior=dict(ready=1,initialize=1,load=1,prepare=1,write=1,persist=1,publish=1,disk=0,sequence=1)
        names=['gr2_ui_storage_ready','gr2_hdf_initialize_state','gr2_hdf_load_state','gr2_hdf_save_state','gr2_hdf_prepare_pool','gr2_hdf_configuration_publish','gr2_hdf_configuration_clear']
        addresses={symbols[name]:name for name in names}
        def boundary(machine,address,size,unused):
            a,b=[machine.reg_read(reg) for reg in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1)]
            if address in (0xa00665cc,0xa0066d94,0xa00671b8):value=17 if address==0xa00665cc else 0
            else:
                name=addresses[address];events.append([name,a] if name in ('gr2_hdf_save_state','gr2_hdf_prepare_pool','gr2_hdf_configuration_publish') else [name])
                if name=='gr2_ui_storage_ready':value=behavior['ready']
                elif name=='gr2_hdf_initialize_state':value=behavior['initialize']
                elif name=='gr2_hdf_load_state':
                    value=behavior['load']
                    if value:machine.mem_write(a,struct.pack('>I',behavior['disk']));machine.mem_write(b,struct.pack('>I',behavior['sequence']))
                elif name=='gr2_hdf_prepare_pool':
                    value=behavior['prepare']
                    if value and a:machine.mem_write(0xa0129c20,b'\x00')
                elif name=='gr2_hdf_save_state':
                    if behavior['persist']:behavior['disk']=a;behavior['sequence']+=1
                    value=behavior['write']
                elif name=='gr2_hdf_configuration_publish':
                    if behavior['publish']:return
                    value=0
                elif name=='gr2_hdf_configuration_clear':return
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in (*addresses,0xa00665cc,0xa0066d94,0xa00671b8):u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
        call=lambda name,*args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,symbols[name],list(args))
        def cache():
            if not call('gr2_hdf_configuration_read',0x50003000,0x50003004):return None
            return struct.unpack('>2I',u.mem_read(0x50003000,8))
        return behavior,events,call,cache

    def test_reload_prepares_original_pool_before_publishing_an_independent_journal(self):
        b,events,call,cache=self.fixture();b['disk']=3;b['sequence']=77
        self.assertEqual(call('gr2_hdf_reload'),1);self.assertEqual(cache(),(3,77))
        self.assertEqual(events,[['gr2_ui_storage_ready'],['gr2_hdf_initialize_state'],['gr2_hdf_load_state'],['gr2_hdf_prepare_pool',3],['gr2_hdf_configuration_publish',3]])
        self.assertEqual(call('gr2_hdf_configuration_needs_bank0'),1)
        for failure in ('ready','initialize','load','prepare','publish'):
            with self.subTest(failure=failure):
                b[failure]=0;events.clear();self.assertEqual(call('gr2_hdf_reload'),0);self.assertIsNone(cache())
                self.assertEqual(call('gr2_hdf_configuration_needs_bank0'),0)
                self.assertEqual(events[-1],['gr2_hdf_configuration_clear'])
                b[failure]=1;self.assertEqual(call('gr2_hdf_reload'),1)

    def test_update_reloads_actual_persisted_value_after_write_or_verification_failure(self):
        for write,persist,expected in ((1,1,3),(0,1,3),(0,0,0),(1,0,0)):
            with self.subTest(write=write,persist=persist):
                b,events,call,cache=self.fixture();self.assertEqual(call('gr2_hdf_reload'),1);events.clear()
                b.update(write=write,persist=persist)
                self.assertEqual(call('gr2_hdf_update',3),int(bool(write and persist)))
                self.assertEqual(cache(),(expected,2 if persist else 1))
                self.assertLess(events.index(['gr2_hdf_prepare_pool',3]),events.index(['gr2_hdf_save_state',3]))
                self.assertIn(['gr2_hdf_load_state'],events)
                self.assertEqual(events[-1],['gr2_hdf_configuration_publish',expected])

    def test_invalid_busy_unknown_media_and_failed_reconciliation_do_not_publish_unverified_values(self):
        b,events,call,cache=self.fixture();self.assertEqual(call('gr2_hdf_reload'),1);events.clear()
        self.assertEqual(call('gr2_hdf_update',4),0);self.assertEqual(events,[])
        for failure in ('ready','initialize','prepare'):
            b[failure]=0;events.clear();self.assertEqual(call('gr2_hdf_update',2),0)
            self.assertNotIn(['gr2_hdf_save_state',2],events);self.assertEqual(b['disk'],0);b[failure]=1
        for failure in ('load','publish'):
            b[failure]=0;events.clear();self.assertEqual(call('gr2_hdf_update',2),0);self.assertIsNone(cache())
            self.assertEqual(b['disk'],2);self.assertEqual(events[-1],['gr2_hdf_configuration_clear']);b[failure]=1
            self.assertEqual(call('gr2_hdf_reload'),1)

    def test_ui_restoration_waits_for_idle_and_retries_io_failures_on_owned_menu_keys(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();symbols=runtime['symbols'];self.assertIn('gr2_hdf_ui_bootstrap',symbols)
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        behavior=dict(ready=0,busy=0,reload=0);events=[]
        def backend(machine,address,size,unused):
            if address==symbols['gr2_ui_storage_ready']:value=behavior['ready'];events.append('ready')
            elif address==0xa00e0e2e:
                self.assertEqual(machine.reg_read(r.UC_ARM_REG_R0),0x344);value=behavior['busy'];events.append('busy')
            else:value=behavior['reload'];events.append('reload')
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in (symbols['gr2_ui_storage_ready'],symbols['gr2_hdf_reload'],0xa00e0e2e):u.hook_add(UC_HOOK_CODE,backend,begin=address,end=address)
        def event(key):
            u.mem_write(0x50003000,struct.pack('>3I',key,0,0))
            return runtime_tests.Gr2RuntimeBuildTests.call(self,u,symbols['gr2_hdf_ui_bootstrap'],[0x50003000])
        self.assertEqual(event(0x60000003),0);self.assertEqual(events,['ready']);events.clear()
        behavior.update(ready=1,busy=1);self.assertEqual(event(0x60000003),0);self.assertEqual(events,['ready','busy']);events.clear()
        behavior['busy']=0;self.assertEqual(event(0x60000003),0);self.assertEqual(events,['ready','busy','reload']);events.clear()
        self.assertEqual(event(0x60000003),0);self.assertEqual(events,[])
        behavior['reload']=1;self.assertEqual(event(0x6000100a),1);self.assertEqual(events,['ready','busy','reload']);events.clear()
        self.assertEqual(event(0x60000003),1);self.assertEqual(events,[])
