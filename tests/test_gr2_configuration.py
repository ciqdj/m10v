"""UI publishes owned configuration; capture freezes it under original RTOS mutex."""
import struct
import subprocess
import unittest
import zlib
from tests import test_gr2_capture as capture_tests,test_gr2_runtime_build as runtime_tests
from tests.test_unity_update import ROOT,component

class Gr2ConfigurationTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    call=runtime_tests.Gr2RuntimeBuildTests.call
    owner_pool=capture_tests.Gr2CaptureTests.owner_pool

    def test_installed_producer_entry_reads_published_configuration_and_preserves_original_iq_return(self):
        from scripts.analyze_gr2_native_contract import probe_producer_iq
        runtime=self.build();self.assertIn('producer_hook_patch_hex',runtime)
        for tone in (9,10,11,18,8):
            with self.subTest(tone=tone):
                result=probe_producer_iq(component('gr2','b01firm8'),component('gr2','b01firm6'),native_runtime=runtime,tone=tone,active_configuration=True)
                self.assertEqual(result['engine_mode'],0);self.assertEqual(result['restored_mode'],tone)
                self.assertEqual(result['snapshot_valid'],1);self.assertEqual(result['producer_return'],0x40020)
                self.assertTrue(result['response_copied']);self.assertTrue(result['stack_preserved'])

    def test_owned_configuration_publishes_atomically_and_freezes_without_sd_or_external_lut_pointers(self):
        self.exercise_owned_configuration(False)

    def test_user_task_configuration_uses_original_svc_and_preserves_user_mode_through_publish_freeze_clear(self):
        self.exercise_owned_configuration(True)

    def exercise_owned_configuration(self,user):
        from scripts.analyze_gr2_native_contract import runtime_machine
        runtime=self.build();self.assertIn('gr2_configuration_publish',runtime['symbols'])
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        u.mem_write(0xa00b5bfe,struct.pack('>H',1));u.mem_write(0xa00b5be0,struct.pack('>I',0x50007000));u.mem_write(0x50007000,struct.pack('>h',-2));self.call(u,0xa0024bcb,[])
        u.mem_write(0xa00b5bf8,struct.pack('>h',2));u.mem_write(0xa00b5bd4,struct.pack('>I',0x50009000))
        for i in range(2):u.mem_write(0x50009000+14*i,struct.pack('>h',-2))
        u.mem_write(0xa06b6de0,b'\1');u.mem_write(0xa06b6de3,b'\1');u.mem_write(0xa00c22c0,struct.pack('>h',1))
        for i in (1,2):
            task=0xa05f5c28+68*i;u.mem_write(task+8,struct.pack('>2h',-1,-1));u.mem_write(task+24,struct.pack('>3h',20,0,20))
        u.mem_map(0x51000000,0x20000);u.mem_map(0x52000000,0x4000)
        context=0x51000008;state=0x50002000;records=0x50002400;out=0x50003000
        u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u,extra=128+12288)
        sym=runtime['symbols'];self.call(u,sym['m10v_library_init'],[state]);initial=bytes(u.mem_read(state,104))
        def invoke(name,*args):
            try:return self.call(u,sym['gr2_configuration_'+name],list(args))
            except Exception as error:
                from unicorn import arm_const as r
                raise RuntimeError(f'{name} user={user} PC={u.reg_read(r.UC_ARM_REG_PC):08x} LR={u.reg_read(r.UC_ARM_REG_LR):08x} SP={u.reg_read(r.UC_ARM_REG_SP):08x} syscalls={syscalls}') from error
        word=lambda p:struct.unpack('>I',u.mem_read(p,4))[0]
        free=lambda:word(word(0x50007004)+12)*word(0x50007014)
        def set_task(identity):
            u.mem_write(0xa00c22c0,struct.pack('>h',identity))
            if user:
                # Match the current synthetic task in the original ready
                # bitmap/head. Otherwise SVC0 correctly schedules task0.
                u.mem_write(0xa00c22c4,struct.pack('>I',0x80000000))
                u.mem_write(0xa05f5800,struct.pack('>I',0x1000))
                u.mem_write(0xa05f5824+19*4,struct.pack('>h',identity))
                u.mem_write(0xa05fa968+identity,b'\1')
        syscalls=capture_tests.Gr2CaptureTests.enter_user_task(self,u,runtime) if user else []
        set_task(1)
        before=free();u.mem_write(out,b'\xa5'*104)
        self.assertEqual(invoke('read',out),0);self.assertEqual(bytes(u.mem_read(out,104)),b'\xa5'*104)
        u.mem_write(context+0x408,b'\x09');self.assertEqual(invoke('freeze',context,1234),0)
        self.assertEqual(invoke('publish',state,records),1);resident=free();self.assertLess(resident,before)
        self.assertEqual(invoke('read',out),1);self.assertEqual(bytes(u.mem_read(out,104)),initial)
        self.assertIn('gr2_configuration_names',sym)
        self.assertEqual(invoke('names',0x50004000),1)
        names=bytes(u.mem_read(0x50004000,960)).decode('utf-16-be').split('\0')
        self.assertEqual(names[0],'Ektar 100')
        # A second task holding the actual kernel mutex prevents publication and
        # capture admission without spinning, altering state or leaking memory.
        set_task(2);self.assertEqual(self.call(u,0xa0066d94,[1,0]),0)
        set_task(1);self.assertEqual(invoke('publish',state,records),0);self.assertEqual(free(),resident)
        self.assertEqual(invoke('freeze',context,1234),0);self.assertEqual(bytes(u.mem_read(context+0xfb0c,128)),bytes(128))
        set_task(2);self.assertEqual(self.call(u,0xa00671b8,[1]),0);set_task(1)
        record=subprocess.check_output(['node','--input-type=module','-e',"import {customFilmRecord} from './compat/gr2-v1/node/gr3-sd-film-pack.mjs';process.stdout.write(customFilmRecord({name:'Published LUT',rgb:Buffer.alloc(6591,83)},79));"],cwd=ROOT)
        custom=bytearray(initial);struct.pack_into('>H',custom,12,79);custom[62]=1;struct.pack_into('>I',custom,100,zlib.crc32(custom[:100]));u.mem_write(state,bytes(custom))
        self.assertEqual(invoke('publish',state,records),0)
        u.mem_write(0x52000000,record);u.mem_write(records,struct.pack('>5I',0x52000000,0,0,0,0));self.assertEqual(invoke('publish',state,records),1)
        u.mem_write(state,b'\xa5'*104);u.mem_write(0x52000000,b'\xa5'*12288);u.mem_write(records,bytes(20))
        self.assertEqual(invoke('names',0x50004000),1)
        self.assertEqual(bytes(u.mem_read(0x50004000,192)).decode('utf-16-be').split('\0')[0],'Published LUT')
        self.assertEqual(invoke('freeze',context,1234),1);self.assertEqual(bytes(u.mem_read(context+0x408,1)),b'\x09')
        self.assertEqual(self.call(u,sym['gr2_frame_read'],[context,out]),1)
        self.assertEqual(bytes(u.mem_read(out+16,104)),bytes(custom));self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),record)
        # A new publication cannot rewrite a retained frame, and clearing the
        # live configuration leaves its value-only image snapshot valid.
        u.mem_write(state,initial);self.assertEqual(invoke('publish',state,records),1);self.assertEqual(invoke('freeze',context,9999),1)
        self.assertEqual(bytes(u.mem_read(context+0xfb0c+12,4)),struct.pack('>I',1234))
        self.assertEqual(invoke('clear'),1);self.assertEqual(free(),before)
        self.assertEqual(self.call(u,sym['gr2_frame_read'],[context,out]),1)
        self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),record)
        # Only a new outer recipe clears the previous value-only snapshot;
        # worker freeze and publication above deliberately retain it.
        self.assertIn('gr2_configuration_begin',sym)
        prefix=bytes(u.mem_read(context,0xfb0c));self.assertEqual(invoke('begin',context),0)
        self.assertEqual(bytes(u.mem_read(context+0xfb0c,128+12288)),bytes(128+12288));self.assertEqual(bytes(u.mem_read(context,0xfb0c)),prefix)
        u.mem_write(state,initial);self.assertEqual(invoke('publish',state,records),1);u.mem_write(context+0x408,b'\x0a')
        self.assertEqual(invoke('begin',context),1);self.assertEqual(self.call(u,sym['gr2_frame_read'],[context,out]),1)
        self.assertEqual(word(out+8),1);self.assertEqual(bytes(u.mem_read(out+16,104)),initial)
        self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),bytes(12288))
        self.assertEqual(invoke('clear'),1);self.assertEqual(free(),before)
        if user:
            from unicorn import arm_const as r
            self.assertEqual(u.reg_read(r.UC_ARM_REG_CPSR)&31,16)
            self.assertIn(4,syscalls);self.assertIn(3,syscalls);self.assertIn(0,syscalls)
