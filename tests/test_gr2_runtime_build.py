"""Execute the independently built BE32 GR II bridge, never a downloadable firmware."""
import tempfile
import unittest
from pathlib import Path
import struct
from tests.test_unity_update import ROOT,component

class Gr2RuntimeBuildTests(unittest.TestCase):
    def build(self):
        try:from scripts.build_gr2_runtime import build_gr2_runtime
        except ImportError:self.fail('GR II big-endian runtime builder is missing')
        code=component('gr2','b01firm8')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        report=build_gr2_runtime(code,{},Path(self.temp.name));return report

    def machine(self,report):
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_MODE_BIG_ENDIAN
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM|UC_MODE_BIG_ENDIAN)
        u.mem_map(0xa0798000,0x68000);u.mem_write(report['base'],bytes.fromhex(report['runtime_hex']))
        u.mem_map(0x50000000,0x20000);return u

    def call(self,u,entry,args):
        from unicorn import arm_const as r
        for reg,value in zip((r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2,r.UC_ARM_REG_R3),args):u.reg_write(reg,value)
        u.reg_write(r.UC_ARM_REG_SP,0x50018000);u.reg_write(r.UC_ARM_REG_LR,0x5001f000)
        u.emu_start(entry,0x5001f000,count=10000000)
        self.assertEqual(u.reg_read(r.UC_ARM_REG_PC),0x5001f000)
        return u.reg_read(r.UC_ARM_REG_R0)

    def test_be32_runtime_preserves_original_post_load_result_and_audits_all_sections(self):
        report=self.build();self.assertEqual(report['endianness'],'big');self.assertFalse(report['be8'])
        self.assertFalse(report['can_package']);self.assertLess(report['memory_bytes'],0x68000)
        u=self.machine(report)
        self.assertEqual(self.call(u,report['symbols']['gr2_post_load'],[]),0xffffffff)
        self.assertEqual(self.call(u,report['symbols']['gr2_post_load'],[]),0xffffffff)
        self.assertEqual(struct.unpack('>I',u.mem_read(report['symbols']['gr2_boot_count'],4))[0],2)
        self.assertEqual(report['undefined_symbols'],[])

    def test_compiled_date_bridge_validates_real_calendar_without_soft_float_helpers(self):
        report=self.build();u=self.machine(report);entry=report['symbols']['gr2_date_valid']
        for fields,valid in (((2024,2,29,23,59,59),1),((2100,2,29,0,0,0),0),((2026,10,20,0,0,0),1),((2026,13,1,0,0,0),0),((2026,1,1,0,60,0),0)):
            u.mem_write(0x50001000,struct.pack('>6H',*fields))
            with self.subTest(fields=fields):self.assertEqual(self.call(u,entry,[0x50001000]),valid)

    def test_compiled_capture_bridge_decodes_planar_frame_and_refuses_overlap_or_odd_width(self):
        report=self.build();u=self.machine(report);entry=report['symbols']['gr2_capture_decode']
        descriptor=bytearray(0x30);struct.pack_into('>3I',descriptor,0,0x60000000,0x64000000,(3264<<16)|4928)
        descriptor[0xd]=2;u.mem_write(0x50001000,bytes(descriptor))
        self.assertEqual(self.call(u,entry,[0x50001000,0x50002000]),1)
        values=struct.unpack('>11I',u.mem_read(0x50002000,44))
        self.assertEqual(values,(0x60000000,0x60000000+4928*3264,0x60000000+(4928+2464)*3264,4928*3264,2464*3264,2464*3264,4928,3264,4928,2464,0x422))
        for offset,value in ((8,(3264<<16)|4927),(0x18,0x60000000)):
            changed=bytearray(descriptor);struct.pack_into('>I',changed,offset,value);u.mem_write(0x50001000,bytes(changed));u.mem_write(0x50002000,b'\xa5'*44)
            self.assertEqual(self.call(u,entry,[0x50001000,0x50002000]),0)
            self.assertEqual(bytes(u.mem_read(0x50002000,44)),b'\xa5'*44)

    def test_compiled_plane_arithmetic_matches_original_encoder_across_alignment_boundaries(self):
        from scripts.analyze_gr2_native_contract import probe_jpeg_input
        report=self.build();u=self.machine(report);entry=report['symbols']['gr2_capture_decode'];code=component('gr2','b01firm8')
        for width,height,kind in ((642,426,2),(642,426,3),(642,426,4),(4928,3264,2)):
            expected=probe_jpeg_input(code,width,height,format_kind=kind)
            descriptor=bytearray(48);struct.pack_into('>3I',descriptor,0,0x60000000,0x64000000,(height<<16)|width);descriptor[13]=kind
            u.mem_write(0x50001000,bytes(descriptor))
            with self.subTest(width=width,height=height,kind=kind):
                self.assertEqual(self.call(u,entry,[0x50001000,0x50002000]),1)
                values=struct.unpack('>11I',u.mem_read(0x50002000,44))
                self.assertEqual(values[:3],(expected['y'],expected['u'],expected['v']))
                self.assertEqual(values[8:11],(expected['y_stride'],expected['chroma_stride'],expected['input_format']))

    def test_native_startup_chain_returns_to_stock_final_callbacks_after_record_14_load(self):
        from scripts.analyze_unity_runtime import probe_gr2_startup_order
        report=self.build()
        traced=probe_gr2_startup_order(component('gr2','b01firm8'),native_runtime=report)
        self.assertEqual(traced['post_load_return'],0xffffffff)
        self.assertEqual(traced['native_boot_count'],1)
        self.assertTrue(traced['native_loaded_by_original_indexed_loader'])
        self.assertEqual(traced['events'][-4:],[['post_load',0],['phase',0],['phase',0xffffffff],['finalize',0xffffffff]])

    def test_planar_chroma_conversion_is_reversible_for_odd_plane_lengths_and_preserves_guards(self):
        report=self.build();self.assertIn('gr2_chroma_shuffle',report['symbols']);u=self.machine(report)
        for n in (1,2,3,7,16,17,31,320,1025):
            a=bytes(i%251 for i in range(n));b=bytes((i*7+93)%251 for i in range(n));address=0x50001004
            u.mem_write(address-4,b'\xa5'*4+a+b+b'\xa5'*4)
            with self.subTest(n=n):
                self.assertEqual(self.call(u,report['symbols']['gr2_chroma_shuffle'],[address,n,0]),1)
                self.assertEqual(bytes(u.mem_read(address,2*n)),bytes(x for pair in zip(a,b) for x in pair))
                self.assertEqual(self.call(u,report['symbols']['gr2_chroma_shuffle'],[address,n,1]),1)
                self.assertEqual(bytes(u.mem_read(address-4,2*n+8)),b'\xa5'*4+a+b+b'\xa5'*4)

    def test_capture_adapter_rejects_stride_overflow_before_converting_or_rendering(self):
        report=self.build();u=self.machine(report)
        self.call(u,report['symbols']['m10v_library_init'],[0x50001000])
        u.mem_write(0x50002000,b'\xa5'*32);u.mem_write(0x50003000,b'\xa5'*32)
        u.mem_write(0x50004000,struct.pack('>11I',0x50002000,0x50003000,0x50003010,32,16,16,8,4,8,0x80000004,0x422))
        u.mem_write(0x50018000,bytes(12))
        self.assertEqual(self.call(u,report['symbols']['gr2_render_planar'],[0x50004000,0x50001000,0,0]),0xffffffff)
        self.assertEqual(bytes(u.mem_read(0x50002000,32))+bytes(u.mem_read(0x50003000,32)),b'\xa5'*64)

    def test_compiled_allocator_handles_real_rtos_pool_exhaustion_and_release(self):
        from scripts.analyze_gr2_native_contract import probe_rtos_pool
        report=self.build();self.assertIn('gr2_allocate',report['symbols'])
        result=probe_rtos_pool(component('gr2','b01firm8'),native_runtime=report)
        self.assertTrue(result['native_allocation_in_pool'])
        self.assertEqual(result['native_exhausted_pointer'],0)
        self.assertEqual(result['native_release_returned'],0)
        self.assertEqual(result['native_reallocated_pointer'],result['native_allocated_pointer'])
        self.assertEqual(result['helpers_intercepted'],[])

    def test_compiled_clock_bridge_accepts_zero_seconds_and_rejects_invalid_dates_atomically(self):
        from scripts.analyze_gr2_native_contract import probe_rtc_get_time
        report=self.build();self.assertIn('gr2_read_clock',report['symbols'])
        for fields in ((2026,10,20,18,30,0),(2024,2,29,0,0,59)):
            result=probe_rtc_get_time(component('gr2','b01firm8'),fields,native_runtime=report)
            self.assertEqual(result['returned'],1);self.assertEqual(result['fields'],list(fields))
        invalid=probe_rtc_get_time(component('gr2','b01firm8'),(2100,2,29,0,0,0),native_runtime=report)
        self.assertEqual(invalid['returned'],0);self.assertEqual(invalid['output_hex'],'a5'*12)
