"""Execute the crop menu and geometry, rather than inspecting patch text."""
import importlib.util
import json
import os
import struct
import subprocess
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_PROT_READ, UC_PROT_EXEC, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR

ROOT = Path(__file__).resolve().parents[1]
BASE, STOP, RAM = 0x53000000, 0x550ff000, 0x55000000


class AspectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.six_id=811;cls.xpan_id=810
        if os.environ.get('M10V_ASPECT_CANDIDATE'):
            candidate=str(Path(os.environ['M10V_ASPECT_CANDIDATE']).resolve())
            script="import{readFileSync}from'node:fs';import{decodeFrameMap}from'./node/gr3-frames.mjs';const b=readFileSync(process.argv[1]),d=decodeFrameMap(b,b.readUInt32LE(b.length-8)).decoded;process.stdout.write(d.subarray(0x10870,0x10870+d.readUInt32LE(0x1086c)));"
            cls.code=subprocess.check_output(['node','--input-type=module','-e',script,candidate],cwd=ROOT)
            from scripts.gr3_aspect_overlay import build_module, MODULE, END
            code,cls.entries=build_module()
            at=cls.entries['m10v_aspect_id_record']-MODULE
            cls.six_id=struct.unpack_from('<I',cls.code,cls.entries['m10v_aspect_id_record']-BASE+4)[0]
            cls.xpan_id=cls.six_id-1
            expected=bytearray(code)
            expected[at+4:at+12]=cls.code[MODULE-BASE+at+4:MODULE-BASE+at+12]
            if cls.code[MODULE-BASE:MODULE-BASE+len(code)]!=bytes(expected):
                raise AssertionError('delivered crop module differs from source-built ARM')
            return
        template = json.loads((ROOT/'.runtime/grlife-current/reconstruction/firmware_store/templates/urban160-native.json').read_text())
        script = "import{readFileSync}from'node:fs';import{officialResources}from'./node/gr3-stock-presets.mjs';const{decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));process.stdout.write(d.subarray(s.RTOS.offset,s.RTOS.offset+s.RTOS.size));"
        cls.code = bytearray(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT))
        cls.code.extend(bytes(0x10ba000-len(cls.code)))
        blob = bytes.fromhex(template['program_hex'])
        cls.code[template['base_va']-BASE:template['base_va']-BASE+len(blob)] = blob
        script = ROOT/'scripts/gr3_aspect_overlay.py'
        cls.entries = {}
        if script.exists():
            spec = importlib.util.spec_from_file_location('aspect_overlay', script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            cls.code, cls.entries = module.apply_overlay(cls.code)

    def machine(self):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        extent = (len(self.code)+4095)&~4095
        u.mem_map(BASE, extent)
        u.mem_write(BASE, bytes(self.code))
        u.mem_protect(BASE, extent, UC_PROT_READ|UC_PROT_EXEC)
        u.mem_map(RAM, 0x100000)
        u.reg_write(UC_ARM_REG_SP, RAM+0xf0000)
        u.reg_write(UC_ARM_REG_LR, STOP)
        return u

    def call(self, address, *args):
        u = self.machine()
        for reg, value in zip([UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3], args):
            u.reg_write(reg, value)
        u.emu_start(address, STOP, count=10000)
        return u

    def test_menu_adds_six_by_seven_without_changing_existing_identities(self):
        self.assertEqual(self.call(0x540b98c4).reg_read(UC_ARM_REG_R0), 5)
        for current, following in [(0,3),(3,1),(1,4),(4,5),(5,0),(255,0)]:
            with self.subTest(current=current):
                self.assertEqual(self.call(0x540b9300,current).reg_read(UC_ARM_REG_R0), following)

    def test_xpan_caption_preserves_case_and_old_crop_identity(self):
        descriptor = 0x540b97ec-BASE
        size = self.code[descriptor]
        ptr = struct.unpack_from('<I', self.code, descriptor+4)[0]-BASE
        self.assertEqual(bytes(self.code[ptr:ptr+size*2]).decode('utf-16le').rstrip('\0'), 'XPan')

    def test_new_ratio_has_its_own_label(self):
        self.assertEqual(self.call(0x540b9428,0,5).reg_read(UC_ARM_REG_R0), self.six_id)

    def test_six_by_seven_resolution_for_all_quality_and_crop_combinations(self):
        for mag, sizes in [(0x3f800000,[(4672,4000),(3728,3200),(2608,2240),(1488,1280)]),
                           (0x3fa00000,[(3728,3200),(3728,3200),(2608,2240),(1488,1280)]),
                           (0x3fe3d70a,[(2608,2240),(2608,2240),(2608,2240),(1488,1280)]),
                           (0x3fe49249,[(2608,2240),(2608,2240),(2608,2240),(1488,1280)])]:
            for quality, expected in enumerate(sizes):
                with self.subTest(mag=hex(mag),quality=quality):
                    u=self.call(self.entries['m10v_aspect_resolution'],mag,quality,RAM,RAM+2)
                    self.assertEqual(struct.unpack('<HH',u.mem_read(RAM,4)),expected)

    def test_text_routes_both_new_names_in_every_native_language(self):
        from unicorn import arm_const as A
        for language in range(21):
            for resource, label in [(self.xpan_id,'XPan'),(self.six_id,'6x7')]:
                for entry,leaf,register in [(0x540b89f8,0x53396700,A.UC_ARM_REG_R7),
                                            (0x540b8bc4,0x5339710c,A.UC_ARM_REG_R3)]:
                    with self.subTest(language=language,resource=resource,entry=hex(entry)):
                        u=self.machine();u.reg_write(A.UC_ARM_REG_R0,language)
                        u.reg_write(A.UC_ARM_REG_R7,resource);u.reg_write(A.UC_ARM_REG_R11,RAM+0xe0000)
                        seen=[]
                        def stop(uc,address,size,data):
                            if address==leaf: seen.append(address);uc.emu_stop()
                        u.hook_add(UC_HOOK_CODE,stop)
                        u.emu_start(entry,STOP,count=1000)
                        self.assertEqual(seen,[leaf])
                        ptr=u.reg_read(register)
                        header=bytes(u.mem_read(ptr,8));count=header[0]
                        text=bytes(u.mem_read(struct.unpack_from('<I',header,4)[0],count*2)).decode('utf-16le').rstrip('\0')
                        self.assertEqual(text,label)

    def test_new_crop_has_centered_screen_and_thumbnail_origins(self):
        for entry,expected in [(0x540b94e8,(80,0)),(0x540b950c,(10,0))]:
            u=self.call(entry,0,5,RAM,RAM+2)
            self.assertEqual(struct.unpack('<HH',u.mem_read(RAM,4)),expected)
        # The XPan geometry is unchanged while its caption is renamed.
        u=self.call(0x540b94e8,0,4,RAM,RAM+2)
        self.assertEqual(struct.unpack('<HH',u.mem_read(RAM,4)),(0,108))

    def test_native_grid_draw_uses_vertical_six_by_seven_mask(self):
        from unicorn import arm_const as A
        for entry in [0x540b90a4,0x540b91cc]:
            with self.subTest(entry=hex(entry)):
                u=self.machine();view=RAM+0x2000;surface=RAM+0x3000
                u.mem_write(RAM+0x100,struct.pack('<I',RAM+0x200))
                u.mem_write(view+0x9e,b'\x01')
                for offset in [0x30,0x64]: u.mem_write(view+offset,struct.pack('<4I',0,0,720,480))
                returns={0x53525d5c:RAM+0x100,0x5354a778:5,0x53549958:0,
                         0x53654150:RAM+0x300,0x53654220:0,0x5339c3b0:0,
                         0x533ab9bc:0,0x5320804c:RAM+0x400,0x532081ec:RAM+0x500}
                rectangles=[]
                def native(uc,address,size,data):
                    if address==0x540b88b4:
                        sp=uc.reg_read(A.UC_ARM_REG_SP)
                        rectangles.append(struct.unpack('<5I',uc.mem_read(sp,20)))
                    elif address not in returns: return
                    uc.reg_write(A.UC_ARM_REG_R0,returns.get(address,0))
                    uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
                u.hook_add(UC_HOOK_CODE,native)
                u.reg_write(A.UC_ARM_REG_R0,view);u.reg_write(A.UC_ARM_REG_R1,surface)
                u.emu_start(entry,STOP,count=2000)
                self.assertEqual(rectangles,[(0,0,80,480,16),(640,0,80,480,16),
                                             (78,0,2,480,2),(640,0,2,480,2)])


if __name__ == '__main__':
    unittest.main()
