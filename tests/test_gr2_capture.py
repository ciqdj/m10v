"""Admission uses stock image ownership handles, not guessed RAM address ranges."""
import struct
import unittest
from tests import test_gr2_runtime_build as runtime_tests

class Gr2CaptureTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    call=runtime_tests.Gr2RuntimeBuildTests.call

    def test_capture_admission_binds_descriptor_to_source_output_and_protected_raw_handles(self):
        report=self.build();self.assertIn('gr2_capture_admit',report['symbols']);u=self.machine(report)
        context=0x50008000;source=0x5000a000;output=0x5000a100;raw=0x5000a200
        def handle(address,data,size):u.mem_write(address,b'BUFF'+struct.pack('>5I',data,size,0,0,size))
        handle(source,0x60000000,640*480*2);handle(output,0x64000000,0x200000);handle(raw,0x68000000,0x2000000)
        for offset,pointer in ((0x1f4,source),(0x204,output),(0x1e4,raw)):u.mem_write(context+offset,struct.pack('>I',pointer))
        u.mem_write(context+0x3e4,struct.pack('>I',(480<<16)|640))
        request=bytearray(48);struct.pack_into('>3I',request,0,0x60000000,0x64000000,(480<<16)|640);request[13]=2
        u.mem_write(0x50001000,bytes(request));entry=report['symbols']['gr2_capture_admit']
        self.assertEqual(self.call(u,entry,[context,1,0x50001000,0x50002000]),1)
        self.assertEqual(self.call(u,entry,[context,1,0x50001000,0x50001000]),0)
        self.assertEqual(bytes(u.mem_read(0x50001000,48)),bytes(request))
        # A freshly allocated JPEG output has zero used bytes and a nonzero capacity.
        u.mem_write(output+8,struct.pack('>I',0))
        self.assertEqual(self.call(u,entry,[context,1,0x50001000,0x50002000]),1)
        for mutation in ('short_source','raw_overlap','wrong_output','wrong_dimensions','bad_magic'):
            handle(source,0x60000000,640*480*2);handle(output,0x64000000,0x200000);handle(raw,0x68000000,0x2000000)
            changed=bytearray(request)
            if mutation=='short_source':handle(source,0x60000000,640*480)
            elif mutation=='raw_overlap':handle(raw,0x60000040,0x10000)
            elif mutation=='wrong_output':struct.pack_into('>I',changed,4,0x64000004)
            elif mutation=='wrong_dimensions':struct.pack_into('>I',changed,8,(400<<16)|640)
            else:u.mem_write(source,b'BAD!')
            u.mem_write(0x50001000,bytes(changed));u.mem_write(0x50002000,b'\xa5'*44)
            with self.subTest(mutation=mutation):
                self.assertEqual(self.call(u,entry,[context,1,0x50001000,0x50002000]),0)
                self.assertEqual(bytes(u.mem_read(0x50002000,44)),b'\xa5'*44)

    def test_synchronous_capture_process_uses_real_pool_and_preserves_raw_or_rejected_pixels(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from tests.test_unity_update import component
        from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,arm_const as r
        import zlib
        report=self.build();self.assertIn('gr2_capture_process',report['symbols'])
        for failure in ('none','raw_overlap','allocation'):
            with self.subTest(failure=failure):
                u=runtime_machine(component('gr2','b01firm8'));u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']))
                table=0x50007000;u.mem_write(0xa00b5bfe,struct.pack('>H',1));u.mem_write(0xa00b5be0,struct.pack('>I',table));u.mem_write(table,struct.pack('>h',-2))
                self.call(u,0xa0024bcb,[])
                for address in (0x60000000,0x64000000,0x68000000):u.mem_map(address,4096)
                y=bytes((i*31+9)%256 for i in range(128));chroma=bytes((i*7+83)%256 for i in range(128));u.mem_write(0x60000000,y+chroma)
                u.mem_write(0x68000000,b'\xa5'*4096)
                context=0x50008000
                for offset,handle,data,used,capacity in ((0x1f4,0x5000a000,0x60000000,256,256),(0x204,0x5000a100,0x64000000,0,4096),(0x1e4,0x5000a200,0x60000008 if failure=='raw_overlap' else 0x68000000,4096,4096)):
                    u.mem_write(context+offset,struct.pack('>I',handle));u.mem_write(handle,b'BUFF'+struct.pack('>5I',data,used,0,0,capacity))
                u.mem_write(context+0x3e4,struct.pack('>I',(4<<16)|32))
                descriptor=bytearray(48);struct.pack_into('>3I',descriptor,0,0x60000000,0x64000000,(4<<16)|32);descriptor[13]=2;u.mem_write(0x50001000,bytes(descriptor))
                self.call(u,report['symbols']['m10v_library_init'],[0x50002000]);state=bytearray(u.mem_read(0x50002000,104));struct.pack_into('>H',state,12,33);struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50002000,bytes(state))
                if failure=='allocation':
                    head=struct.unpack('>I',u.mem_read(table+4,4))[0];blocks=struct.unpack('>I',u.mem_read(head+12,4))[0];unit=struct.unpack('>I',u.mem_read(table+20,4))[0]
                    self.assertNotEqual(self.call(u,report['symbols']['gr2_allocate'],[blocks*unit]),0)
                cache=[];timeline=[]
                u.hook_add(UC_HOOK_MEM_READ,lambda *args:timeline.append("context"),begin=context,end=context+0x400)
                def cp15(uc,address,size,context):
                    word=struct.unpack('>I',uc.mem_read(address,4))[0]
                    if word&0x0f100f10==0x0e000f10:cache.append(address);timeline.append("cache");uc.reg_write(r.UC_ARM_REG_PC,address+4)
                u.hook_add(UC_HOOK_CODE,cp15,begin=report['symbols']['gr2_cache_before'],end=report['symbols']['gr2_cache_gateway']-4)
                u.mem_write(0x50018000,struct.pack('>I',0))
                result=self.call(u,report['symbols']['gr2_capture_process'],[context,1,0x50001000,0x50002000])
                self.assertEqual(result,0 if failure=='none' else 0xfffffffe if failure=='allocation' else 0xffffffff)
                self.assertEqual(bytes(u.mem_read(0x68000000,4096)),b'\xa5'*4096)
                if failure!='none':self.assertEqual(bytes(u.mem_read(0x60000000,256)),y+chroma)
                else:
                    self.assertEqual(len(cache),2)
                    self.assertEqual(timeline[0],"cache")
                    self.assertNotEqual(bytes(u.mem_read(0x60000000,256)),y+chroma)
