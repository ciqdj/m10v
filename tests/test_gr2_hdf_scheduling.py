"""Scheduling snapshots precede thumbnail decisions and survive UI publication."""
import struct,unittest,zlib
from tests import test_gr2_runtime_build as runtime_tests
from tests import test_gr2_capture as capture_tests
from tests.test_unity_update import component

class Gr2HdfSchedulingTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    def fixture(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();required={'gr2_hdf_configuration_policy','gr2_hdf_configuration_prepare'}
        self.assertTrue(required<=runtime['symbols'].keys(),'scheduling snapshot helpers missing')
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']));u.mem_map(0x51000000,0x40000)
        capture_tests.Gr2CaptureTests.owner_pool(self,u,extra=128+12288+16)
        contexts=[0x51000008+i*0x12ba4 for i in range(3)]
        for context in contexts:u.mem_write(context-8,b'IMG '+bytes(4));u.mem_write(context,b'\xa5'*0x12b8c+bytes(16))
        calls=[];behavior={'busy':False}
        def kernel(machine,address,size,unused):
            calls.append(address)
            if address==0xa00665cc:value=17
            elif address==0xa0066d94:
                self.assertEqual(machine.reg_read(r.UC_ARM_REG_R0),17);self.assertEqual(machine.reg_read(r.UC_ARM_REG_R1),0)
                value=-1 if behavior['busy'] else 0
            elif address==0xa00671b8:value=0
            else:self.fail('unexpected scheduling I/O/service '+hex(address))
            machine.reg_write(r.UC_ARM_REG_R0,value&0xffffffff);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,kernel,begin=0xa0060000,end=0xa006ffff)
        call=lambda name,*args:runtime_tests.Gr2RuntimeBuildTests.call(self,u,runtime['symbols'][name],list(args))
        def frame(context):
            self.assertEqual(call('gr2_hdf_frame_read',context,0x50003000),1)
            return list(struct.unpack('>4I',u.mem_read(0x50003000,16)))
        return u,contexts,behavior,calls,call,frame

    def test_parent_and_sibling_share_one_scheduling_snapshot_then_consume_it_independently(self):
        u,contexts,b,calls,call,frame=self.fixture();parent,child,other=contexts
        prefixes=[bytes(u.mem_read(c,0x12b8c)) for c in contexts]
        self.assertEqual(call('gr2_hdf_configuration_publish',1,10),1)
        self.assertEqual(call('gr2_hdf_configuration_policy',parent,child),1)
        self.assertEqual(frame(parent),frame(child));self.assertEqual(frame(parent)[1:3],[0x30001,10])
        self.assertEqual(call('gr2_hdf_configuration_publish',3,11),1);before=len(calls)
        self.assertEqual(call('gr2_hdf_configuration_prepare',parent),1)
        self.assertEqual(frame(parent)[1:3],[0x10001,10]);self.assertEqual(frame(child)[1:3],[0x30001,10])
        self.assertEqual(call('gr2_hdf_configuration_prepare',child),1)
        self.assertEqual(frame(child)[1:3],[0x10001,10]);self.assertEqual(len(calls),before)
        self.assertEqual(call('gr2_hdf_configuration_freeze',parent),1);self.assertEqual(frame(parent)[1:3],[0x10001,10])
        self.assertEqual(call('gr2_hdf_configuration_prepare',parent),1)
        self.assertEqual(frame(parent)[1:3],[0x10003,11]);self.assertEqual(frame(child)[1:3],[0x10001,10])
        for context,prefix in zip(contexts,prefixes):self.assertEqual(bytes(u.mem_read(context,0x12b8c)),prefix)

    def test_off_or_unavailable_policy_cannot_adopt_a_later_on_value_before_reservation(self):
        u,contexts,b,calls,call,frame=self.fixture();parent,child,_=contexts
        self.assertEqual(call('gr2_hdf_configuration_publish',0,20),1)
        self.assertEqual(call('gr2_hdf_configuration_policy',parent,child),1)
        self.assertEqual(call('gr2_hdf_configuration_publish',3,21),1)
        for context in (parent,child):
            self.assertEqual(call('gr2_hdf_configuration_prepare',context),1);self.assertEqual(frame(context)[1:3],[0x10000,20])
            self.assertEqual(call('gr2_hdf_reservation_required',context),0)
        b['busy']=True;self.assertEqual(call('gr2_hdf_configuration_policy',parent,child),1);b['busy']=False
        self.assertEqual(frame(parent),frame(child));self.assertEqual(frame(parent)[1:3],[0x30000,0])
        self.assertEqual(call('gr2_hdf_configuration_publish',2,22),1)
        for context in (parent,child):
            self.assertEqual(call('gr2_hdf_configuration_prepare',context),1);self.assertEqual(frame(context)[1:3],[0x10000,0])
        self.assertEqual(calls.count(0xa00665cc),1)

    def test_policy_validates_both_owners_before_writing_and_rejects_unknown_phase_even_with_valid_crc(self):
        u,contexts,b,calls,call,frame=self.fixture();parent,child,_=contexts
        self.assertEqual(call('gr2_hdf_configuration_publish',2,30),1)
        self.assertEqual(call('gr2_hdf_configuration_begin',parent),1);before=bytes(u.mem_read(parent,0x12b9c))
        for peer in (parent,child+4):
            self.assertEqual(call('gr2_hdf_configuration_policy',parent,peer),0);self.assertEqual(bytes(u.mem_read(parent,0x12b9c)),before)
        self.assertEqual(call('gr2_hdf_configuration_policy',parent,0),1);self.assertEqual(frame(parent)[1:3],[0x30002,30])
        original=bytes(u.mem_read(parent+0x12b8c,16))
        for phase in (0x20000,0x40000,0x50000):
            prefix=struct.pack('>3I',0x47324844,phase|2,30);wire=prefix+struct.pack('>I',zlib.crc32(prefix))
            u.mem_write(parent+0x12b8c,wire);self.assertEqual(call('gr2_hdf_frame_read',parent,0x50003000),0)
        u.mem_write(parent+0x12b8c,original);self.assertEqual(call('gr2_hdf_configuration_prepare',parent),1)
        self.assertEqual(frame(parent)[1:3],[0x10002,30])

    def test_cold_policy_hook_freezes_both_original_main_queue_owners_before_allowing_auxiliary_clone(self):
        from scripts.analyze_gr2_native_contract import probe_thumbnail_clone_scheduling
        runtime=self.build()
        for sibling in (False,True):
            for grade in (0,1,2,3):
                with self.subTest(sibling=sibling,grade=grade):
                    result=probe_thumbnail_clone_scheduling(component('gr2','b01firm8'),0,sibling=sibling,native_runtime=runtime,
                                                            hdf_strength=grade,publish_after=(3 if grade==0 else 0,88))
                    family=[result['parent'],result['main']] if sibling else [result['parent']]
                    self.assertEqual(result['frozen'],[[0x30000|grade,77]]*len(family))
                    self.assertEqual(result['prepared'],[[0x10000|grade,77]]*len(family))
                    expected=([[0x20004005,result['auxiliary'],0]] if grade==0 else [])
                    if sibling:expected.append([0x20004001,result['main'],0])
                    expected.append([0x20004001,result['parent'],0])
                    self.assertEqual(result['queues'],expected);self.assertTrue(result['stack_preserved'])

    def test_original_preparation_and_dsp_graph_use_policy_grade_after_ui_changes_before_reservation(self):
        from scripts.analyze_gr2_native_contract import probe_ordered_capture_pools
        from collections import Counter
        runtime=self.build()
        for policy,ui in ((0,3),(3,0),(1,3)):
            with self.subTest(policy=policy,ui=ui):
                result=probe_ordered_capture_pools(component('gr2','b01firm8'),native_runtime=runtime,postprocess_effect=0,
                                                 postprocess_original_prepare=True,postprocess_hdf=ui,postprocess_policy_strength=policy,postprocess_execute_hdf=True)
                post=result['postprocessor'];self.assertEqual(post['hdf_after'],[0x10000|policy,77])
                self.assertEqual([row['operation'] for row in post['packets']],[13] if policy else [])
                self.assertEqual(bool(post['reserved_before']),bool(policy));self.assertEqual(post['reserved_after'],0)
                self.assertEqual(post['peak_jpeg_blocks'],2 if policy else 1)
                self.assertTrue(all(row['stage6'] for row in post['preparation_trace']))
                self.assertEqual(post['dsp']['graph_calls'],int(bool(policy)))
                self.assertEqual(Counter(post['dsp']['resources_acquired']),Counter(post['dsp']['resources_released']))
                self.assertTrue(post['property_counters_balanced']);self.assertTrue(post['ring_restored']);self.assertTrue(post['primary_retained'])
                self.assertTrue(result['stack_preserved'])

    def test_owned_film_carriers_do_not_use_the_preproducer_auxiliary_clone_even_with_hdf_off(self):
        from scripts.analyze_gr2_native_contract import probe_thumbnail_clone_scheduling
        runtime=self.build();code=component('gr2','b01firm8')
        for tone in (9,10,11,18,8):
            with self.subTest(tone=tone):
                stock=probe_thumbnail_clone_scheduling(code,tone,sibling=True)
                self.assertEqual(stock['queues'][0][0],0x20004005)
                native=probe_thumbnail_clone_scheduling(code,tone,sibling=True,native_runtime=runtime,hdf_strength=0)
                self.assertEqual(native['clones'],[])
                self.assertEqual(native['queues'],[[0x20004001,native['main'],0],[0x20004001,native['parent'],0]])
                self.assertEqual(native['frozen'],[[0x30000,77],[0x30000,77]])

    def test_unknown_callers_or_invalid_family_retain_original_predicate_without_freezing(self):
        u,contexts,b,calls,call,frame=self.fixture();parent,child,_=contexts
        for context in (parent,child):
            u.mem_write(context+0x355,b'\x01');u.mem_write(context+0x357,b'\x00');u.mem_write(context+0x254,b'\x00')
            u.mem_write(context+0x408,b'\x00');u.mem_write(context+0x400,b'\x00');u.mem_write(context+0x304,b'\x00');u.mem_write(context+0x20,bytes(4))
        before=[bytes(u.mem_read(context,0x12b9c)) for context in (parent,child)]
        for peer,caller in ((0,0),(child,0xa029e1f6),(0,0xa029e1f7),(parent,0xa029e1f7),(child+4,0xa029e1f7),(child,0xa029e25f)):
            with self.subTest(peer=peer,caller=hex(caller)):
                self.assertEqual(call('gr2_hdf_clone_policy',parent,peer,caller),1)
                self.assertEqual([bytes(u.mem_read(context,0x12b9c)) for context in (parent,child)],before)
        self.assertEqual(calls,[])
