"""Read-only ARM probe of the exact GR III focal-crop consumers.

This diagnoses why writing an arbitrary StillCropMag is insufficient. It never
patches firmware or accesses a camera. Run with the project's .venv Python.
"""
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC, UC_ARM_REG_LR,
    UC_ARM_REG_R0, UC_ARM_REG_S0,
)

ROOT = Path(__file__).resolve().parents[1]
BASE, STOP = 0x53000000, 0x550FF000


def probe():
    js = """import{readFileSync}from'node:fs';
import{officialResources}from'./node/gr3-stock-presets.mjs';
const{decoded:d,sections:s}=officialResources(readFileSync('bin/fwdc239b-gr3-official.bin'));
process.stdout.write(d.subarray(s.RTOS.offset,s.RTOS.offset+s.RTOS.size));"""
    code = subprocess.check_output(['node','--input-type=module','-e',js],cwd=ROOT)
    digest = hashlib.sha256(code).hexdigest()
    if digest != '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67':
        raise ValueError('GR III RTOS baseline differs')
    rows = []
    for mm in (28,30,35,36,41,49,50,70,100):
        bits = struct.unpack('<I',struct.pack('<f',mm/28))[0]
        row = {'mm':mm,'magnification_bits':f'{bits:08x}','rectangle_pointers':{}}
        for address in (0x535F4808,0x535F4860,0x535F48B8):
            u = Uc(UC_ARCH_ARM,UC_MODE_ARM)
            u.mem_map(BASE,(len(code)+4095)&~4095)
            u.mem_write(BASE,code)
            u.mem_map(0x55000000,0x100000)
            u.reg_write(UC_ARM_REG_C1_C0_2,0xF00000)
            u.reg_write(UC_ARM_REG_FPEXC,0x40000000)
            u.reg_write(UC_ARM_REG_S0,bits)
            u.reg_write(UC_ARM_REG_LR,STOP)
            u.emu_start(address,STOP,count=100)
            result = u.reg_read(UC_ARM_REG_R0)
            row['rectangle_pointers'][f'{address:08x}'] = f'{result:08x}'
            if (mm in (28,35,50)) != bool(result):
                raise AssertionError(f'unexpected native rectangle result at {address:x}: {mm}mm')
        rows.append(row)
    return {'rtos_sha256':digest,'camera_tested':False,
            'scope':'Original native rectangle selectors only; no new hooks enabled',
            'results':rows}


if __name__ == '__main__':
    print(json.dumps(probe(),indent=2))
