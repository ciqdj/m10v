"""Execute stock GR III 2.10 allocation ARM bytes; never generate firmware."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                              UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6,
                              UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
                              UC_ARM_REG_R10, UC_ARM_REG_SP, UC_ARM_REG_LR,
                              UC_ARM_REG_PC)

BASE = 0x53000000
SHA256 = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
RECIPE = 0x55000000
STOP = 0x5501f000


def descriptor(u, offset):
    data = bytes(u.mem_read(RECIPE + offset, 32))
    y, c, third = struct.unpack_from('<III', data, 4)
    width, height, stride, allocated, x, z = struct.unpack_from('<6H', data, 16)
    plane = stride * allocated
    return {'offset': hex(offset), 'format': data[0], 'y': hex(y),
            'chroma': hex(c), 'third': third, 'width': width, 'height': height,
            'stride': stride, 'allocatedHeight': allocated, 'origin': [x, z],
            'planeBytes': plane, 'planeSeparation': c-y, 'gapBytes': c-y-plane,
            'enumByte': data[28], 'enumWord': struct.unpack_from('<I', data, 28)[0],
            'paddingBytes': data[29:32].hex()}


def analyze(firmware):
    sha = hashlib.sha256(firmware).hexdigest()
    if sha != SHA256:
        raise ValueError('Exact GR III 2.10 decoded RTOS SHA256 required')
    disassembler = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    evidence = []
    for address in (0x5350f224, 0x5350f290, 0x536a3db8, 0x536a3de4,
                    0x5350dd6c, 0x5350ddd0, 0x5350dd44, 0x5350dd98):
        instruction = next(disassembler.disasm(firmware[address-BASE:address-BASE+4], address))
        evidence.append({'address': hex(address), 'instruction': instruction.mnemonic+' '+instruction.op_str})
    cases = []
    for width, height, stride in ((6000, 4000, 6016), (2992, 2000, 3008)):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.mem_map(BASE, (len(firmware)+4095)&~4095)
        u.mem_write(BASE, firmware)
        u.mem_map(RECIPE, 0x20000)
        u.mem_write(RECIPE, b'\xa5' * 0x200)
        writes = []
        phase = ['constructor']
        helper_calls = []

        def record_write(uc, access, address, size, value, _):
            if RECIPE+0x70 <= address < RECIPE+0xd0:
                writes.append({'phase': phase[0], 'pc': hex(uc.reg_read(UC_ARM_REG_PC)),
                               'offset': hex(address-RECIPE), 'size': size})

        def helper(uc, address, size, _):
            if address == 0x536a2f10:
                helper_calls.append(hex(address))
                uc.mem_write(uc.reg_read(UC_ARM_REG_R1), struct.pack('<H', 160))
                uc.mem_write(uc.reg_read(UC_ARM_REG_R2), struct.pack('<H', 120))
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        u.hook_add(UC_HOOK_MEM_WRITE, record_write)
        u.hook_add(UC_HOOK_CODE, helper)
        # Execute only the original descriptor constructor stores, with its real
        # local-register values. A5 padding deliberately detects unwritten bytes.
        for reg, value in ((UC_ARM_REG_R4, RECIPE), (UC_ARM_REG_R5, 0),
                           (UC_ARM_REG_R6, RECIPE+0x104), (UC_ARM_REG_R7, RECIPE+0x100),
                           (UC_ARM_REG_R0, RECIPE+0x108), (UC_ARM_REG_R9, 0x106),
                           (UC_ARM_REG_R10, 0x102)):
            u.reg_write(reg, value)
        u.emu_start(0x5350f210, 0x5350f31c, count=1000)
        if u.reg_read(UC_ARM_REG_PC) != 0x5350f31c:
            raise RuntimeError('Constructor instruction budget exhausted')
        u.mem_write(RECIPE, struct.pack('<I', 0x53d0fc90))
        # Recipe geometry read by the actual allocation method; preview geometry
        # is synthetic and does not claim any real-camera shooting configuration.
        u.mem_write(RECIPE+0x252, struct.pack('<8H', stride, 0, width, height, 0, 720, 480, 720))
        u.reg_write(UC_ARM_REG_SP, RECIPE+0x1e000)
        u.reg_write(UC_ARM_REG_LR, STOP)
        u.reg_write(UC_ARM_REG_R0, RECIPE)
        u.reg_write(UC_ARM_REG_R1, 0x60000000)
        phase[0] = 'allocation'
        u.emu_start(0x5350db3c, STOP, count=10000)
        if u.reg_read(UC_ARM_REG_PC) != STOP:
            raise RuntimeError('Allocation instruction budget exhausted')
        cases.append({'input': {'width': width, 'height': height, 'stride': stride},
                      'returned': True, 'helperCalls': helper_calls,
                      'source': descriptor(u, 0x70), 'main': descriptor(u, 0xb0),
                      'descriptorWrites': writes})
    return {'schema': 'm10v-gr3-capture-allocation-proof/v1', 'rtosSha256': sha,
            'allocationEntry': '0x5350db3c', 'cases': cases,
            'instructionEvidence': evidence,
            'limits': ['Original descriptor constructor fragment and allocation CPU instructions executed with synthetic geometry and allocation base.',
                       'Helper 0x536a2f10 intercepted to return 160x120; its hardware/configuration behavior is not emulated.',
                       'BackResize/hardware/cache/scheduler and actual camera addresses are not executed here.',
                       'A5 padding demonstrates constructor byte semantics; actual camera padding values are not observed.',
                       'Layout evidence does not prove a hardware halation fix.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rtos', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = analyze(args.rtos.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'output': str(args.output), 'rtosSha256': report['rtosSha256'],
                      'cases': len(report['cases'])}, indent=2))


if __name__ == '__main__':
    main()
