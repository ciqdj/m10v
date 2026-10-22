"""Exercise appended film artwork through the packaged stock icon decoder."""
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from unicorn.arm_const import *
from scripts.build_gr3_m10v_library import build
from scripts.analyze_gr3_device_regression import machine, run

ROOT = Path(__file__).resolve().parents[1]


class PixelIconArmTests(unittest.TestCase):
    def test_pixel_icon_dimensions_and_rom_pixels_in_both_catalog_modes(self):
        for sd in (False, True):
            with self.subTest(sd_library=sd), tempfile.TemporaryDirectory() as folder:
                manifest = build(folder, sd_library=sd)
                script = """
import {readFileSync,writeFileSync} from 'node:fs';
import {buildNativeLibrary} from './node/gr3-m10v-native-build.mjs';
import {decodeFrameMap} from './node/gr3-frames.mjs';
const dir=process.argv[1];
const {candidate}=buildNativeLibrary(readFileSync('bin/fwdc239b-gr3-official.bin'),readFileSync(dir+'/m10v-library-arm.bin'),JSON.parse(readFileSync(dir+'/m10v-library-arm.json')));
const {decoded}=decodeFrameMap(candidate,candidate.readUInt32LE(candidate.length-8));
let at=0;while(decoded.toString('ascii',at,at+4)!=='RTOS')at+=16+decoded.readUInt32LE(at+12);
writeFileSync(dir+'/rtos.bin',decoded.subarray(at+16,at+16+decoded.readUInt32LE(at+12)));
"""
                subprocess.run(['node', '--input-type=module', '-e', script, folder], cwd=ROOT, check=True)
                code = (Path(folder)/'rtos.bin').read_bytes()
                u = machine(code)
                last = 761 if sd else 755
                # Actual installed width/height functions, including their
                # upper bounds and (in SD mode) directory adapters.
                for entry in (0x53209fb8, 0x53209fec):
                    u.reg_write(UC_ARM_REG_R1, last)
                    u.reg_write(UC_ARM_REG_LR, 0x551ff000)
                    self.assertEqual(run(u, entry), 40)
                    u.reg_write(UC_ARM_REG_R1, last+1)
                    u.reg_write(UC_ARM_REG_LR, 0x551ff000)
                    self.assertEqual(run(u, entry), 0)
                # The drawing path has a separate maximum check.
                word = struct.unpack_from('<I', code, 0x5320a7cc-0x53000000)[0]
                self.assertEqual((word & 0xfff) | ((word >> 4) & 0xf000), last)
                table = manifest['icons']['table']
                desc = struct.unpack('<I', u.mem_read(table+last*4, 4))[0]
                width, height, offset = struct.unpack('<HHI', u.mem_read(desc, 8))
                self.assertEqual((width, height), (40, 40))
                self.assertEqual(bytes(u.mem_read(offset*4, 6400)), (ROOT/'native/gr3/m10v_pixel_world.rgba').read_bytes())
                u.mem_write(0x55009024, struct.pack('<H', last))
                for reg, value in ((UC_ARM_REG_R0,11),(UC_ARM_REG_R1,22),
                                   (UC_ARM_REG_R5,0x55009000),(UC_ARM_REG_R6,offset),
                                   (UC_ARM_REG_LR,0x57000000),(UC_ARM_REG_SP,0x551fe000)):
                    u.reg_write(reg, value)
                u.reg_write(UC_ARM_REG_CPSR, 0xa00001d3)
                u.emu_start(manifest['symbols']['m10v_icon_pixels'], 0x5320a838, count=100)
                self.assertEqual(u.reg_read(UC_ARM_REG_R12), offset*4)
                self.assertEqual(u.reg_read(UC_ARM_REG_R0), 11)
                self.assertEqual(u.reg_read(UC_ARM_REG_R1), 22)
                self.assertEqual(u.reg_read(UC_ARM_REG_SP), 0x551fe000)
                self.assertEqual(u.reg_read(UC_ARM_REG_CPSR) & 0xf8000000, 0xa0000000)
