"""GR II's original independently pitched, separated planes must retain padding."""
import struct,unittest,zlib
from tests import test_gr2_runtime_build as runtime_tests

class Gr2PlanarLayoutTests(unittest.TestCase):
    build=runtime_tests.Gr2RuntimeBuildTests.build
    call=runtime_tests.Gr2RuntimeBuildTests.call
    machine=runtime_tests.Gr2RuntimeBuildTests.machine
    def test_padded_planes_match_paired_renderer_and_borrow_failure_never_changes_source(self):
        from unicorn import UC_HOOK_CODE,arm_const as r
        runtime=self.build();u=self.machine(runtime);u.mem_map(0xa029a000,4096)
        for address,size in ((0x60000000,0x40000),(0x61000000,4096),(0x62000000,4096),(0x63000000,0x20000)):u.mem_map(address,size)
        width,height=32,8;y,u_plane,v=0x60000020,0x60010020,0x60020020
        work,reference,scratch=0x61000020,0x62000020,0x63000000;handle=0x50005000
        behavior={'available':True,'capacity':512};calls=[]
        def sdk(machine,address,size,unused):
            if address==0xa029a94e:
                self.assertEqual(machine.reg_read(r.UC_ARM_REG_R0),0x2e);self.assertEqual(machine.reg_read(r.UC_ARM_REG_R1),0)
                value=handle if behavior['available'] else 0;calls.append('borrow')
                machine.mem_write(handle,b'BUFF'+struct.pack('>5I',behavior.get('data',work),0,0,0,behavior['capacity']))
            else:
                pointer=machine.reg_read(r.UC_ARM_REG_R0);self.assertEqual(struct.unpack('>I',machine.mem_read(pointer,4))[0],handle)
                machine.mem_write(pointer,bytes(4));calls.append('release');value=0
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for address in (0xa029a94e,0xa029aa1a):u.hook_add(UC_HOOK_CODE,sdk,begin=address,end=address)
        self.call(u,runtime['symbols']['m10v_library_init'],[0x50001000])
        state=bytearray(u.mem_read(0x50001000,104))
        def render(name,image):
            u.mem_write(0x50018000,struct.pack('>3I',1234,scratch,0x20000))
            return self.call(u,runtime['symbols'][name],[image,0x50001000,0,0])
        for film,ys,cs in [*((film,64,48) for film in range(1,79)),(78,4960,2496)]:
            with self.subTest(film=film,ys=ys,cs=cs):
                state[12:14]=struct.pack('>H',film);state[14]=2;state[16]=3
                struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50001000,bytes(state))
                before=bytearray(b'\xa5'*0x40000);luma=bytes((i*31+9)%256 for i in range(256));chroma=bytes((i*7+83)%256 for i in range(256))
                for row in range(height):
                    before[y-0x60000000+row*ys:y-0x60000000+row*ys+width]=luma[row*width:(row+1)*width]
                    before[u_plane-0x60000000+row*cs:u_plane-0x60000000+row*cs+width//2]=chroma[row*width:(row+1)*width:2]
                    before[v-0x60000000+row*cs:v-0x60000000+row*cs+width//2]=chroma[row*width+1:(row+1)*width:2]
                u.mem_write(0x60000000,bytes(before));u.mem_write(work-32,b'\x5a'*(512+64));u.mem_write(reference,luma+chroma)
                u.mem_write(0x50002000,struct.pack('>7I',reference,reference+256,256,256,width,height,width))
                self.assertEqual(render('m10v_library_render',0x50002000),0);expected_pixels=bytes(u.mem_read(reference,512));expected=bytearray(before)
                for row in range(height):
                    expected[y-0x60000000+row*ys:y-0x60000000+row*ys+width]=expected_pixels[row*width:(row+1)*width]
                    expected[u_plane-0x60000000+row*cs:u_plane-0x60000000+row*cs+width//2]=expected_pixels[256+row*width:256+(row+1)*width:2]
                    expected[v-0x60000000+row*cs:v-0x60000000+row*cs+width//2]=expected_pixels[257+row*width:256+(row+1)*width:2]
                u.mem_write(0x50003000,struct.pack('>11I',y,u_plane,v,ys*height,cs*height,cs*height,width,height,ys,cs,0x422));calls.clear()
                self.assertEqual(render('gr2_render_planar',0x50003000),0)
                self.assertEqual(bytes(u.mem_read(0x60000000,0x40000)),bytes(expected));self.assertEqual(calls,['borrow','release'])
                self.assertEqual(bytes(u.mem_read(work-32,32))+bytes(u.mem_read(work+512,32)),b'\x5a'*64)
        for available,capacity,data,expected_calls in ((False,512,work,['borrow']),(True,511,work,['borrow','release']),(True,512,y,['borrow','release'])):
            behavior.update(available=available,capacity=capacity,data=data);u.mem_write(0x60000000,bytes(before));calls.clear()
            self.assertEqual(render('gr2_render_planar',0x50003000),0xfffffffe)
            self.assertEqual(bytes(u.mem_read(0x60000000,0x40000)),bytes(before));self.assertEqual(calls,expected_calls)

        behavior.update(available=True,capacity=512,data=work);state[52]=1;struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50001000,bytes(state));calls.clear()
        self.assertEqual(render('gr2_render_planar',0x50003000),0xffffffff)
        self.assertEqual(bytes(u.mem_read(0x60000000,0x40000)),bytes(before));self.assertEqual(calls,['borrow','release'])
        # The same borrowed adapter must preserve frozen custom LUTs and mark
        # the original image only after successful pixel copy-back.
        import subprocess
        from tests.test_unity_update import ROOT
        from tests.test_gr2_capture import Gr2CaptureTests
        record=subprocess.check_output(['node','--input-type=module','-e',"import {customFilmRecord} from './node/gr3-sd-film-pack.mjs';process.stdout.write(customFilmRecord({name:'Padded LUT',rgb:Buffer.from(Array.from({length:6591},(_,i)=>(i*7+83)%256))},79));"],cwd=ROOT)
        u.mem_map(0x51000000,0x20000);u.mem_map(0x64000000,0x4000);u.mem_map(0x65000000,4096)
        context=0x51000008;u.mem_write(context-8,b'IMG '+bytes(4));Gr2CaptureTests.owner_pool(self,u,extra=128+12288+16)
        state[52]=0;state[62]=1;struct.pack_into('>H',state,12,79);struct.pack_into('>I',state,100,zlib.crc32(state[:100]));u.mem_write(0x50001000,bytes(state));u.mem_write(0x64000000,record)
        u.mem_write(0x50018000,struct.pack('>I',0x64000000));self.assertEqual(self.call(u,runtime['symbols']['gr2_frame_freeze_custom'],[context,0x50001000,0,1234]),1)
        u.mem_write(reference,luma+chroma);u.mem_write(0x50018000,struct.pack('>6I',1234,scratch,0x20000,0,0x64000040,0x64000010))
        self.assertEqual(self.call(u,runtime['symbols']['m10v_library_render_custom'],[0x50002000,0x50001000,0,0]),0)
        custom_expected=bytes(u.mem_read(reference,512));expected=bytearray(before)
        for row in range(height):
            expected[y-0x60000000+row*ys:y-0x60000000+row*ys+width]=custom_expected[row*width:(row+1)*width]
            expected[u_plane-0x60000000+row*cs:u_plane-0x60000000+row*cs+width//2]=custom_expected[256+row*width:256+(row+1)*width:2]
            expected[v-0x60000000+row*cs:v-0x60000000+row*cs+width//2]=custom_expected[257+row*width:256+(row+1)*width:2]
        for offset,pointer,data,length,capacity in ((0x1f4,0x5000a000,0x60000000,0x40000,0x40000),(0x204,0x5000a100,0x65000000,0,4096)):
            u.mem_write(context+offset,struct.pack('>I',pointer));u.mem_write(pointer,b'BUFF'+struct.pack('>5I',data,length,0,0,capacity))
        u.mem_write(context+0x3e4,struct.pack('>I',(height<<16)|width))
        descriptor=bytearray(48);struct.pack_into('>3I',descriptor,0,y,0x65000000,(height<<16)|width);descriptor[13]=2
        struct.pack_into('>4I',descriptor,24,u_plane,v,ys,cs);u.mem_write(0x50006000,bytes(descriptor))
        def platform(machine,address,size,unused):
            value=scratch if address==runtime['symbols']['gr2_allocate'] else 1 if address in (runtime['symbols']['gr2_cache_before'],runtime['symbols']['gr2_cache_after']) else 0
            machine.reg_write(r.UC_ARM_REG_R0,value);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
        for name in ('gr2_allocate','gr2_release','gr2_cache_before','gr2_cache_after'):u.hook_add(UC_HOOK_CODE,platform,begin=runtime['symbols'][name],end=runtime['symbols'][name])
        u.mem_write(0x60000000,bytes(before));calls.clear();behavior['available']=False
        self.assertEqual(self.call(u,runtime['symbols']['gr2_capture_frozen'],[context,1,0x50006000]),0xfffffffe)
        self.assertEqual(bytes(u.mem_read(0x60000000,0x40000)),bytes(before));self.assertEqual(calls,['borrow'])
        behavior['available']=True;calls.clear()
        self.assertEqual(self.call(u,runtime['symbols']['gr2_capture_frozen'],[context,1,0x50006000]),0)
        self.assertEqual(bytes(u.mem_read(0x60000000,0x40000)),bytes(expected));self.assertEqual(calls,['borrow','release'])
        self.assertEqual(bytes(u.mem_read(context+0xfb8c,12288)),record)
        calls.clear();self.assertEqual(self.call(u,runtime['symbols']['gr2_capture_frozen'],[context,1,0x50006000]),0);self.assertEqual(calls,[])
