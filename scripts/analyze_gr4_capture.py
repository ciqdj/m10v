#!/usr/bin/env python3
"""Execute exact GR IV descriptor construction/allocation bytes, without patches."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

BASE = 0x53000000
SHA256 = 'a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1'
RECIPE = 0x55000000
STOP = 0x5503F000
ALLOCATION = 0x5370E804


def _descriptor(machine, offset):
    data = bytes(machine.mem_read(RECIPE + offset, 32))
    y, chroma, third = struct.unpack_from('<3I', data, 4)
    width, height, stride, capacity_height, x, z = struct.unpack_from('<6H', data, 16)
    plane_bytes = stride * capacity_height
    return {'offset': hex(offset), 'format': data[0], 'y': hex(y), 'chroma': hex(chroma),
            'third': third, 'width': width, 'height': height, 'stride': stride,
            'allocated_height': capacity_height, 'origin': [x, z],
            'plane_bytes': plane_bytes, 'gap_bytes': chroma - y - plane_bytes,
            'enum_byte': data[28], 'padding_bytes': data[29:32].hex()}


def analyze(rtos: bytes) -> dict:
    identity = hashlib.sha256(rtos).hexdigest()
    if identity != SHA256:
        raise ValueError('GR IV exact RTOS identity required')
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP)
    # The constructor's literal points to the exact recipe virtual table;
    # virtual method 43 contains the allocation entry inspected here.
    vtable = struct.unpack_from('<I', rtos, 0x710C64)[0]
    if vtable != 0x53F85050 or struct.unpack_from('<I', rtos, vtable - BASE + 43 * 4)[0] != ALLOCATION:
        raise ValueError('GR IV recipe virtual table differs')
    caller = 0x537035C8
    word = struct.unpack_from('<I', rtos, caller - BASE)[0]
    if word >> 24 != 0xEB:
        raise ValueError('GR IV capture call is not the expected ARM BL')
    displacement = word & 0xFFFFFF
    if displacement & 0x800000:
        displacement -= 0x1000000
    target = caller + 8 + displacement * 4
    if target != 0x538DD430:
        raise ValueError('GR IV capture original target differs')
    cases = []
    for width, height, stride in ((6256, 4176, 6288), (3120, 2088, 3136)):
        machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        machine.mem_map(BASE, (len(rtos) + 4095) & ~4095)
        machine.mem_write(BASE, rtos)
        machine.mem_map(RECIPE, 0x40000)
        machine.mem_write(RECIPE, b'\xA5' * 0x200)
        for register, value in ((UC_ARM_REG_R4, RECIPE), (UC_ARM_REG_R5, 0),
                (UC_ARM_REG_R6, RECIPE + 0x104), (UC_ARM_REG_R7, RECIPE + 0x100),
                (UC_ARM_REG_R0, RECIPE + 0x108), (UC_ARM_REG_R9, 0x106),
                (UC_ARM_REG_R10, 0x102)):
            machine.reg_write(register, value)
        machine.emu_start(0x5370FF7C, 0x53710084, count=1000)
        if machine.reg_read(UC_ARM_REG_PC) != 0x53710084:
            raise RuntimeError('GR IV constructor exceeded its instruction budget')
        machine.mem_write(RECIPE, struct.pack('<I', vtable))
        machine.mem_write(RECIPE + 0x2BA, struct.pack('<8H', stride, 0, width, height, 0, 720, 480, 720))
        machine.mem_write(RECIPE + 0x31000, struct.pack('<I', RECIPE + 0x32000))
        machine.mem_write(RECIPE + 0x32014, struct.pack('<I', RECIPE + 0x33000))
        helpers = []

        def geometry(uc, address, size, context):
            if address not in (0x538D05F0, 0x538D0764, RECIPE + 0x33000):
                return
            helpers.append(hex(address))
            if address == 0x538D05F0:
                uc.reg_write(UC_ARM_REG_R0, RECIPE + 0x30000)
            elif address == 0x538D0764:
                uc.reg_write(UC_ARM_REG_R0, RECIPE + 0x31000)
            else:
                uc.mem_write(uc.reg_read(UC_ARM_REG_R1), struct.pack('<H', 160))
                uc.mem_write(uc.reg_read(UC_ARM_REG_R2), struct.pack('<H', 120))
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        machine.hook_add(UC_HOOK_CODE, geometry)
        machine.reg_write(UC_ARM_REG_SP, RECIPE + 0x2F000)
        machine.reg_write(UC_ARM_REG_LR, STOP)
        machine.reg_write(UC_ARM_REG_R0, RECIPE)
        machine.reg_write(UC_ARM_REG_R1, 0x60000000)
        machine.emu_start(ALLOCATION, STOP, count=10000)
        if machine.reg_read(UC_ARM_REG_PC) != STOP:
            raise RuntimeError('GR IV allocation exceeded its instruction budget')
        cases.append({'input': {'width': width, 'height': height, 'stride': stride},
                      'returned': True, 'helper_calls': helpers,
                      'source': _descriptor(machine, 0x70),
                      'main': _descriptor(machine, 0xB0),
                      'preview': _descriptor(machine, 0xD0)})
    return {'schema': 'm10v-gr4-capture-allocation-proof/v1', 'rtos_sha256': identity,
            'allocation_entry': hex(ALLOCATION), 'recipe_vtable': hex(vtable),
            'encoder_call': {'caller': hex(caller), 'target': hex(target), 'preimage': hex(word)},
            'cases': cases, 'native_bridge_ready': False,
            'limits': ['Original CPU construction and allocation instructions only; dimensions and allocation base are synthetic.',
                      'Geometry service manager/accessor and a virtual helper are intercepted; helper returns 160x120.',
                      'Pixel processing, scheduler delivery, cache coherency and JPEG output have not been executed.',
                      'A5 padding demonstrates fields left unwritten by the constructor; it is not observed camera RAM.',
                      'Capture request, mode admission, clock and persistence ABI require separate proof.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rtos', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = analyze(args.rtos.read_bytes())
    if args.out.resolve() == args.rtos.resolve():
        raise ValueError('output must not overwrite RTOS input')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'report': str(args.out), 'cases': len(result['cases'])}))
