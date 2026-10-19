"""Stage profiling must preserve JPEG pixels and avoid timed-region SD writes."""
import struct
import tempfile
import unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE,UC_HOOK_INTR
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R12,UC_ARM_REG_PC,UC_ARM_REG_LR
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_capture as capture

class CaptureProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        capture.M10VCaptureTests.setUpClass()
        cls.addClassCleanup(capture.M10VCaptureTests.doClassCleanups)
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.manifest=build(Path(cls.tmp.name),debug_mode=True,profile_mode=True)
        cls.code=(Path(cls.tmp.name)/'m10v-library-arm.bin').read_bytes()

    def fixture(self,film=66,clock_error=0):
        hcase=capture.M10VCaptureTests()
        hcase.debug_manifest,hcase.debug_code=self.manifest,self.code
        h,u,context,y,uv,cache,frees,*_=hcase.fixture(film=film,raw=1,raw_bank=0xa3000000,debug=True,stamp=0)
        u.mem_map(0x53050000,4096)
        u.mem_write(0x53050000,capture.M10VCaptureTests.official[0x50000:0x51000])
        ticks=[0xffffff00];saw_flush=[]
        def service(uc,number,data):
            # Execute the exact official facade; substitute only the kernel
            # SVC boundary, whose tick source is unavailable in emulation.
            self.assertEqual(uc.reg_read(UC_ARM_REG_PC),0x53050b90)
            self.assertEqual(uc.reg_read(UC_ARM_REG_R12),0x80510100)
            ticks[0]+=100
            pointer=uc.reg_read(UC_ARM_REG_R0)
            uc.mem_write(pointer,struct.pack('<II',ticks[0]>>32,ticks[0]&0xffffffff))
            uc.reg_write(UC_ARM_REG_R0,clock_error&0xffffffff)
        u.hook_add(UC_HOOK_INTR,service)
        def timer(uc,pc,size,data):
            if pc==self.manifest['symbols']['m10v_debug_batch']:
                saw_flush.append(bytes(uc.mem_read(0x55010000,len(y)))!=bytes(y))
        u.hook_add(UC_HOOK_CODE,timer)
        return h,u,context,y,uv,saw_flush

    def test_timing_is_stack_owned_and_flushes_once_after_pixels_changed(self):
        for film in (33,66,67):
            h,u,context,y,uv,flushes=self.fixture(film)
            self.assertEqual(h.call(u,'m10v_capture_library',context),0)
            marks=[e for e in h.capture_events if e[0]==150]
            self.assertEqual([e[2] for e in marks],list(range(1,13)))
            clocks=[(e[4]<<32)|e[3] for e in marks]
            self.assertEqual([b-a for a,b in zip(clocks,clocks[1:])],[100]*11)
            self.assertEqual(flushes,[True])
            self.assertEqual([e[1] for e in marks],[context]*12)

    def test_profile_pixels_match_release_for_all_reported_films(self):
        for film in (33,66,67):
            h,u,context,y,uv,_=self.fixture(film)
            self.assertEqual(h.call(u,'m10v_capture_library',context),0)
            normal=capture.M10VCaptureTests()
            h0,u0,c0,y0,uv0,*_=normal.fixture(film=film,raw=1,raw_bank=0xa3000000,stamp=0)
            self.assertEqual(h0.call(u0,'m10v_capture_library',c0),0)
            self.assertEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(u0.mem_read(0x55010000,len(y0))))
            self.assertEqual(bytes(u.mem_read(0x55020000,len(uv))),bytes(u0.mem_read(0x55020000,len(uv0))))

    def test_clock_failure_cannot_suppress_image_processing(self):
        h,u,context,y,uv,flushes=self.fixture(clock_error=-5)
        self.assertEqual(h.call(u,'m10v_capture_library',context),0)
        self.assertNotEqual(bytes(u.mem_read(0x55010000,len(y))),bytes(y))
        self.assertTrue(all(e[2]&0x80000000 for e in h.capture_events if e[0]==150))
        self.assertEqual(flushes,[True])

    def test_profile_requires_debug_and_has_no_effect_in_release(self):
        with self.assertRaises(ValueError):build(Path(self.tmp.name)/'invalid',profile_mode=True)

    def test_official_svc_table_routes_to_unscaled_operating_time_counter(self):
        # Independently follow the official negative function-code dispatch.
        # The adjacent get-time service adds wall-clock offset; this getter
        # copies boot time directly. The timer advances it by TTimPeriod (ms).
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
        from unicorn.arm_const import UC_ARM_REG_SP
        official=capture.M10VCaptureTests.official
        word=lambda address:struct.unpack_from('<I',official,address-0x53000000)[0]
        table=word(0x530716d4)
        getter=word(table+(-32687)*4)
        self.assertEqual(getter,0x53067c24)
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x53000000,0x100000)
        u.mem_write(0x53000000,official[:0x100000])
        u.mem_map(0x55000000,0x100000);u.mem_map(0x557f0000,0x10000)
        def locks(uc,pc,size,data):
            if pc in (0x5304fa88,0x5304fa98,0x53051360,0x530513e4):
                uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,locks)
        for ticks in (41668,0x100000000+41668):
            u.mem_write(0x557f25b8,struct.pack('<Q',ticks))
            u.reg_write(UC_ARM_REG_R0,0x55001000);u.reg_write(UC_ARM_REG_SP,0x550fe000);u.reg_write(UC_ARM_REG_LR,0x550ff000)
            u.emu_start(getter,0x550ff000,count=1000)
            self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x550ff000)
            self.assertEqual(u.reg_read(UC_ARM_REG_R0),0)
            self.assertEqual(bytes(u.mem_read(0x55001000,8)),struct.pack('<II',ticks>>32,ticks&0xffffffff))
