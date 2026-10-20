"""Admission uses stock image ownership handles, not guessed RAM address ranges."""
import struct
import unittest
from tests import test_gr2_runtime_build as runtime_tests

class Gr2CaptureTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    call=runtime_tests.Gr2RuntimeBuildTests.call

    def owner_pool(self,u,base=0x51000000,extra=0):
        # Synthetic initialized MPF metadata; the independent owner probe also
        # executes the original factory against its actual initialized pools.
        for page in (0xa0113000,0xa0129000,0xa05fb000,0xa00b5000):
            if not any(lo<=page<=hi for lo,hi,_ in u.mem_regions()):u.mem_map(page,4096)
        block=0xfb14+extra
        u.mem_write(0xa0129c54,struct.pack('>I',0xa05fb0e8));u.mem_write(0xa01137ec,struct.pack('>I',block-8))
        u.mem_write(0xa05fb0e8,b'MPL '+struct.pack('>4I',0x01000000,block,60*block,0)+struct.pack('>2H',1,0))
        u.mem_write(0xa00b5bfc,struct.pack('>H',1));u.mem_write(0xa00b5bdc,struct.pack('>I',0x50008000))
        u.mem_write(0x50008000,struct.pack('>6I',0xffffffff,base,0,60*block,block,base))

    def test_inline_frame_snapshot_freezes_recipe_once_and_rejects_unextended_or_corrupt_owners(self):
        report=self.build();self.assertIn('gr2_frame_freeze',report['symbols']);self.assertIn('gr2_frame_read',report['symbols'])
        u=self.machine(report);u.mem_map(0x51000000,0x10000);context=0x51000008;u.mem_write(context-8,b'IMG '+bytes(4))
        self.owner_pool(u);state=0x50002000;out=0x50003000;tail=context+0xfb0c
        self.call(u,report['symbols']['m10v_library_init'],[state]);original=bytes(u.mem_read(state,104))
        freeze=report['symbols']['gr2_frame_freeze'];read=report['symbols']['gr2_frame_read']
        self.assertEqual(self.call(u,freeze,[context,state,2,0x12345678]),0)
        self.assertEqual(bytes(u.mem_read(tail,128)),bytes(128))
        self.owner_pool(u,extra=128)
        self.assertEqual(self.call(u,freeze,[context,state,2,0x12345678]),1)
        snapshot=bytes(u.mem_read(tail,128));self.assertEqual(snapshot[16:120],original)
        u.mem_write(state,b'\xa5'*104)
        self.assertEqual(self.call(u,read,[context,out]),1);self.assertEqual(bytes(u.mem_read(out,128)),snapshot)
        self.assertEqual(self.call(u,freeze,[context,out+16,3,99]),0)
        self.assertEqual(bytes(u.mem_read(tail,128)),snapshot)
        self.assertEqual(self.call(u,read,[context,context+128]),0)
        u.mem_write(out,b'\xa5'*128);u.mem_write(tail+12,bytes(4))
        self.assertEqual(self.call(u,read,[context,out]),0);self.assertEqual(bytes(u.mem_read(out,128)),b'\xa5'*128)

    def test_native_image_owner_matches_original_fixed_pool_and_rejects_forgery(self):
        from scripts.analyze_gr2_native_contract import probe_image_object_pools
        from tests.test_unity_update import component
        runtime=self.build()
        self.assertIn('gr2_image_owner_bytes',runtime['symbols'])
        for extra in (0,128):
            result=probe_image_object_pools(component('gr2','b01firm8'),extra=extra,native_runtime=runtime)
            self.assertEqual(result['native_owner_live'],[0xfb0c+extra]*2)
            self.assertEqual(result['native_owner_rejected'],[0]*6)
            self.assertEqual(result['native_owner_retired'],[0,0])
            if extra:self.assertEqual(result['native_frame_clone'],dict(freeze=1,read=1,matches=True))

    def test_capture_admission_binds_descriptor_to_source_output_and_protected_raw_handles(self):
        report=self.build();self.assertIn('gr2_capture_admit',report['symbols']);u=self.machine(report)
        u.mem_map(0x51000000,0x10000);context=0x51000008
        u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u)
        source=0x5000a000;output=0x5000a100;raw=0x5000a200
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
        for mutation in ('short_source','raw_overlap','producer_raw_overlap','context_bad_magic','context_wrong_type','pool_wrong_base','pool_wrong_stride','wrong_output','wrong_dimensions','bad_magic'):
            handle(source,0x60000000,640*480*2);handle(output,0x64000000,0x200000);handle(raw,0x68000000,0x2000000)
            u.mem_write(context+0x1e0,bytes(4));u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u)
            changed=bytearray(request)
            if mutation=='short_source':handle(source,0x60000000,640*480)
            elif mutation=='raw_overlap':handle(raw,0x60000040,0x10000)
            elif mutation=='producer_raw_overlap':
                handle(0x5000a300,0x60000040,0x10000);u.mem_write(context+0x1e0,struct.pack('>I',0x5000a300))
            elif mutation=='context_bad_magic':u.mem_write(context-8,b'void')
            elif mutation=='context_wrong_type':u.mem_write(context-4,struct.pack('>I',1))
            elif mutation=='pool_wrong_base':u.mem_write(0x50008014,struct.pack('>I',0x51000004))
            elif mutation=='pool_wrong_stride':u.mem_write(0x50008010,struct.pack('>I',0xfb18))
            elif mutation=='wrong_output':struct.pack_into('>I',changed,4,0x64000004)
            elif mutation=='wrong_dimensions':struct.pack_into('>I',changed,8,(400<<16)|640)
            else:u.mem_write(source,b'BAD!')
            u.mem_write(0x50001000,bytes(changed));u.mem_write(0x50002000,b'\xa5'*44)
            with self.subTest(mutation=mutation):
                self.assertEqual(self.call(u,entry,[context,1,0x50001000,0x50002000]),0)
                self.assertEqual(bytes(u.mem_read(0x50002000,44)),b'\xa5'*44)

    def test_admission_preserves_image_owner_and_buff_metadata(self):
        report=self.build();u=self.machine(report);u.mem_map(0x51000000,0x10000)
        context=0x51000008;source=0x5000a000;output=0x5000a100;request=0x50001000
        u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u)
        def setup(data=0x60000000):
            u.mem_write(source,b'BUFF'+struct.pack('>5I',data,256,0,0,256))
            u.mem_write(output,b'BUFF'+struct.pack('>5I',0x64000000,0,0,0,4096))
            u.mem_write(context+0x1f4,struct.pack('>I',source));u.mem_write(context+0x204,struct.pack('>I',output))
            u.mem_write(context+0x3e4,struct.pack('>I',(4<<16)|32))
            descriptor=bytearray(48);struct.pack_into('>3I',descriptor,0,data,0x64000000,(4<<16)|32);descriptor[13]=2
            u.mem_write(request,bytes(descriptor))
        entry=report['symbols']['gr2_capture_admit'];setup()
        before=bytes(u.mem_read(output,24))
        self.assertEqual(self.call(u,entry,[context,1,request,output]),0)
        self.assertEqual(bytes(u.mem_read(output,24)),before)
        u.mem_write(context+0x800,b'\xa5'*44)
        self.assertEqual(self.call(u,entry,[context,1,request,context+0x800]),0)
        self.assertEqual(bytes(u.mem_read(context+0x800,44)),b'\xa5'*44)
        for data in (context+0x100,source+4):
            setup(data);u.mem_write(0x50002000,b'\xa5'*44)
            self.assertEqual(self.call(u,entry,[context,1,request,0x50002000]),0)
            self.assertEqual(bytes(u.mem_read(0x50002000,44)),b'\xa5'*44)

    def test_synchronous_capture_process_uses_real_pool_and_preserves_raw_or_rejected_pixels(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from tests.test_unity_update import component
        from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_INTR,arm_const as r
        import zlib
        report=self.build();self.assertIn('gr2_capture_process',report['symbols'])
        rendered=None
        for failure,mode in (('none',0x13),('frozen',0x13),('corrupt_frame',0x13),('raw_overlap',0x13),('allocation',0x13),('none',0x10)):
            with self.subTest(failure=failure,mode=mode):
                u=runtime_machine(component('gr2','b01firm8'),cpu_model=r.UC_CPU_ARM_946);u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']))
                table=0x50007000;u.mem_write(0xa00b5bfe,struct.pack('>H',1));u.mem_write(0xa00b5be0,struct.pack('>I',table));u.mem_write(table,struct.pack('>h',-2))
                self.call(u,0xa0024bcb,[])
                for address in (0x60000000,0x64000000,0x68000000):u.mem_map(address,4096)
                y=bytes((i*31+9)%256 for i in range(128));chroma=bytes((i*7+83)%256 for i in range(128));u.mem_write(0x60000000,y+chroma)
                u.mem_write(0x68000000,b'\xa5'*4096)
                u.mem_map(0x51000000,0x10000);context=0x51000008;u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u)
                for offset,handle,data,used,capacity in ((0x1f4,0x5000a000,0x60000000,256,256),(0x204,0x5000a100,0x64000000,0,4096),(0x1e4,0x5000a200,0x60000008 if failure=='raw_overlap' else 0x68000000,4096,4096)):
                    u.mem_write(context+offset,struct.pack('>I',handle));u.mem_write(handle,b'BUFF'+struct.pack('>5I',data,used,0,0,capacity))
                u.mem_write(context+0x3e4,struct.pack('>I',(4<<16)|32))
                descriptor=bytearray(48);struct.pack_into('>3I',descriptor,0,0x60000000,0x64000000,(4<<16)|32);descriptor[13]=2;u.mem_write(0x50001000,bytes(descriptor))
                self.call(u,report['symbols']['m10v_library_init'],[0x50002000]);state=bytearray(u.mem_read(0x50002000,104));struct.pack_into('>H',state,12,33);struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50002000,bytes(state))
                if failure in ('frozen','corrupt_frame'):
                    self.owner_pool(u,extra=128)
                    self.assertEqual(self.call(u,report['symbols']['gr2_frame_freeze'],[context,0x50002000,0,0x60000000]),1)
                    u.mem_write(0x50002000,b'\xa5'*104)
                    if failure=='corrupt_frame':u.mem_write(context+0xfb0c+12,bytes(4))
                if failure=='allocation':
                    head=struct.unpack('>I',u.mem_read(table+4,4))[0];blocks=struct.unpack('>I',u.mem_read(head+12,4))[0];unit=struct.unpack('>I',u.mem_read(table+20,4))[0]
                    self.assertNotEqual(self.call(u,report['symbols']['gr2_allocate'],[blocks*unit]),0)
                cache=[];timeline=[]
                u.hook_add(UC_HOOK_MEM_READ,lambda *args:timeline.append("context"),begin=context-8,end=context+0xfb0c)
                def cp15(uc,address,size,context):
                    word=struct.unpack('>I',uc.mem_read(address,4))[0]
                    if word&0x0f100f10==0x0e000f10:cache.append(address);timeline.append("cache");uc.reg_write(r.UC_ARM_REG_PC,address+4)
                u.hook_add(UC_HOOK_CODE,cp15,begin=report['symbols']['gr2_cache_before'],end=report['symbols']['gr2_cache_gateway']+80)
                if mode==0x10:
                    from scripts.analyze_unity_runtime import parse_executable_load_map
                    code=component('gr2','b01firm8');low=parse_executable_load_map(code)[15]
                    u.mem_map(0,0x10000);u.mem_write(low['address'],code[low['source_file_offset']:low['source_file_offset']+low['length']])
                    u.mem_write(0xA0044F4C,bytes.fromhex(report['cache_gateway_patch_hex']))
                    syscalls=[]
                    def interrupt(uc,number,context):
                        self.assertEqual(number,2)
                        old=uc.reg_read(r.UC_ARM_REG_CPSR);resume=uc.reg_read(r.UC_ARM_REG_PC)
                        syscalls.append(struct.unpack('>I',uc.mem_read(resume-4,4))[0]&0xffffff)
                        uc.reg_write(r.UC_ARM_REG_CPSR,(old&~0x3f)|0x13)
                        uc.reg_write(r.UC_ARM_REG_SP,0x50017000);uc.reg_write(r.UC_ARM_REG_SPSR,old)
                        uc.reg_write(r.UC_ARM_REG_LR,resume);uc.reg_write(r.UC_ARM_REG_PC,0x844)
                    u.hook_add(UC_HOOK_INTR,interrupt)
                    # One running task, no pending switch. Exercise the stock
                    # scheduler return after pool free, not a synthetic bypass.
                    u.mem_write(0xA00C22C0,struct.pack('>H',1));u.mem_write(0xA05FA969,b'\x01')
                    old=u.reg_read(r.UC_ARM_REG_CPSR)
                    u.reg_write(r.UC_ARM_REG_CPSR,(old&~0x3f)|0x12);u.reg_write(r.UC_ARM_REG_SP,0x50016000)
                    u.reg_write(r.UC_ARM_REG_CPSR,(old&~0x3f)|mode)
                u.mem_write(0x50018000,struct.pack('>I',0))
                entry=report['symbols'].get('gr2_capture_frozen') if failure in ('frozen','corrupt_frame') else report['symbols']['gr2_capture_process']
                self.assertIsNotNone(entry,'frozen capture adapter missing')
                result=self.call(u,entry,[context,1,0x50001000,0x50002000])
                if mode==0x10:
                    self.assertEqual(syscalls,[5,4,3,5,4,3,0])
                    self.assertEqual(u.reg_read(r.UC_ARM_REG_CPSR)&31,16)
                    self.assertEqual(u.reg_read(r.UC_ARM_REG_SP),0x50018000)
                self.assertEqual(result,0 if failure in ('none','frozen') else 0xfffffffe if failure=='allocation' else 0xffffffff)
                self.assertEqual(bytes(u.mem_read(0x68000000,4096)),b'\xa5'*4096)
                if failure not in ('none','frozen'):self.assertEqual(bytes(u.mem_read(0x60000000,256)),y+chroma)
                else:
                    self.assertEqual(len(cache),2)
                    self.assertEqual(timeline[0],"cache")
                    pixels=bytes(u.mem_read(0x60000000,256))
                    if failure=='frozen':self.assertEqual(pixels,rendered)
                    elif mode==0x13:rendered=pixels
                    self.assertNotEqual(bytes(u.mem_read(0x60000000,256)),y+chroma)
