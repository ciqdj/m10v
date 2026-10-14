import struct
import os
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
from scripts.build_gr3_camera_adapter import build_adapter
from scripts.build_gr3_menu_controls import build_menu_controls
from scripts.build_gr3_halation import build
from scripts.build_gr3_800t_trace import build_trace


class CameraAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TemporaryDirectory() as folder:
            build(folder)
            cls.core = (Path(folder) / 'halation-arm.bin').read_bytes()
        cls.adapters = {strength: build_adapter(1, 18, strength) for strength in (1, 2)}
        cls.trace_adapter = dict(build_trace())['adapter']

    def run_adapter(self, strength=1, raw=0, jpeg=1, tone=18, order=1, allocation=True, alias=False,
                    raw_alias=False, preview_alias=False, bad_topology=False, mode=0, scratch_raw=False,
                    metadata_alias=False, raw_config_ready=False, plane_gap=0,descriptor_padding=False,
                    chroma_address=None,raw_at_chroma=False,scratch_at_chroma=False,trace=False,raw_address=None,
                    halo_gain=4,halo_radius=4,halo_threshold=4,grain=0,profile=4,use_menu=False,stock_values=None,private_record=0x55007400):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for addr, size in ((0x540bb000, 16384), (0x536af000, 4096), (0x5383c000, 4096),
                           (0x55000000, 32768), (0x56000000, 12288),
                           (0x57000000, 4096), (0x58000000, 65536),(0x5320b000,4096),(0x53584000,4096)):
            u.mem_map(addr, size)
        u.mem_write(0x540bb000, self.adapters[strength]); u.mem_write(0x540bb800, self.core)
        if use_menu:
            u.mem_write(0x540be000,build_menu_controls())
            u.mem_write(0x55007200,struct.pack('<II',0,private_record))
            packed=halo_gain|(halo_radius<<4)|(halo_threshold<<8)|({0:0,1:1,4:2,7:3}[profile]<<12)|({0:0,2:1,4:2,8:3}[grain]<<16)
            if private_record==0x55007400:
                u.mem_write(private_record+0x1c0,b'\0')
                u.mem_write(private_record+0xb28,struct.pack('<8I',0x38564d52,1,0,packed,packed,packed,32,0x43464738))
        stages=[];trace_stats=[]
        if trace:
            u.mem_write(0x540bcc00,self.trace_adapter)
        ctx = bytearray(0x60); struct.pack_into('<I', ctx, 0, 0x53d0fbe0)
        for offset, value in ((0x30, 0x550001a8), (0x34, 0x55006000), (0x38, 0x55005000),
                              (0x3c, 0x550000b0), (0x48, 0x55000110), (0x4c, 0x55000130)):
            struct.pack_into('<I', ctx, offset, value)
        if bad_topology: struct.pack_into('<I', ctx, 0, 0)
        u.mem_write(0x550009b8, bytes(ctx))
        u.mem_write(0x55000018, struct.pack('<I', mode))
        u.mem_write(0x5500005c, struct.pack('<I', 0x55005000))
        u.mem_write(0x550044c8, struct.pack('<I', 0x55006000))
        u.mem_write(0x55005000, struct.pack('<I', 0x53d0fe60))
        u.mem_write(0x5500500c, bytes((jpeg, raw)))
        u.mem_write(0x5500677c, bytes((tone,)))
        for offset,value in ((0x77d,halo_gain),(0x77e,halo_radius),(0x77f,halo_threshold),
                             (0x781,profile),(0x784,grain)):
            u.mem_write(0x55006000+offset,bytes((value,)))
        if stock_values is not None:
            for offset,value in zip((0x77d,0x77e,0x77f,0x781,0x784),stock_values):u.mem_write(0x55006000+offset,bytes((value,)))
        u.mem_write(0x55000140, b'\x01')
        raw_source = 0x560002d0+plane_gap if raw_at_chroma else (0x56000000 if raw_alias else 0x59000000)
        if raw_address is not None:raw_source=raw_address
        u.mem_write(0x55000060, struct.pack('<I', raw_source))
        u.mem_write(0x55000a50, struct.pack('<II', 0x53d0fc30, raw_source))
        u.mem_write(0x55000a80, struct.pack('<I', 0x550001a8))
        u.mem_write(0x55000230, struct.pack('<I', 0x55007000))
        u.mem_write(0x55007000, struct.pack('<HH', 6112, 4064))
        w, h, stride, allocated = 32, 17, 40, 18
        capacity = stride * allocated
        main_start=0x55000000 if metadata_alias else 0x56000000
        chroma_start=chroma_address if chroma_address is not None else main_start+capacity+plane_gap
        descriptor = struct.pack('<4I8H', order, main_start, chroma_start, 0,
                                 w, h, stride, allocated, 0, 0, 2, 0)
        u.mem_write(0x550000b0, descriptor)
        if descriptor_padding:u.mem_write(0x550000cd,b'\xa5\x5a\x91')
        preview_start = 0x56000000 if preview_alias else 0x5a000000
        u.mem_write(0x55000110, struct.pack('<4I8H', 1, preview_start, preview_start + capacity+plane_gap,
                                         0, w, h, stride, allocated, 0, 0, 2, 0))
        if descriptor_padding:u.mem_write(0x5500012d,b'\x91\x5a\xa5')
        if not raw_config_ready:
            # Execute original constructor stores and JPEG-only SetupModuleConfig.
            # RAW's own setup is later in the real planner, not before this hook.
            original_path=Path(os.environ.get('GR3_RTOS_PATH','/tmp/m10v-800t-analysis/rtos.bin'))
            if not original_path.exists(): self.skipTest('requires locked original RTOS; set GR3_RTOS_PATH')
            firmware=original_path.read_bytes()
            if hashlib.sha256(firmware).hexdigest()!='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67':
                raise ValueError('pre-JPEG reproduction requires exact original RTOS')
            for address in (0x5350e000,0x5350f000,0x536a3000):
                u.mem_map(address,4096);u.mem_write(address,firmware[address-0x53000000:address-0x53000000+4096])
            u.mem_write(0x55000070,bytes(u.mem_read(0x55000110,32)))
            u.reg_write(UC_ARM_REG_R4,0x55000000);u.reg_write(UC_ARM_REG_R5,0)
            u.reg_write(UC_ARM_REG_R1,0x53d0fc30)
            u.emu_start(0x5350f658,0x5350f69c,count=100)
            u.reg_write(UC_ARM_REG_R0,0x55000000);u.reg_write(UC_ARM_REG_R4,0x55000000)
            u.reg_write(UC_ARM_REG_SP,0x5800fff0)
            u.emu_start(0x5350ea50,0x5350e6f0,count=1000)
            self.assertEqual(bytes(u.mem_read(0x55000a54,4)),bytes(4))
            self.assertEqual(bytes(u.mem_read(0x55000a80,4)),bytes(4))
        pixels = bytearray([24] * capacity+[165]*plane_gap+[128] * capacity)
        pixels[8 * stride + 16] = 255
        before = bytes(pixels); u.mem_write(0x56000000, before)
        calls = []
        def external(uc, address, size, data):
            if address==0x5320b31c:
                uc.reg_write(UC_ARM_REG_R0,0x55007200)
                uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
            if not use_menu and address==0x540be000:
                op=uc.reg_read(UC_ARM_REG_R0)
                packed=0x80000000|halo_gain|(halo_radius<<4)|(halo_threshold<<8)|(grain<<12)|(profile<<16)
                if strength==1:packed=(packed&~15)|(halo_gain>>1)
                uc.reg_write(UC_ARM_REG_R0,0 if op==5 else packed)
                uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
            if trace and address==0x540bc800:
                stages.append((uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)))
                stats_ptr=uc.reg_read(UC_ARM_REG_R2)
                if stats_ptr:trace_stats.append(struct.unpack('<8I',uc.mem_read(stats_ptr,32)))
                uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
            if address not in (0x536af2a8, 0x536af2e4, 0x5383c8a8): return
            calls.append((address, uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)))
            if address == 0x536af2a8:
                address = (0x560002d0+plane_gap) if scratch_at_chroma else (0x59000000 if scratch_raw else (0x56000000 if alias else 0x57000000))
                uc.reg_write(UC_ARM_REG_R0, address if allocation else 0)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        def write_guard(uc, access, address, size, value, data):
            if 0x58000000 <= address and address + size <= 0x5800fff0: return
            if 0x57000000 <= address and address + size <= 0x57000000 + 6 * w * h: return
            for start in (0x56000000,0x56000000+capacity+plane_gap):
                if start<=address<start+capacity:
                    offset=address-start
                    if offset//stride<h and offset%stride+size<=w:return
            self.fail(f'adapter wrote outside permitted regions: {address:#x}')
        u.hook_add(UC_HOOK_CODE, external); u.hook_add(UC_HOOK_MEM_WRITE, write_guard)
        u.reg_write(UC_ARM_REG_R0, 0x550009b8); u.reg_write(UC_ARM_REG_SP, 0x5800fff0)
        u.reg_write(UC_ARM_REG_LR, 0x536afffc)
        u.emu_start(0x540bcc00 if trace else 0x540bb000, 0x536afffc, count=2000000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC), 0x536afffc)
        self.assertEqual(u.reg_read(UC_ARM_REG_SP), 0x5800fff0)
        self.last_trace_stages=stages
        self.last_trace_stats=trace_stats
        return before, bytes(u.mem_read(0x56000000, len(before))), calls

    def test_trace_records_real_guard_exit_and_keeps_the_effect_identical(self):
        for options,stage in (({},100),({'raw':1,'raw_address':0xacebc470},100),
                              ({'tone':12},6),({'allocation':False},15),({'raw_alias':True},12)):
            before,after,calls=self.run_adapter(strength=2,**options)
            t_before,t_after,t_calls=self.run_adapter(strength=2,trace=True,**options)
            self.assertEqual((t_before,t_after,t_calls),(before,after,calls))
            self.assertEqual(self.last_trace_stages,[(stage,0x550009b8)])
            if stage==100:
                stats=self.last_trace_stats[0]
                self.assertEqual(stats[0:2],(0,255))
                self.assertGreater(stats[5],stats[4]);self.assertGreater(stats[7],stats[6])

    def test_camera_reported_high_raw_bank_does_not_skip_halation(self):
        # User's real M10V8.BIN: RAW+JPEG, mode0, tone18, CFA ACEBC470,
        # 6112x4064. No RAW memory is read or written by the adapter.
        before,after,calls=self.run_adapter(strength=2,raw=1,raw_address=0xacebc470)
        self.assertNotEqual(before,after)
        self.assertEqual([x[0] for x in calls],[0x536af2a8]+[0x5383c8a8]*4+[0x536af2e4])

    def test_camera_menu_gain_and_grain_reach_pixel_processing(self):
        before,after,calls=self.run_adapter(strength=2,halo_gain=0,grain=0)
        self.assertEqual(before,after)
        before,after,calls=self.run_adapter(strength=2,halo_gain=0,grain=8)
        self.assertNotEqual(before[:720],after[:720])
        self.assertEqual(before[720:],after[720:])

    def test_real_camera_trace_reaches_core_with_exact_addresses_and_geometry(self):
        # Replay the user's stage11 snapshot. The core is deliberately stubbed:
        # this verifies bridge arguments/guards, not full-image rendering.
        for traced in (False,True):
            with self.subTest(traced=traced):
                u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
                recipe,context=0x5c0047d0,0x5c005188
                y,chroma=0x626fe4c0,0x63f46500
                capacity=6144*4000
                regions=((0x540bb000,16384),(0x536af000,4096),(0x5383c000,4096),
                         (0x5c004000,24576),(0x59c74000,8192),(0x5e6a7000,8192),
                         (0x57000000,0x8a000),(0x58000000,65536))
                for address,size in regions:u.mem_map(address,size)
                for pointer in (y,chroma):
                    start=pointer&~4095
                    u.mem_map(start,((pointer+capacity-start+4095)//4096)*4096)
                u.mem_write(0x540bb020,self.adapters[2])
                u.mem_write(0x540bcc00,self.trace_adapter)
                words=(0x53d0fbe0,)+(0,)*11+(0x5c004978,0x5e6a71c0,0x59c750d0,
                       0x5c004880,0x5c0048a0,0x5c0048c0,0x5c0048e0,0x5c004900,
                       0x5c004918,0x5c004930,0x5c004948,0x53d0fbf0)
                u.mem_write(context,struct.pack('<24I',*words))
                for offset,value in ((0x18,0),(0x5c,0x59c750d0),(0x60,0xacebc470),
                                     (0x230,0x59c74868),(0x44c8,0x5e6a71c0)):
                    u.mem_write(recipe+offset,struct.pack('<I',value))
                desc=(0xaaaa8a01,y,chroma,0,0x0fa01770,0x0fa01800,0,0xaaaaaa02)
                u.mem_write(recipe+0xb0,struct.pack('<8I',*desc))
                u.mem_write(recipe+0x110,struct.pack('<8I',0xaa8aea01,*desc[1:]))
                u.mem_write(recipe+0x140,b'\x01')
                u.mem_write(0x59c750d0,struct.pack('<I',0x53d0fe60))
                u.mem_write(0x59c750dc,b'\x01\x01')
                u.mem_write(0x5e6a793c,b'\x12')
                for offset,value in ((0x77d,4),(0x77e,4),(0x77f,4),(0x781,4),(0x784,0)):
                    u.mem_write(0x5e6a71c0+offset,bytes((value,)))
                u.mem_write(0x59c74868,struct.pack('<HH',6112,4064))
                calls=[];core_calls=[];stages=[]
                def external(uc,address,size,data):
                    if address==0x540be000:
                        result=0 if uc.reg_read(UC_ARM_REG_R0)==5 else 0x80040444
                        uc.reg_write(UC_ARM_REG_R0,result)
                        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
                    if address==0x540bc800:
                        stages.append(uc.reg_read(UC_ARM_REG_R0))
                    elif address==0x540bb800:
                        descriptor=struct.unpack('<9I',uc.mem_read(uc.reg_read(UC_ARM_REG_R0),36))
                        core_calls.append((descriptor,uc.reg_read(UC_ARM_REG_R1),
                                           uc.reg_read(UC_ARM_REG_R2),uc.reg_read(UC_ARM_REG_R3)))
                        uc.reg_write(UC_ARM_REG_R0,0)
                    elif address in (0x536af2a8,0x536af2e4,0x5383c8a8):
                        calls.append((address,uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)))
                        if address==0x536af2a8:uc.reg_write(UC_ARM_REG_R0,0x57000000)
                    else:return
                    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
                def writes(uc,access,address,size,value,data):
                    self.assertTrue(0x58000000<=address and address+size<=0x5800fff0,
                                    f'bridge wrote outside its stack: {address:#x}')
                u.hook_add(UC_HOOK_CODE,external);u.hook_add(UC_HOOK_MEM_WRITE,writes)
                u.reg_write(UC_ARM_REG_R0,context);u.reg_write(UC_ARM_REG_SP,0x5800fff0)
                u.reg_write(UC_ARM_REG_LR,0x536afffc)
                u.emu_start(0x540bcc00 if traced else 0x540bb020,0x536afffc,count=2000000)
                self.assertEqual(u.reg_read(UC_ARM_REG_PC),0x536afffc)
                self.assertEqual(core_calls,[((y,chroma,capacity,capacity,6000,4000,6144,6144,1),
                                              0x80040444,0x57000000,562500)])
                touched=3999*6144+6000
                self.assertEqual([row[1:] for row in calls[1:5]],[(y,touched),(chroma,touched)]*2)
                self.assertEqual([row[0] for row in calls],[0x536af2a8]+[0x5383c8a8]*4+[0x536af2e4])
                self.assertEqual(stages,[100] if traced else [])

    def test_raw_bank_holes_wrap_and_end_crossing_skip_without_writes(self):
        for address in (0x90000000,0xdf000000,0xffffff00,0xacebc471):
            before,after,calls=self.run_adapter(strength=2,raw=1,raw_address=address)
            self.assertEqual(before,after);self.assertEqual(calls,[])

    def test_actual_arm_bridge_calls_core_and_bounds_cache_then_frees(self):
        for strength in (1, 2):
            before, after, calls = self.run_adapter(strength=strength)
            self.assertNotEqual(before, after)
            self.assertEqual([x[0] for x in calls], [0x536af2a8]+[0x5383c8a8]*4+[0x536af2e4])
            self.assertEqual([x[1:] for x in calls[1:5]],[(0x56000000,672),(0x560002d0,672)]*2)

    def test_raw_only_other_tone_and_other_format_do_not_touch_buffers(self):
        for kwargs in ({'raw': 1, 'jpeg': 0}, {'jpeg': 0}, {'tone': 12}, {'order': 2}):
            before, after, calls = self.run_adapter(**kwargs)
            self.assertEqual(before, after); self.assertEqual(calls, [])

    def test_allocation_failure_and_alias_do_not_modify_pixels(self):
        for kwargs in ({'allocation': False}, {'alias': True}, {'scratch_raw': True}):
            before, after, calls = self.run_adapter(**kwargs)
            self.assertEqual(before, after)
            self.assertNotIn(0x5383c8a8, [row[0] for row in calls])

    def test_invalid_build_configuration_is_rejected(self):
        with self.assertRaises(ValueError): build_adapter(0, 18, 1)

    def test_cfa_alias_and_other_recipe_are_rejected_before_allocation(self):
        for kwargs in ({'raw_alias': True}, {'bad_topology': True}, {'mode': 2}, {'metadata_alias': True}):
            before, after, calls = self.run_adapter(**kwargs)
            self.assertEqual(before, after); self.assertEqual(calls, [])

    def test_raw_plus_jpeg_can_share_developed_preview_but_not_cfa(self):
        before, after, calls = self.run_adapter(raw=1, preview_alias=True)
        self.assertNotEqual(before, after)
        self.assertEqual(calls[-1][0], 0x536af2e4)

    def test_original_pre_jpeg_setup_does_not_require_later_raw_config(self):
        for raw in (0,1):
            before,after,calls=self.run_adapter(raw=raw,raw_config_ready=False)
            self.assertNotEqual(before,after)

    def test_padded_original_style_planes_are_processed_and_gap_is_untouched(self):
        gap=144*40+64
        before,after,calls=self.run_adapter(raw=1,plane_gap=gap,preview_alias=True,descriptor_padding=True)
        self.assertTrue(before!=after,'padded camera planes were silently skipped')
        self.assertEqual(after[720:720+gap],before[720:720+gap])

    def test_address_mode_ignores_uninitialized_padding_bytes(self):
        before,after,calls=self.run_adapter(raw=1,descriptor_padding=True)
        self.assertTrue(before!=after,'address-mode padding was interpreted as a field')

    def test_chroma_only_protected_aliases_and_plane_overlap_are_rejected(self):
        for kwargs in ({'raw_at_chroma':True},{'chroma_address':0x55000400},
                       {'scratch_at_chroma':True},{'chroma_address':0x56000004}):
            before,after,calls=self.run_adapter(raw=1,**kwargs)
            self.assertEqual(before,after)
            self.assertNotIn(0x5383c8a8,[row[0] for row in calls])

    def test_actual_private_menu_backend_feeds_capture_and_stock_colors_are_independent(self):
        for strength in (1,2):
            options=dict(strength=strength,halo_gain=5,halo_radius=1,halo_threshold=7,profile=4,grain=4)
            reference=self.run_adapter(**options)
            for values in ((0,0,0,0,0),(8,8,8,8,8)):
                self.assertEqual(self.run_adapter(**options,use_menu=True,stock_values=values),reference)
    def test_private_control_record_is_protected_from_jpeg_alias(self):
        before,after,calls=self.run_adapter(use_menu=True,private_record=0x56000000)
        self.assertEqual(before,after);self.assertEqual(calls,[])
