"""Admission uses stock image ownership handles, not guessed RAM address ranges."""
import struct
import unittest
import zlib
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

    def test_custom_lut_record_is_frozen_inline_and_corruption_never_overwrites_stock_owner(self):
        import subprocess
        from tests.test_unity_update import ROOT
        runtime=self.build();self.assertIn('gr2_frame_freeze_custom',runtime['symbols'])
        record=subprocess.check_output(['node','--input-type=module','-e',"import {customFilmRecord} from './node/gr3-sd-film-pack.mjs';process.stdout.write(customFilmRecord({name:'Frozen LUT',rgb:Buffer.from(Array.from({length:6591},(_,i)=>(i*7+83)%256))},79));"],cwd=ROOT)
        from scripts.analyze_gr2_native_contract import probe_image_object_pools
        from tests.test_unity_update import component
        cloned=probe_image_object_pools(component('gr2','b01firm8'),extra=128+12288,native_runtime=runtime,custom_record=record)
        self.assertEqual(cloned['native_owner_live'],[0x12b8c]*2)
        self.assertEqual(cloned['native_frame_clone'],dict(freeze=1,read=1,matches=True,custom_record_matches=True))
        self.assertTrue(cloned['all_blocks_released']);self.assertEqual(cloned['counter_after_retirement'],0)
        from scripts.analyze_gr2_native_contract import runtime_machine
        u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
        u.mem_write(0xa00b5bfe,struct.pack('>H',1));u.mem_write(0xa00b5be0,struct.pack('>I',0x50007000));u.mem_write(0x50007000,struct.pack('>h',-2));self.call(u,0xa0024bcb,[])
        u.mem_map(0x51000000,0x20000);u.mem_map(0x52000000,0x4000)
        context=0x51000008;state=0x50002000;out=0x50003000;tail=context+0xfb0c
        u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u,extra=128+12288)
        self.call(u,runtime['symbols']['m10v_library_init'],[state]);wire=bytearray(u.mem_read(state,104));struct.pack_into('>H',wire,12,79);wire[62]=1;struct.pack_into('>I',wire,100,zlib.crc32(wire[:100]));u.mem_write(state,bytes(wire))
        self.assertEqual(self.call(u,runtime['symbols']['m10v_library_valid'],[state]),1)
        u.mem_write(0x52000000,record);before=bytes(u.mem_read(context,0xfb0c))
        self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_freeze'],[context,state,0,1234]),0)
        u.mem_write(0x50018000,struct.pack('>I',0x52000000))
        self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_freeze_custom'],[context,state,0,1234]),1)
        self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),record)
        self.assertEqual(bytes(u.mem_read(context,0xfb0c)),before)
        u.mem_write(0x52000000,b'\xa5'*12288)
        self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_read'],[context,out]),1)
        self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),record)
        # Render only the owned record; the external record has been overwritten.
        from unicorn import UC_HOOK_CODE,arm_const as r
        for address in (0x60000000,0x64000000):u.mem_map(address,4096)
        y=bytes((i*31+9)%256 for i in range(128));uv=bytes((i*7+83)%256 for i in range(128))
        planar=y+uv[::2]+uv[1::2];u.mem_write(0x60000000,planar)
        for offset,handle,address,used,capacity in ((0x1f4,0x5000a000,0x60000000,256,256),(0x204,0x5000a100,0x64000000,0,4096)):
            u.mem_write(context+offset,struct.pack('>I',handle));u.mem_write(handle,b'BUFF'+struct.pack('>5I',address,used,0,0,capacity))
        u.mem_write(context+0x3e4,struct.pack('>I',(4<<16)|32));request=bytearray(48);struct.pack_into('>3I',request,0,0x60000000,0x64000000,(4<<16)|32);request[13]=2;u.mem_write(0x50001000,bytes(request))
        def cp15(uc,address,size,unused):
            word=struct.unpack('>I',uc.mem_read(address,4))[0]
            if word&0x0f100f10==0x0e000f10:uc.reg_write(r.UC_ARM_REG_PC,address+4)
        u.hook_add(UC_HOOK_CODE,cp15,begin=runtime['symbols']['gr2_cache_before'],end=runtime['symbols']['gr2_cache_gateway']+80)
        u.mem_write(context+0x408,b'\x07')
        self.assertEqual(self.call(u,runtime['symbols']['gr2_capture_frozen'],[context,1,0x50001000]),0xffffffff)
        self.assertEqual(bytes(u.mem_read(0x60000000,256)),planar)
        u.mem_write(context+0x408,b'\0')
        self.assertEqual(self.call(u,runtime['symbols']['gr2_capture_frozen'],[context,1,0x50001000]),0)
        rendered=bytes(u.mem_read(0x60000000,256));self.assertNotEqual(rendered,planar)
        import ctypes as C,shutil,tempfile
        from pathlib import Path
        from tests.test_gr3_m10v_library import State,Image
        with tempfile.TemporaryDirectory() as folder:
            library=Path(folder)/'custom.dylib';sources=['m10v_library','halation_core','film_5207','film_harman','film_curated','film_newstocks']
            subprocess.run([shutil.which('clang'),'-O2','-dynamiclib',*[str(ROOT/f'native/gr3/{name}.c') for name in sources],'-o',str(library)],check=True,capture_output=True)
            host=C.CDLL(str(library));host.m10v_library_render_custom.argtypes=[C.POINTER(Image),C.POINTER(State),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_char_p]
            expected_state=State();host.m10v_library_init(C.byref(expected_state));expected_state.slots[0].film=79;expected_state.effects[0][6]=1;expected_state.crc=zlib.crc32(bytes(expected_state)[:100])
            expected_y=(C.c_uint8*128).from_buffer_copy(y);expected_uv=(C.c_uint8*128).from_buffer_copy(uv);lut=(C.c_uint8*6591).from_buffer_copy(record[64:6655]);image=Image(expected_y,expected_uv,128,128,32,4,32)
            self.assertEqual(host.m10v_library_render_custom(C.byref(image),C.byref(expected_state),0,None,1234,None,0,0,lut,b'Frozen LUT'),0)
            self.assertEqual(rendered,bytes(expected_y)+bytes(expected_uv)[::2]+bytes(expected_uv)[1::2])
        self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),record)
        u.mem_write(context+0xfb8c+64,bytes([record[64]^1]));u.mem_write(out,b'\xa5'*128)
        self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_read'],[context,out]),0)
        self.assertEqual(bytes(u.mem_read(out,128)),b'\xa5'*128)
        for extra,valid_record in ((128,True),(128+12288,False)):
            self.owner_pool(u,extra=extra);u.mem_write(tail,bytes(128+12288));u.mem_write(0x52000000,record if valid_record else b'\xa5'*12288)
            u.mem_write(0x50018000,struct.pack('>I',0x52000000))
            self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_freeze_custom'],[context,state,0,1234]),0)
            self.assertEqual(bytes(u.mem_read(tail,128+12288)),bytes(128+12288))

    def test_native_producer_wrapper_runs_original_iq_lookup_before_engine_and_restores_color_mode(self):
        from scripts.analyze_gr2_native_contract import probe_producer_iq
        from tests.test_unity_update import component
        runtime=self.build();self.assertIn('gr2_producer_run',runtime['symbols'])
        for tone in (8,9,10,11,18):
            with self.subTest(tone=tone):
                result=probe_producer_iq(component('gr2','b01firm8'),component('gr2','b01firm6'),native_runtime=runtime,tone=tone)
                self.assertEqual(result['engine_mode'],0);self.assertEqual(result['restored_mode'],tone)
                self.assertEqual(result['snapshot_valid'],1);self.assertEqual(result['producer_return'],(4<<16)|32)
                self.assertTrue(result['response_copied']);self.assertTrue(result['arena_guards_unchanged'])
                self.assertTrue(result['stack_preserved']);self.assertEqual(result['helpers_intercepted'],['ISP engine completion'])

    def enter_user_task(self,u,runtime):
        from scripts.analyze_unity_runtime import parse_executable_load_map
        from tests.test_unity_update import component
        from unicorn import UC_HOOK_INTR,arm_const as r
        code=component('gr2','b01firm8');low=parse_executable_load_map(code)[15]
        u.mem_map(0,0x10000);u.mem_write(low['address'],code[low['source_file_offset']:low['source_file_offset']+low['length']])
        u.mem_write(0xa0044f4c,bytes.fromhex(runtime['cache_gateway_patch_hex']));syscalls=[]
        def interrupt(uc,number,unused):
            self.assertEqual(number,2);old=uc.reg_read(r.UC_ARM_REG_CPSR);resume=uc.reg_read(r.UC_ARM_REG_PC)
            syscalls.append(struct.unpack('>I',uc.mem_read(resume-4,4))[0]&0xffffff)
            uc.reg_write(r.UC_ARM_REG_CPSR,(old&~0x3f)|0x13);uc.reg_write(r.UC_ARM_REG_SP,0x50017000)
            uc.reg_write(r.UC_ARM_REG_SPSR,old);uc.reg_write(r.UC_ARM_REG_LR,resume);uc.reg_write(r.UC_ARM_REG_PC,0x844)
        u.hook_add(UC_HOOK_INTR,interrupt)
        u.mem_write(0xa00c22c0,struct.pack('>H',1));u.mem_write(0xa05fa969,b'\x01')
        old=u.reg_read(r.UC_ARM_REG_CPSR);u.reg_write(r.UC_ARM_REG_CPSR,(old&~0x3f)|0x12);u.reg_write(r.UC_ARM_REG_SP,0x50016000)
        u.reg_write(r.UC_ARM_REG_CPSR,(old&~0x3f)|0x10)
        return syscalls

    def test_installed_jpeg_veneer_renders_frozen_pixels_before_encoder_and_preserves_stock_release(self):
        from scripts.analyze_gr2_native_contract import runtime_machine
        from tests.test_unity_update import component
        from unicorn import UC_HOOK_CODE,arm_const as r
        import zlib
        runtime=self.build();self.assertIn('jpeg_hook_patch_hex',runtime)
        for kind,corrupt,mode in ((1,False,0x13),(3,False,0x13),(1,True,0x13),(1,False,0x10)):
            with self.subTest(kind=kind,corrupt=corrupt,mode=mode):
                u=runtime_machine(component('gr2','b01firm8'));u.mem_write(runtime['base'],bytes.fromhex(runtime['runtime_hex']))
                u.mem_write(0xa02adc98,bytes.fromhex(runtime['jpeg_hook_patch_hex']))
                u.mem_write(0xa00b5bfe,struct.pack('>H',1));u.mem_write(0xa00b5be0,struct.pack('>I',0x50007000));u.mem_write(0x50007000,struct.pack('>h',-2))
                self.call(u,0xa0024bcb,[]);u.mem_map(0x51000000,0x10000);context=0x51000008
                u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u,extra=128)
                for address in (0x60000000,0x64000000,0x68000000):u.mem_map(address,4096)
                pixels=bytes((i*31+9)%256 for i in range(256));u.mem_write(0x60000000,pixels);u.mem_write(0x68000000,b'\xa5'*4096)
                source_offset=(0x1f4,0x1fc,0x200)[kind-1];output_offset=0x200+4*kind
                for offset,handle,address,used,capacity in ((source_offset,0x5000a000,0x60000000,256,256),(output_offset,0x5000a100,0x64000000,0,4096),(0x1e4,0x5000a200,0x68000000,4096,4096)):
                    u.mem_write(context+offset,struct.pack('>I',handle));u.mem_write(handle,b'BUFF'+struct.pack('>5I',address,used,0,0,capacity))
                u.mem_write(context+0x3e0+4*kind,struct.pack('>I',(4<<16)|32));u.mem_write(context+0x400,b'\x02')
                self.call(u,runtime['symbols']['m10v_library_init'],[0x50002000]);state=bytearray(u.mem_read(0x50002000,104));struct.pack_into('>H',state,12,33);struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50002000,bytes(state))
                self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_freeze'],[context,0x50002000,0,1234]),1)
                if corrupt:u.mem_write(context+0xfb0c+12,bytes(4))
                timeline=[];cache=[]
                def boundary(uc,address,size,unused):
                    if address==0xa01324ba:
                        request=uc.reg_read(r.UC_ARM_REG_R0);timeline.append('encode')
                        self.assertEqual(bytes(uc.mem_read(0x60000000,256))==pixels,corrupt)
                        uc.mem_write(request+0x28,struct.pack('>I',512));value=0
                    elif address==0xa029aa1a:
                        self.assertEqual(uc.reg_read(r.UC_ARM_REG_R0),context+source_offset)
                        timeline.append('release');uc.mem_write(context+source_offset,bytes(4));value=0
                    elif address in (0xa0039f9c,0xa003a01a):self.fail('stock capture assertion')
                    else:value=0x2b if address==0xa02adb7c else 0x100000
                    uc.reg_write(r.UC_ARM_REG_R0,value);uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
                for address in (0xa01324ba,0xa029aa1a,0xa02adb7c,0xa029ab3c,0xa0039f9c,0xa003a01a):u.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
                def cp15(uc,address,size,unused):
                    word=struct.unpack('>I',uc.mem_read(address,4))[0]
                    if word&0x0f100f10==0x0e000f10:cache.append(address);uc.reg_write(r.UC_ARM_REG_PC,address+4)
                u.hook_add(UC_HOOK_CODE,cp15,begin=runtime['symbols']['gr2_cache_before'],end=runtime['symbols']['gr2_cache_gateway']+80)
                for register in range(r.UC_ARM_REG_R4,r.UC_ARM_REG_R11+1):u.reg_write(register,0x12340000+register)
                syscalls=self.enter_user_task(u,runtime) if mode==0x10 else []
                self.call(u,0xa02ae5c1 if kind==1 else 0xa02ae611,[context])
                if mode==0x10:
                    self.assertEqual(syscalls,[5,4,3,5,4,3,0]);self.assertEqual(u.reg_read(r.UC_ARM_REG_CPSR)&31,16)
                self.assertEqual(timeline,['encode','release']);self.assertEqual(len(cache),1 if corrupt else 2)
                self.assertEqual(bytes(u.mem_read(0x68000000,4096)),b'\xa5'*4096)
                self.assertEqual(u.reg_read(r.UC_ARM_REG_SP),0x50018000)
                for register in range(r.UC_ARM_REG_R4,r.UC_ARM_REG_R11+1):self.assertEqual(u.reg_read(register),0x12340000+register)

    def test_prepared_frames_reach_the_original_isp_recipe_as_standard_then_restore_stock_mode(self):
        from scripts.analyze_gr2_native_contract import probe_isp_color_recipe
        from tests.test_unity_update import component
        runtime=self.build()
        for tone in (0,8,9,10,11,12,18,19,20):
            with self.subTest(tone=tone):
                result=probe_isp_color_recipe(component('gr2','b01firm8'),tone,native_runtime=runtime)
                carriers=(9,10,11,18,8);prepared=tone in carriers
                self.assertEqual(result['native_prepare'],int(prepared))
                self.assertEqual(result['native_restore'],int(prepared))
                self.assertEqual(result['restored_mode'],tone)
                if prepared:self.assertEqual(result['recipe'],0)
                self.assertTrue(result['context_unchanged'])
                self.assertTrue(result['output_guards_unchanged'])
                self.assertEqual(result['helpers_intercepted'],[])

    def test_producer_ingress_neutralizes_only_gr2_carriers_after_freezing_and_restores_owned_mode(self):
        report=self.build();self.assertIn('gr2_producer_ingress',report['symbols']);self.assertIn('gr2_producer_leave',report['symbols'])
        u=self.machine(report);u.mem_map(0x51000000,0x10000);context=0x51000008;state=0x50002000
        u.mem_write(context-8,b'IMG '+bytes(4));self.owner_pool(u,extra=128)
        self.call(u,report['symbols']['m10v_library_init'],[state])
        enter=report['symbols']['gr2_producer_ingress'];leave=report['symbols']['gr2_producer_leave']
        for tone in range(21):
            u.mem_write(context+0x408,bytes([tone]));u.mem_write(context+0xfb0c,bytes(128))
            before=bytes(u.mem_read(context,0xfb8c));carriers=(9,10,11,18,8)
            result=self.call(u,enter,[context,state,1234])
            if tone not in carriers:
                self.assertEqual(result,0);self.assertEqual(bytes(u.mem_read(context,0xfb8c)),before);continue
            self.assertEqual(result,1);self.assertEqual(bytes(u.mem_read(context+0x408,1)),bytes(1))
            snapshot=bytes(u.mem_read(context+0xfb0c,128));self.assertEqual(struct.unpack_from('>2I',snapshot,8),(carriers.index(tone),1234))
            self.assertEqual(self.call(u,leave,[context]),1);self.assertEqual(bytes(u.mem_read(context+0x408,1)),bytes([tone]))
            processed=bytearray(snapshot);struct.pack_into('>I',processed,120,5);struct.pack_into('>I',processed,124,zlib.crc32(processed[:124]));u.mem_write(context+0xfb0c,bytes(processed))
            self.assertEqual(self.call(u,enter,[context,0,9999]),1)
            self.assertEqual(bytes(u.mem_read(context+0xfb0c,128)),snapshot)
            u.mem_write(context+0x408,b'\x07');self.assertEqual(self.call(u,leave,[context]),0)
            self.assertEqual(bytes(u.mem_read(context+0x408,1)),b'\x07')
        u.mem_write(context+0x408,b'\x09');u.mem_write(context+0xfb0c,bytes(128));self.owner_pool(u)
        self.assertEqual(self.call(u,enter,[context,state,1234]),0xffffffff)
        self.assertEqual(bytes(u.mem_read(context+0x408,1)),b'\x09')

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
        report=self.build();u=self.machine(report);u.mem_map(0x51000000,0x20000)
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
        self.owner_pool(u,extra=128+12288)
        for data in (context+0x100,source+4,context+0xfb8c):
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
                    if failure=='frozen':
                        self.assertEqual(pixels,rendered)
                        self.assertEqual(self.call(u,report['symbols']['gr2_capture_frozen'],[context,1,0x50001000]),0)
                        self.assertEqual(bytes(u.mem_read(0x60000000,256)),pixels)
                        self.assertEqual(len(cache),3)
                        # Distinct kind3 output still needs its own rendering.
                        u.mem_write(0x60000200,y+chroma)
                        u.mem_write(0x5000a300,b'BUFF'+struct.pack('>5I',0x60000200,256,0,0,256))
                        for offset,value in ((0x200,0x5000a300),(0x20c,0x5000a100),(0x3ec,(4<<16)|32)):u.mem_write(context+offset,struct.pack('>I',value))
                        third=bytearray(descriptor);struct.pack_into('>I',third,0,0x60000200);u.mem_write(0x50001000,bytes(third))
                        self.assertEqual(self.call(u,report['symbols']['gr2_capture_frozen'],[context,3,0x50001000]),0)
                        self.assertEqual(bytes(u.mem_read(0x60000200,256)),pixels)
                        self.assertEqual(len(cache),5)
                        self.assertEqual(struct.unpack('>I',u.mem_read(context+0xfb0c+120,4))[0],5)
                    elif mode==0x13:rendered=pixels
                    self.assertNotEqual(bytes(u.mem_read(0x60000000,256)),y+chroma)
