"""Execute the linked M10V ARM runtime; camera services are not emulated."""
import ctypes as C
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_EXEC
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
from unicorn.arm_const import UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12, UC_ARM_REG_CPSR
from scripts.build_gr3_m10v_library import build
from tests import test_gr3_m10v_library as host_tests
State, Image, Date = host_tests.State, host_tests.Image, host_tests.Date


class FilmLibraryArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        cls.manifest = build(Path(cls.tmp.name))
        cls.code = (Path(cls.tmp.name) / 'm10v-library-arm.bin').read_bytes()
        host_tests.NativeFilmLibraryTests.setUpClass(); cls.addClassCleanup(host_tests.NativeFilmLibraryTests.doClassCleanups)

    def machine(self):
        base = self.manifest['base']; u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.mem_map(base, (len(self.code) + 4095) & ~4095); u.mem_write(base, self.code)
        u.mem_protect(base,(len(self.code)+4095)&~4095,UC_PROT_READ|UC_PROT_EXEC)
        u.mem_map(0x55000000, 0x100000)
        self.store_result = 0; self.saved = []; self.files = {}; self.file_calls = []
        self.focus = 0; self.current_tone = 18; self.native_tones = []; self.redraws = 0; self.captions = []; self.forwarded = []
        for address in (0x53828000, 0x53825000): u.mem_map(address, 8192)
        u.mem_write(0x55004008, struct.pack('<I', 0x55004100))
        u.mem_write(0x55004100, struct.pack('<I', 0x55004200))
        u.mem_write(0x55004220, b'\x01')
        u.mem_write(0x55068200, bytes([18]) + bytes(31))
        u.mem_write(0x55005174, struct.pack('<I', 0x55005200))
        u.mem_write(0x55005160, struct.pack('<I', 0x55005300))
        for address in (0x5320a000, 0x532bd000, 0x53394000, 0x53396000, 0x531ac000): u.mem_map(address, 8192)
        def services(uc, address, size, data):
            if address == 0x550ff100:
                self.saved.append(bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R1), C.sizeof(State))))
                uc.reg_write(UC_ARM_REG_R0, self.store_result & 0xffffffff)
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif address == 0x53828014:
                uc.reg_write(UC_ARM_REG_R0, 0x55004000); uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif address in (0x53825648, 0x53825fa8):
                fs, name, length, buffer = [uc.reg_read(r) for r in
                    (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
                self.assertEqual(fs, 0x55004200); self.assertIn(length,(C.sizeof(State),64,44))
                filename = bytes(uc.mem_read(name, 12)).split(b'\0')[0].decode()
                self.assertIn(filename, ('M10V4A.bin','M10V4B.bin','M10V3A.bin','M10V3B.bin','M10V2A.bin','M10V2B.bin','M10V0.bin','M10V1.bin'))
                self.file_calls.append((address, filename))
                result = 0
                if address == 0x53825fa8 and self.store_result == 0:
                    self.files[filename] = bytes(uc.mem_read(buffer, length)); result = 1
                elif address == 0x53825648 and filename in self.files and len(self.files[filename])==length:
                    uc.mem_write(buffer, self.files[filename]); result = 1
                uc.reg_write(UC_ARM_REG_R0, result); uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif address in (0x5320ad88, 0x5320ba9c, 0x532bd6b4, 0x53394820, 0x53395430, 0x531ac074, 0x53396f80):
                if address == 0x5320ad88: uc.reg_write(UC_ARM_REG_R0, 0x55006000)
                elif address == 0x5320ba9c: uc.reg_write(UC_ARM_REG_R0, 0x55068200)
                elif address == 0x532bd6b4: uc.reg_write(UC_ARM_REG_R0, self.current_tone)
                elif address == 0x53394820: uc.reg_write(UC_ARM_REG_R0, self.focus)
                elif address == 0x53395430: self.focus = uc.reg_read(UC_ARM_REG_R1)
                elif address == 0x531ac074: self.redraws += 1
                elif address == 0x53396f80: self.captions.append(uc.reg_read(UC_ARM_REG_R1))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            elif base <= address < base + 0x100 and (address - base) % 16 == 0:
                offset = address - base; self.forwarded.append(offset)
                if offset == 0:
                    self.current_tone = uc.reg_read(UC_ARM_REG_R1)
                    self.native_tones.append(self.current_tone)
                if offset == 0x80: uc.reg_write(UC_ARM_REG_R0, 12)
                if offset == 0x90: uc.reg_write(UC_ARM_REG_R0, 11 + uc.reg_read(UC_ARM_REG_R1))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE, services); return u

    def call(self, u, name, *args):
        sp = 0x550fe000; stop = 0x550ff000
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args[:4]):
            u.reg_write(reg, value)
        for i, value in enumerate(args[4:]): u.mem_write(sp + i * 4, struct.pack('<I', value))
        u.reg_write(UC_ARM_REG_SP, sp); u.reg_write(UC_ARM_REG_LR, stop)
        u.emu_start(self.manifest['symbols'][name], stop, count=20000000)
        self.assertEqual(u.reg_read(UC_ARM_REG_PC), stop)
        result = u.reg_read(UC_ARM_REG_R0)
        return result if result < 0x80000000 else result - 0x100000000

    def test_icon_catalog_and_five_slots_follow_selected_films(self):
        u=self.machine()
        for film in range(1,66):
            tone=144+film-1 if film<=32 else 213 if film==33 else 256+film-34
            self.assertEqual(self.call(u,'m10v_menu_icon',0,tone),670+film)
        state=0x55008000
        self.call(u,'m10v_library_init',state)
        self.assertEqual(self.call(u,'m10v_camera_library_select',state,1,65),0)
        self.assertEqual(self.call(u,'m10v_menu_icon',0,18),735)
        self.assertEqual(self.call(u,'m10v_menu_icon',0,209),735)
        self.assertEqual(self.call(u,'m10v_menu_icon',0,21),703)

    def test_slot_names_follow_saved_films_in_main_and_slot_selection_lists(self):
        u = self.machine(); state = 0x55008000
        self.call(u, 'm10v_library_init', state)
        # Catalog IDs and captions are independently assigned: 33 is 800T;
        # legacy catalog 34..65 occupies captions 879..910.
        for slot, film, caption in [(0, 1, 786), (1, 64, 909), (2, 56, 901),
                                    (3, 54, 899), (4, 33, 860)]:
            self.assertEqual(self.call(u, 'm10v_camera_library_select', state, slot, film), 0)
            tone = (12, 18, 19, 20, 21)[slot]
            self.assertEqual(self.call(u, 'm10v_menu_name', 0, tone), caption)
            self.assertEqual(self.call(u, 'm10v_menu_name', 0, 208 + slot), caption)
        self.assertEqual(self.call(u, 'm10v_camera_library_select', state, 4, 65), 0)
        self.assertEqual(self.call(u, 'm10v_menu_name', 0, 21), 910)
        self.assertEqual(self.call(u, 'm10v_menu_name', 0, 212), 910)

    def test_open_library_targets_highlighted_slot_instead_of_entry_snapshot(self):
        u = self.machine(); state = 0x55008000; model = 0x55068200
        self.call(u, 'm10v_library_init', state)
        self.assertEqual(self.call(u, 'm10v_camera_library_select', state, 4, 33), 0)
        self.assertEqual(self.call(u, 'm10v_camera_library_halation', state, 4, 8, 1, 7, 3), 0)
        # Stock m[0] is the entry snapshot; browsing changed the active tone.
        self.current_tone = 21
        self.focus = 12; self.call(u, 'm10v_menu_confirm', 0x55005000)
        self.assertEqual(u.mem_read(model, 1), b'\x12')
        self.focus = 6; self.call(u, 'm10v_menu_confirm', 0x55005000)
        self.focus = 0; self.call(u, 'm10v_menu_confirm', 0x55005000)
        self.assertEqual(u.mem_read(model + 0x1d, 1), b'\x0b')
        self.assertEqual(self.focus, 8)
        self.assertFalse(self.native_tones)
        # Pick another slot without altering the stock cancellation snapshot.
        u.mem_write(model + 0x1d, b'\x06'); self.focus = 3
        self.call(u, 'm10v_menu_confirm', 0x55005000)
        self.assertEqual(u.mem_read(model, 1), b'\x12')
        self.assertEqual(u.mem_read(model + 0x1e, 1), b'\x14')

    def test_original_icon_dimensions_and_bitmap_pointer_with_flags_preserved(self):
        from subprocess import check_output
        root=Path(__file__).resolve().parents[1]
        js="import {readFileSync} from 'node:fs';import {officialResources} from './node/gr3-stock-presets.mjs';const {decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.RTOS.offset,s.RTOS.offset+s.RTOS.size));"
        rtos=check_output(['node','--input-type=module','-e',js],cwd=root)
        u=self.machine();u.mem_map(0x53209000,4096)
        table=self.manifest['icons']['table']
        for start,end in [(0x53209fb8,0x53209fec),(0x53209fec,0x5320a020)]:
            u.mem_write(start,rtos[start-0x53000000:end-0x53000000])
            u.mem_write(start,struct.pack('<I',0xe300329e+0x41)) # 670 -> 735
            low=start+20;high=start+24
            def mov(op,reg,val):return op|((val&0xf000)<<4)|(reg<<12)|(val&0xfff)
            u.mem_write(low,struct.pack('<II',mov(0xe3000000,3,table&65535),mov(0xe3400000,3,table>>16)))
            for identifier in [671,703,735,736]:
                u.reg_write(UC_ARM_REG_R1,identifier);u.reg_write(UC_ARM_REG_LR,0x550ff000)
                u.emu_start(start,0x550ff000,count=100)
                self.assertEqual(u.reg_read(UC_ARM_REG_R0),40 if identifier<=735 else 0)
        # Run the new pointer shim at the exact point where stock drawing
        # consumes an ICONBIN-relative word offset. Private pixels are ROM.
        for identifier in [548,671,703,735]:
            u.mem_write(0x55009024,struct.pack('<H',identifier))
            offset=(self.manifest['icons']['pixels']+(identifier-671)*6400)//4 if identifier>=671 else 1234
            for reg,val in [(UC_ARM_REG_R0,11),(UC_ARM_REG_R1,22),(UC_ARM_REG_R2,33),(UC_ARM_REG_R3,44),(UC_ARM_REG_R5,0x55009000),(UC_ARM_REG_R6,offset),(UC_ARM_REG_LR,0x57000000),(UC_ARM_REG_SP,0x550fe000)]:u.reg_write(reg,val)
            u.reg_write(UC_ARM_REG_CPSR,0xa00001d3)
            u.emu_start(self.manifest['symbols']['m10v_icon_pixels'],0x5320a838,count=100)
            self.assertEqual(u.reg_read(UC_ARM_REG_R12),offset*4+(0 if identifier>=671 else 0x57000000))
            for reg,val in [(UC_ARM_REG_R0,11),(UC_ARM_REG_R1,22),(UC_ARM_REG_R2,33),(UC_ARM_REG_R3,44),(UC_ARM_REG_SP,0x550fe000)]:self.assertEqual(u.reg_read(reg),val)
            self.assertEqual(u.reg_read(UC_ARM_REG_CPSR)&0xf8000000,0xa0000000)
        from PIL import Image as PILImage
        pixels=(root/'native/gr3/m10v_icons.rgba').read_bytes()
        for i in range(65):
            with PILImage.open(root/f'web/gr3/film-icons/{i+1:02d}.png') as im:self.assertEqual(im.convert('RGBA').tobytes(),pixels[i*6400:(i+1)*6400])
        red=pixels[32*6400+(8*40+20)*4:32*6400+(8*40+20)*4+4]
        self.assertGreater(red[0],red[1]*2)

    def test_official_list_consumer_allocates_35_rows_and_renders_33_visible_films(self):
        # The raw instruction fixture comes from the official decompression,
        # not a reimplementation of its row count/loop.
        from subprocess import check_output
        root = Path(__file__).resolve().parents[1]
        script = "import {readFileSync} from 'node:fs';import {decodeFrameMap} from './node/gr3-frames.mjs';import {inspectOfficial} from './node/firmware.mjs';const b=readFileSync('fwdc239b-offical.bin'),d=decodeFrameMap(b).decoded;let at=0;for(const row of inspectOfficial(b).sections){if(row.name==='RTOS'){process.stdout.write(d.subarray(at+16,at+row.size));break;}at+=row.size;}"
        rtos = check_output(['node','--input-type=module','-e',script],cwd=root)
        self.assertEqual(__import__('hashlib').sha256(rtos).hexdigest(), '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67')
        u = self.machine()
        u.mem_map(0x531ab000,4096);u.mem_map(0x532c2000,4096);u.mem_map(0x53293000,4096);u.mem_map(0x532a9000,4096);u.mem_map(0x533a1000,4096)
        for address,length in [(0x531abc18,36),(0x531ab7e4,0x130)]:
            u.mem_write(address,rtos[address-0x53000000:address-0x53000000+length])
        for address,name in [(0x532c2b7c,'m10v_menu_max_count'),(0x532c2a9c,'m10v_menu_count'),(0x532c2c80,'m10v_menu_index'),(0x532935dc,'m10v_menu_icon'),(0x532a9988,'m10v_menu_value_icon')]:
            delta=self.manifest['symbols'][name]-address-8
            u.mem_write(address,struct.pack('<I',0xea000000|((delta>>2)&0xffffff)))
        rows=[]
        def view(uc,address,size,data):
            if address == 0x5320b67c: uc.reg_write(UC_ARM_REG_R0,0x55007000)
            elif address == 0x53394758:
                index=uc.reg_read(UC_ARM_REG_R1);rows.append(index);self.assertLess(index,36)
                uc.reg_write(UC_ARM_REG_R0,0x55008000+index*4)
            elif address != 0x533a1734: return
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,view)
        u.reg_write(UC_ARM_REG_SP,0x550fe000);u.reg_write(UC_ARM_REG_LR,0x550ff000)
        u.emu_start(0x531abc18,0x550ff000,count=100000)
        self.assertEqual(u.reg_read(UC_ARM_REG_R0),36)
        u.mem_write(0x5506821d,b'\x02');u.mem_write(0x550051a9,b'\x24')
        u.reg_write(UC_ARM_REG_SP,0x550fe000);u.reg_write(UC_ARM_REG_LR,0x550ff000);u.reg_write(UC_ARM_REG_R0,0x55005000)
        u.emu_start(0x531ab7e4,0x550ff000,count=100000)
        self.assertEqual(rows,list(range(36)))

    def test_compiled_browser_defaults_initialize_exact_arm_state(self):
        initial = bytearray(104)
        struct.pack_into('<IHHI', initial, 0, 0x5630314d, 3, 104, 0)
        for i in range(5): struct.pack_into('<H6B', initial, 12+i*8, 65-i, i%4, (i+2)%4,8,1,7,3)
        initial[52:56] = bytes([2,3,2,1])
        for i in range(5):initial[56+i*8]=1;initial[59+i*8]=4
        struct.pack_into('<I', initial, 100, zlib.crc32(initial[:100]))
        with tempfile.TemporaryDirectory() as folder:
            manifest = build(Path(folder), initial_state_hex=initial.hex())
            code = (Path(folder)/'m10v-library-arm.bin').read_bytes()
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.mem_map(manifest['base'], (len(code)+4095)&~4095); u.mem_write(manifest['base'], code)
        u.mem_map(0x55000000, 0x100000)
        u.reg_write(UC_ARM_REG_SP,0x550fe000);u.reg_write(UC_ARM_REG_R0,0x55001000);u.reg_write(UC_ARM_REG_LR,0x550ff000)
        u.emu_start(manifest['symbols']['m10v_library_init'],0x550ff000,count=100000)
        self.assertEqual(bytes(u.mem_read(0x55001000,C.sizeof(State))),bytes(initial))
        self.assertEqual(manifest['initial_state_hex'],initial.hex())
        with tempfile.TemporaryDirectory() as folder:
            initial[52] = 9
            with self.assertRaises(ValueError): build(Path(folder), initial_state_hex=initial.hex())

    def test_arm_initialization_and_persist_failure_are_atomic(self):
        u = self.machine(); state = 0x55001000
        self.call(u, 'm10v_library_init', state)
        before = bytes(u.mem_read(state, C.sizeof(State)))
        self.assertEqual([s.film for s in State.from_buffer_copy(before).slots], [34,35,36,37,33])
        self.assertEqual(self.call(u, 'm10v_library_valid', state), 1)
        self.store_result = -1
        self.assertEqual(self.call(u, 'm10v_library_select', state, 4, 32, 0x550ff100, 0), -2)
        self.assertEqual(bytes(u.mem_read(state, C.sizeof(State))), before)
        self.store_result = 0
        self.assertEqual(self.call(u, 'm10v_library_select', state, 4, 32, 0x550ff100, 0), 0)
        self.assertEqual(State.from_buffer_copy(u.mem_read(state, C.sizeof(State))).slots[4].film, 32)
        self.assertEqual(self.call(u, 'm10v_library_valid', state), 1)

    def test_arm_all_effects_match_host_and_preserve_pixel_padding(self):
        u = self.machine(); state = 0x55001000
        self.call(u, 'm10v_library_init', state)
        self.call(u, 'm10v_library_select', state, 0, 2, 0x550ff100, 0)
        self.call(u, 'm10v_library_texture', state, 0, 2, 3, 0x550ff100, 0)
        self.call(u, 'm10v_library_stamp', state, 2, 2, 3, 1, 0x550ff100, 0)
        width, height, stride = 128, 96, 136; size = stride * height
        y = bytearray([64] * size + [173] * 32); uv = bytearray([128] * size + [197] * 32)
        for row in range(height):
            y[row * stride + width:(row + 1) * stride] = bytes([173] * 8)
            uv[row * stride + width:(row + 1) * stride] = bytes([197] * 8)
        y[48 * stride + 64] = 255
        date = Date(2026, 10, 14, 23, 59)
        u.mem_write(0x55002000, struct.pack('<7I', 0x55010000, 0x55020000, size, size, width, height, stride))
        u.mem_write(0x55003000, bytes(date)); u.mem_write(0x55010000, bytes(y)); u.mem_write(0x55020000, bytes(uv))
        u.mem_write(0x55030000, bytes([91]) * (2 * width * height + 32))
        self.assertEqual(self.call(u, 'm10v_library_render', 0x55002000, state, 0, 0x55003000,
                                  123, 0x55030000, 2 * width * height), 0)
        host_state = State.from_buffer_copy(u.mem_read(state, C.sizeof(State)))
        host_y = (C.c_uint8 * len(y)).from_buffer_copy(y); host_uv = (C.c_uint8 * len(uv)).from_buffer_copy(uv)
        scratch = (C.c_uint8 * (2 * width * height))()
        image = Image(host_y, host_uv, size, size, width, height, stride)
        self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(C.byref(image), C.byref(host_state),
                         0, C.byref(date), 123, scratch, len(scratch)), 0)
        self.assertEqual(bytes(u.mem_read(0x55010000, len(y))), bytes(host_y))
        self.assertEqual(bytes(u.mem_read(0x55020000, len(uv))), bytes(host_uv))
        self.assertEqual(bytes(u.mem_read(0x55030000 + 2 * width * height, 32)), bytes([91]) * 32)

    def test_internal_camera_journal_uses_native_fs_abi_and_survives_bad_latest_record(self):
        u = self.machine(); state = 0x55001000
        self.assertEqual(self.call(u, 'm10v_camera_library_load', state), 1)
        self.assertEqual(self.call(u, 'm10v_camera_library_select', state, 1, 32), 0)
        first = bytes(u.mem_read(state, C.sizeof(State)))
        self.assertIn('M10V4B.bin', self.files)
        self.assertEqual(self.call(u, 'm10v_camera_library_select', state, 4, 17), 0)
        self.assertIn('M10V4A.bin', self.files)
        fresh = 0x55002000
        self.assertEqual(self.call(u, 'm10v_camera_library_load', fresh), 0)
        self.assertEqual(bytes(u.mem_read(fresh, C.sizeof(State))), bytes(u.mem_read(state, C.sizeof(State))))
        damaged = bytearray(self.files['M10V4A.bin']); damaged[16] ^= 1
        self.files['M10V4A.bin'] = bytes(damaged)
        self.assertEqual(self.call(u, 'm10v_camera_library_load', fresh), 0)
        self.assertEqual(bytes(u.mem_read(fresh, C.sizeof(State))), first)
        self.store_result = -1; before = bytes(u.mem_read(fresh, C.sizeof(State)))
        self.assertEqual(self.call(u, 'm10v_camera_library_select', fresh, 0, 31), -2)
        self.assertEqual(bytes(u.mem_read(fresh, C.sizeof(State))), before)

    def test_menu_browsing_has_no_writes_and_confirm_installs_into_cached_target_slot(self):
        u = self.machine(); model = 0x55068200; controller = 0x55005000
        self.assertEqual(self.call(u, 'm10v_menu_count', model), 13)
        self.assertEqual(self.call(u, 'm10v_menu_index', model, 12), 128)
        self.call(u, 'm10v_menu_focus', controller, 12)
        self.assertFalse(self.native_tones); self.assertFalse(self.files)
        self.focus = 12; self.call(u, 'm10v_menu_confirm', controller)
        self.assertEqual(u.mem_read(model + 0x1d, 1), b'\x01')

        self.assertEqual(self.call(u, 'm10v_menu_count', model), 6)
        self.focus = 0; self.call(u, 'm10v_menu_confirm', controller)
        self.assertEqual(self.call(u, 'm10v_menu_count', model), 34)
        self.call(u, 'm10v_menu_focus', controller, 31)
        self.assertFalse(self.files); self.assertFalse(self.native_tones)
        self.focus = 31; self.call(u, 'm10v_menu_confirm', controller)
        state = State.from_buffer_copy(self.files['M10V4B.bin'])
        self.assertEqual(state.slots[1].film, 64)
        self.assertEqual(self.native_tones, [18])
        self.assertTrue(all(value < 25 for value in self.native_tones))
        self.assertEqual(u.mem_read(model + 0x1d, 1), b'\x01')

    def test_visible_catalog_index_names_and_icons_are_consistent(self):
        u=self.machine(); model=0x55068200
        u.mem_write(model+0x1d,b'\x02')
        self.assertEqual(self.call(u,'m10v_menu_max_count'),34)
        self.assertEqual(self.call(u,'m10v_menu_count',model),34)
        for index in range(34):
            tone=self.call(u,'m10v_menu_index',model,index)
            self.assertEqual(tone,213 if index==0 else 255+index)
            self.assertEqual(self.call(u,'m10v_menu_name',0,tone),860 if index==0 else 878+index)
            self.assertEqual(self.call(u,'m10v_menu_icon',0,tone),703+index)
        self.assertEqual(self.call(u,'m10v_menu_index',model,34),0)
        self.assertFalse(self.files);self.assertFalse(self.native_tones)

    def test_legacy_simulation_really_executes_on_arm_with_pixel_exact_host_output(self):
        for film in (34,38,45,65):
            u=self.machine();state=0x55001000
            self.call(u,'m10v_library_init',state);self.call(u,'m10v_library_select',state,0,film,0x550ff100,0)
            width,height,stride=32,16,40;size=stride*height
            y=bytes((i*37+19)%256 for i in range(size));uv=bytes((i*13+97)%256 for i in range(size))
            u.mem_write(0x55010000,y);u.mem_write(0x55020000,uv)
            u.mem_write(0x55002000,struct.pack('<7I',0x55010000,0x55020000,size,size,width,height,stride))
            self.assertEqual(self.call(u,'m10v_library_render',0x55002000,state,0,0,0,0,0),0)
            hstate=State.from_buffer_copy(u.mem_read(state,C.sizeof(State)));hy=(C.c_uint8*size).from_buffer_copy(y);hc=(C.c_uint8*size).from_buffer_copy(uv)
            image=Image(hy,hc,size,size,width,height,stride)
            self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(C.byref(image),C.byref(hstate),0,None,0,None,0),0)
            self.assertEqual(bytes(u.mem_read(0x55010000,size)),bytes(hy));self.assertEqual(bytes(u.mem_read(0x55020000,size)),bytes(hc))
            self.assertNotEqual(bytes(hy),y)
            for row in range(height):
                self.assertEqual(bytes(hy)[row*stride+width:(row+1)*stride],y[row*stride+width:(row+1)*stride])
                self.assertEqual(bytes(hc)[row*stride+width:(row+1)*stride],uv[row*stride+width:(row+1)*stride])

    def test_previous_800t_journal_migrates_without_reusing_aggressive_parameters(self):
        u=self.machine();addr=0x55001000
        self.call(u,'m10v_library_init',addr)
        old=bytearray(u.mem_read(addr,56))+bytearray(8);struct.pack_into('<HHI',old,4,2,64,19)
        struct.pack_into('<H6B',old,44,33,2,1,8,8,0,3)
        struct.pack_into('<I',old,60,zlib.crc32(old[:60]));self.files['M10V2B.bin']=bytes(old)
        self.assertEqual(self.call(u,'m10v_camera_library_load',addr),2)
        state=State.from_buffer_copy(u.mem_read(addr,C.sizeof(State)));v=state.slots[4]
        self.assertEqual([v.halo_gain,v.halo_spread,v.halo_threshold,v.halo_profile],[3,3,5,2])
        self.assertEqual([v.grain,v.soft],[2,1]);self.assertEqual(state.sequence,19)
        self.assertEqual(self.files['M10V2B.bin'],bytes(old))
        self.assertEqual(self.call(u,'m10v_camera_library_detail',addr,4,6,2,7,1,2),0)
        self.assertIn('M10V4A.bin',self.files)
        self.assertEqual(self.call(u,'m10v_camera_library_load',addr),0)
        state=State.from_buffer_copy(u.mem_read(addr,C.sizeof(State)))
        self.assertEqual([state.slots[4].halo_gain,state.slots[4].soft],[6,2])

    def test_old_44_byte_journal_migrates_without_overwriting_legacy_files(self):
        u=self.machine();old=bytearray(44)
        struct.pack_into('<IHHI',old,0,0x5630314d,1,44,7)
        for i in range(5):struct.pack_into('<HBB',old,12+4*i,33-i,i%4,(i+1)%4)
        old[32:36]=bytes([2,3,2,1]);struct.pack_into('<I',old,40,zlib.crc32(old[:40]))
        self.files['M10V1.bin']=bytes(old)
        self.assertEqual(self.call(u,'m10v_camera_library_load',0x55001000),3)
        state=State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(State)))
        self.assertEqual((state.version,state.size,state.sequence),(3,104,7))
        self.assertEqual([s.film for s in state.slots],[33,32,31,30,29])
        self.assertEqual([state.slots[0].halo_gain,state.slots[0].halo_spread,state.slots[0].halo_threshold,state.slots[0].halo_profile],[3,3,5,2])
        self.assertEqual(self.call(u,'m10v_camera_library_halation',0x55001000,0,8,1,7,3),0)
        self.assertEqual(self.files['M10V1.bin'],bytes(old));self.assertIn('M10V4A.bin',self.files)
        self.assertEqual(self.call(u,'m10v_camera_library_load',0x55001000),0)
        state=State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(State)));self.assertEqual(state.slots[0].halo_gain,8)

    def test_halation_menu_commits_three_controls_and_reopens_from_journal(self):
        u=self.machine();model=0x55068200;controller=0x55005000
        for mode,index in [(11,8),(12,1),(13,7)]:
            u.mem_write(model+0x1d,bytes([mode]));self.focus=index
            self.assertEqual(self.call(u,'m10v_menu_confirm',controller),0)
            self.assertEqual(u.mem_read(model+0x1d,1),b'\x0a')
        self.assertEqual(self.call(u,'m10v_camera_library_load',0x55001000),0)
        state=State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(State)));slot=state.slots[1]
        self.assertEqual([slot.halo_gain,slot.halo_spread,slot.halo_threshold,slot.halo_profile],[8,1,7,2])
        self.assertEqual(self.call(u,'m10v_library_valid',0x55001000),1)
        self.assertFalse(self.native_tones)

    def test_local_switch_pointer_relocation_is_bounded_to_arm_text(self):
        import subprocess,shutil
        from scripts.build_gr3_m10v_library import link_object
        compiler='/opt/homebrew/opt/llvm/bin/clang'
        if not Path(compiler).is_file():compiler=shutil.which('clang')
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            for addend in (0,4096):
                source=folder/'switch.S';obj=folder/'switch.o'
                source.write_text('.syntax unified\n.arm\n.text\n.global m10v_resource_primary\n.type m10v_resource_primary,%function\nm10v_resource_primary: bx lr\n.global m10v_resource_secondary\n.type m10v_resource_secondary,%function\nm10v_resource_secondary: bx lr\n.section .rodata\n.word m10v_resource_secondary+'+str(addend)+'\n')
                subprocess.run([compiler,'--target=armv7-none-eabi','-marm','-c',str(source),'-o',str(obj)],check=True,capture_output=True)
                if addend:
                    with self.assertRaisesRegex(ValueError,'leaves local ARM text'):link_object(obj.read_bytes(),0x540b6000,prefix='m10v_resource_')
                else:
                    code,symbols=link_object(obj.read_bytes(),0x540b6000,prefix='m10v_resource_')
                    self.assertEqual(struct.unpack_from('<I',code,len(code)-4)[0],symbols['m10v_resource_secondary'])

    def test_parameter_lists_focus_saved_values_without_writing_on_open(self):
        u=self.machine();model=0x55068200;controller=0x55005000
        self.call(u,'m10v_library_init',0x55001000)
        self.call(u,'m10v_camera_library_halation',0x55001000,1,8,1,7,3)
        before=dict(self.files)
        for index,expected in enumerate((8,1,7)):
            u.mem_write(model+0x1d,b'\x0a');self.focus=index
            self.call(u,'m10v_menu_confirm',controller)
            self.assertEqual(self.focus,expected)
            self.assertEqual(self.files,before)

    def test_menu_save_failure_remains_open_and_shows_error_without_native_tone_write(self):
        u = self.machine(); model = 0x55068200; controller = 0x55005000
        u.mem_write(model + 0x1d, b'\x02'); self.focus = 31; self.store_result = -1
        self.call(u, 'm10v_menu_confirm', controller)
        self.assertEqual(u.mem_read(model + 0x1d, 1), b'\x02')
        self.assertEqual(self.captions, [824]); self.assertFalse(self.native_tones)
        self.assertFalse(self.files)

    def test_menu_texture_and_timestamp_actions_commit_real_runtime_settings(self):
        u = self.machine(); model = 0x55068200; controller = 0x55005000
        for group, value in ((3, 3), (4, 2), (5, 2), (7, 2), (8, 3), (9, 1)):
            u.mem_write(model + 0x1d, bytes([group])); self.focus = value
            self.call(u, 'm10v_menu_confirm', controller)
        self.call(u, 'm10v_camera_library_load', 0x55001000)
        state = State.from_buffer_copy(u.mem_read(0x55001000, C.sizeof(State)))
        self.assertEqual((state.slots[1].grain, state.slots[1].soft), (3, 2))
        self.assertEqual((state.stamp, state.format, state.corner, state.color), (2, 2, 3, 1))
        self.assertEqual(state.sequence, 6)
        self.assertEqual(self.call(u, 'm10v_library_valid', 0x55001000), 1)
        self.assertEqual([self.call(u, 'm10v_menu_name', 0, 144 + i) for i in range(32)], list(range(786, 818)))

    def test_private_utf16_resource_hooks_preserve_stock_fallback_and_locale(self):
        u = self.machine(); stop = 0x550ff000; table = 0x55008000; stock_record = 0x55009000
        for language in (0, 1, 20): u.mem_write(0x55002bac + 4 * language, struct.pack('<I', table))
        for identifier in (4, 785): u.mem_write(table + identifier * 4, struct.pack('<I', stock_record))
        calls = []
        def done(uc, address, size, data):
            if address in (0x53396700, 0x5339710c): calls.append(address); uc.reg_write(UC_ARM_REG_PC, stop)
        u.hook_add(UC_HOOK_CODE, done)
        for language in (0, 1, 20):
            for identifier in (4, 785, 786, 817, 859):
                expected = (stock_record if identifier < 786 else self.manifest['resources']['descriptors'][identifier - 786])
                for symbol, continuation in (('m10v_resource_primary', 0x53396700), ('m10v_resource_secondary', 0x5339710c)):
                    u.reg_write(UC_ARM_REG_R7, identifier); u.reg_write(UC_ARM_REG_R9, language)
                    u.reg_write(UC_ARM_REG_R0, language); u.reg_write(UC_ARM_REG_R11, 0x550fe080)
                    u.emu_start(self.manifest['symbols'][symbol], stop, count=1000)
                    self.assertEqual(calls[-1], continuation)
                    self.assertEqual(u.reg_read(UC_ARM_REG_R7 if continuation == 0x53396700 else UC_ARM_REG_R3), expected)
                    if continuation == 0x5339710c: self.assertEqual(u.reg_read(UC_ARM_REG_R0), language)
                    else: self.assertEqual(u.reg_read(UC_ARM_REG_R0), 0x550fe080 - 0xb0)

    def test_v2_journal_migrates_to_v3_and_keeps_old_bytes_on_failed_save(self):
        u=self.machine();old=bytearray(64)
        struct.pack_into('<IHHI',old,0,0x5630314d,2,64,17)
        for i in range(5):struct.pack_into('<H6B',old,12+i*8,65-i,2,1,8,1,7,3)
        old[52:56]=bytes([2,3,2,1]);struct.pack_into('<I',old,60,zlib.crc32(old[:60]))
        self.files['M10V2B.bin']=bytes(old)
        self.assertEqual(self.call(u,'m10v_camera_library_load',0x55001000),2)
        s=State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(State)))
        self.assertEqual((s.version,s.size,s.sequence),(3,104,17))
        self.assertEqual([v.film for v in s.slots],[65,64,63,62,61])
        self.assertEqual(list(s.effects[0])[:5],[1,0,0,4,0])
        self.store_result=-1
        self.assertEqual(self.call(u,'m10v_camera_library_select',0x55001000,0,66),-2)
        self.assertEqual(self.files['M10V2B.bin'],bytes(old))
        self.assertEqual(bytes(u.mem_read(0x55001000,C.sizeof(State))),bytes(s))

    def test_experimental_texture_journal_migrates_old_halation_and_preserves_leak(self):
        u=self.machine();addr=0x55001000;self.call(u,'m10v_library_init',addr)
        old=bytearray(u.mem_read(addr,C.sizeof(State)))
        struct.pack_into('<H6B',old,12,33,2,1,8,8,0,0)
        old[57]=7;struct.pack_into('<I',old,100,zlib.crc32(old[:100]))
        self.files['M10V3B.bin']=bytes(old)
        self.assertEqual(self.call(u,'m10v_camera_library_load',addr),2)
        s=State.from_buffer_copy(u.mem_read(addr,C.sizeof(State)))
        self.assertEqual(s.slots[0].halo_gain,0);self.assertEqual(s.effects[0][1],7)
        self.assertEqual(self.files['M10V3B.bin'],bytes(old))

    def test_published_energy_journal_preserves_controls_in_new_texture_namespace(self):
        u=self.machine();old=bytearray(64)
        struct.pack_into('<IHHI',old,0,0x5630314d,2,64,17)
        for i in range(5):struct.pack_into('<H6B',old,12+i*8,33,2,1,8,1,7,2)
        struct.pack_into('<I',old,60,zlib.crc32(old[:60]))
        self.files['M10V3B.bin']=bytes(old)
        self.assertEqual(self.call(u,'m10v_camera_library_load',0x55001000),2)
        s=State.from_buffer_copy(u.mem_read(0x55001000,C.sizeof(State)))
        self.assertEqual((s.slots[0].halo_gain,s.slots[0].halo_spread,s.slots[0].halo_threshold),(8,1,7))
        self.assertEqual(self.call(u,'m10v_camera_library_effects',0x55001000,0,1,8),0)
        self.assertEqual(self.files['M10V3B.bin'],bytes(old));self.assertIn('M10V4A.bin',self.files)

    def test_all_films_have_common_menu_and_only_800t_has_halation_entry(self):
        u=self.machine();state=0x55001000;model=0x55068200
        self.call(u,'m10v_library_init',state)
        for film in range(1,67):
            self.assertEqual(self.call(u,'m10v_camera_library_select',state,1,film),0)
            u.mem_write(model+0x1d,b'\x01')
            self.assertEqual(self.call(u,'m10v_menu_count',model),7 if film==33 else 6)
            self.assertEqual(self.call(u,'m10v_menu_index',model,5),300)
            self.assertEqual(self.call(u,'m10v_menu_index',model,6),214 if film==33 else 0)
        u.mem_write(model+0x1d,b'\x03')
        self.assertEqual(self.call(u,'m10v_menu_count',model),5)
        self.assertEqual(self.call(u,'m10v_menu_index',model,4),301)

    def test_5207_menu_saves_independent_leak_and_resets_defaults(self):
        u=self.machine();state=0x55001000;model=0x55068200;controller=0x55005000
        self.call(u,'m10v_library_init',state)
        self.assertEqual(self.call(u,'m10v_camera_library_select',state,1,66),0)
        for group,index in [(16,2),(17,8),(18,1),(19,7),(20,1)]:
            u.mem_write(model+0x1d,bytes([group]));self.focus=index
            self.assertEqual(self.call(u,'m10v_menu_confirm',controller),0)
            self.assertEqual(u.mem_read(model+0x1d,1),b'\x03' if group==16 else b'\x0f')
        self.call(u,'m10v_camera_library_load',state)
        s=State.from_buffer_copy(u.mem_read(state,C.sizeof(State)))
        self.assertEqual(list(s.effects[1])[:5],[2,8,1,7,1])
        u.mem_write(model+0x1d,b'\x0f');self.focus=4
        self.call(u,'m10v_menu_confirm',controller);self.call(u,'m10v_camera_library_load',state)
        s=State.from_buffer_copy(u.mem_read(state,C.sizeof(State)))
        self.assertEqual(list(s.effects[1])[:5],[1,0,0,4,0]);self.assertEqual(s.slots[1].grain,1)

    def test_5207_arm_pixels_match_host_with_leak_grain_and_padding(self):
        u=self.machine();state=0x55001000;self.call(u,'m10v_library_init',state)
        self.call(u,'m10v_camera_library_select',state,0,66)
        for field,value in [(0,2),(1,8),(2,4),(3,7),(4,1)]:self.call(u,'m10v_camera_library_effects',state,0,field,value)
        width,height,stride=32,16,40;size=stride*height
        y=bytes((i*37+19)%256 for i in range(size));uv=bytes((i*13+97)%256 for i in range(size))
        u.mem_write(0x55010000,y);u.mem_write(0x55020000,uv)
        u.mem_write(0x55002000,struct.pack('<7I',0x55010000,0x55020000,size,size,width,height,stride))
        self.assertEqual(self.call(u,'m10v_library_render',0x55002000,state,0,0,5207,0,0),0)
        s=State.from_buffer_copy(u.mem_read(state,C.sizeof(State)))
        hy=(C.c_uint8*size).from_buffer_copy(y);hc=(C.c_uint8*size).from_buffer_copy(uv);im=Image(hy,hc,size,size,width,height,stride)
        self.assertEqual(host_tests.NativeFilmLibraryTests.lib.m10v_library_render(C.byref(im),C.byref(s),0,None,5207,None,0),0)
        self.assertEqual(bytes(u.mem_read(0x55010000,size)),bytes(hy));self.assertEqual(bytes(u.mem_read(0x55020000,size)),bytes(hc))
        for row in range(height):self.assertEqual(bytes(hy[row*stride+width:(row+1)*stride]),y[row*stride+width:(row+1)*stride])

    def test_capture_chain_restores_registers_flags_and_unaligned_caller_stack(self):
        registers = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4,
                     UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
                     UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_R12)
        for sp in (0x550fe000, 0x550fe004):
            u = self.machine(); u.mem_map(0x536ab000, 4096)
            values = [0x55000a00 + 4 * i for i in range(13)]; cpsr = 0x68050013; seen = []
            def intercept(uc, address, size, data):
                if address == self.manifest['symbols']['m10v_capture_library']:
                    self.assertEqual(uc.reg_read(UC_ARM_REG_R0), values[4])
                    self.assertEqual(uc.reg_read(UC_ARM_REG_SP) & 7, 0)
                    for register in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R12): uc.reg_write(register, 0xdeadbeef)
                    uc.reg_write(UC_ARM_REG_CPSR, 0x980a0013); uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
                elif address == 0x536abd28:
                    seen.append(address); self.assertEqual([uc.reg_read(r) for r in registers], values)
                    self.assertEqual(uc.reg_read(UC_ARM_REG_SP), sp)
                    self.assertEqual(uc.reg_read(UC_ARM_REG_CPSR) & 0xff0f0000, cpsr & 0xff0f0000)
                    uc.reg_write(UC_ARM_REG_R0, 99); uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
            u.hook_add(UC_HOOK_CODE, intercept)
            for register, value in zip(registers, values): u.reg_write(register, value)
            u.reg_write(UC_ARM_REG_CPSR, cpsr); u.reg_write(UC_ARM_REG_SP, sp); u.reg_write(UC_ARM_REG_LR, 0x550ff000)
            u.emu_start(self.manifest['symbols']['m10v_chain_capture'], 0x550ff000, count=1000)
            self.assertEqual(seen, [0x536abd28]); self.assertEqual(u.reg_read(UC_ARM_REG_R0), 99)


if __name__ == '__main__': unittest.main()
