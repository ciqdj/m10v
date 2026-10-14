"""Prove the locked GR III chroma contract using original CPU instructions only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

LOAD = 0x53000000
RTOS_SHA256 = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
ANCHORS = [
    (0x536c9450, '5038e7e7', 'CPU converter extracts Cr from input byte2'),
    (0x536c9464, '7030efe6', 'CPU converter extracts unsigned Y byte0'),
    (0x536c9468, '5004e7e7', 'CPU converter extracts Cb byte1'),
    (0x536c9480, 'c76a76ee', 'Cr minus128'),
    (0x536c9490, '476a36ee', 'Cb minus128'),
    (0x536c9550, '00000043', '128.0 f32 neutral'),
    (0x536c9438, '5004efe7', 'repacker extracts Cb/Cr halfword'),
    (0x536c9440, '1038dfe7', 'repacker places Cb/Cr at bits16..31'),
    (0x536d6dd8, '020053e3', 'fill dispatcher recognizes UI format2'),
    (0x536d6de8, '010053e3', 'fill dispatcher recognizes UI format1'),
    (0x536d6e60, '60ffffeb', 'UI format1 calls semiplanar422 fill'),
    (0x536d6c28, 'b6a1dbe1', '422 fill takes repacked Cb/Cr halfword'),
    (0x536d6b14, 'b220c3e0', 'CPU stores Cb/Cr halfword little endian'),
    (0x536c7674, '00c0c4e5', 'adapter writes low descriptor format'),
    (0x536c76e4, '080084e5', 'adapter writes combined chroma pointer'),
    (0x53dbae40, '01020102', 'UI types1/2 map low422/420 formats1/2'),
    (0x53dbae44, '02020101', 'UI types1/2 map combined address mode2'),
    (0x536d8624, 'b270d8e0', '420 consumer reads two Y samples'),
    (0x536d862c, 'b240d9e0', '420 consumer reads Cb/Cr pair'),
]


def validate_identity(rtos):
    if hashlib.sha256(rtos).hexdigest() != RTOS_SHA256:
        raise ValueError('exact GR III RTOS identity required')
    for address, preimage, _ in ANCHORS:
        offset = address - LOAD
        if rtos[offset:offset + len(preimage) // 2].hex() != preimage:
            raise ValueError(f'chroma preimage differs at {address:#x}')


class OriginalCpu:
    """Read-only firmware mapping, synthetic data, no patched calls or stubs."""
    def __init__(self, rtos):
        validate_identity(rtos)
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_EXEC
        from unicorn import arm_const as reg
        self.reg = reg
        self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.u.mem_map(LOAD, (len(rtos) + 4095) & ~4095)
        self.u.mem_write(LOAD, rtos)
        self.u.mem_protect(LOAD, (len(rtos) + 4095) & ~4095, UC_PROT_READ | UC_PROT_EXEC)
        self.u.mem_map(0x10000000, 0x10000)
        self.u.reg_write(reg.UC_ARM_REG_C1_C0_2, 0xf00000)
        self.u.reg_write(reg.UC_ARM_REG_FPEXC, 0x40000000)
        self.executed = set()

        def guard(uc, address, size, _):
            allowed = ((0x536c74b0, 0x536c7704), (0x536c9428, 0x536c9550),
                       (0x536c9568, 0x536c959c), (0x536d6808, 0x536d6eec),
                       (0x536d858c, 0x536d8788))
            if not any(start <= address < end for start, end in allowed):
                raise ValueError(f'CPU proof reached unapproved code {address:#x}')
            self.executed.add(address)
        self.u.hook_add(UC_HOOK_CODE, guard)

    def call(self, entry, args, stack=b''):
        r = self.reg
        for register, value in zip((r.UC_ARM_REG_R0, r.UC_ARM_REG_R1,
                                   r.UC_ARM_REG_R2, r.UC_ARM_REG_R3), args):
            self.u.reg_write(register, value)
        self.u.reg_write(r.UC_ARM_REG_SP, 0x1000f000)
        self.u.reg_write(r.UC_ARM_REG_LR, 0x10000000)
        if stack:
            self.u.mem_write(0x1000f000, stack)
        self.u.emu_start(entry, 0x10000000, count=100000)
        if self.u.reg_read(r.UC_ARM_REG_PC) != 0x10000000:
            raise ValueError('CPU proof did not return within instruction budget')
        if self.u.reg_read(r.UC_ARM_REG_SP) != 0x1000f000:
            raise ValueError('CPU proof failed to restore stack')
        return self.u.reg_read(r.UC_ARM_REG_R0)


def bitmap(format_no, base, width, height, stride, allocated_height):
    data = bytearray(40)
    data[2] = format_no
    struct.pack_into('<I', data, 8, base)
    struct.pack_into('<6H', data, 0x18, stride, allocated_height, width, height,
                     stride, allocated_height)
    return bytes(data)


def inspect_chroma(rtos):
    cpu = OriginalCpu(rtos)
    u = cpu.u
    pixel_cases = []
    known = [((0, 128, 128), (0, 0, 0, 255)),
             ((255, 128, 128), (255, 255, 255, 255)),
             ((128, 128, 128), (128, 128, 128, 255)),
             ((128, 160, 128), (128, 116, 184, 255)),
             ((128, 128, 160), (172, 105, 128, 255)),
             ((128, 96, 128), (128, 139, 71, 255)),
             ((128, 128, 96), (83, 150, 128, 255)),
             ((128, 0, 255), (255, 81, 0, 255)),
             ((128, 255, 0), (0, 175, 255, 255))]
    for color, expected in known:
        word = color[0] | color[1] << 8 | color[2] << 16
        actual = tuple(struct.pack('<I', cpu.call(0x536c9450, [word])))
        if actual != expected:
            raise ValueError(f'original pixel converter differs for {color}: {actual}')
        pixel_cases.append({'input_YCbCr': color, 'actual_RGBA': actual})

    fill_cases = []
    colors = [(0, 128, 128), (255, 128, 128), (128, 128, 128),
              (128, 160, 128), (128, 128, 160), (128, 0, 255), (128, 255, 0)]
    for fmt in (1, 2):
        for width, height, stride, allocated in ((4, 2, 4, 2), (66, 4, 80, 6)):
            area = stride * allocated
            span = area if fmt == 1 else area // 2
            for y, cb, cr in colors:
                base, obj, descriptor = 0x10002000, 0x10001000, 0x10004000
                u.mem_write(obj, bitmap(fmt, base, width, height, stride, allocated))
                u.mem_write(base, bytes([0x66] * (area + span)))
                cpu.call(0x536d6d94, [0, obj, width, height],
                         struct.pack('<III', 0, 0, y | cb << 8 | cr << 16))
                actual = bytes(u.mem_read(base, area + span))
                expected = bytearray([0x66] * (area + span))
                for row in range(height):
                    expected[row * stride:row * stride + width] = bytes([y] * width)
                for row in range(height if fmt == 1 else height // 2):
                    start = area + row * stride
                    expected[start:start + width] = bytes([cb, cr] * (width // 2))
                if actual != expected:
                    raise ValueError(f'original fill/order/padding differs for format{fmt}')
                cpu.call(0x536c761c, [descriptor, obj])
                desc = bytes(u.mem_read(descriptor, 32))
                expected_desc = struct.pack('<4I6H B3x', fmt, base, base + area, 0,
                                            width, height, stride, allocated, 0, 0, 2)
                if desc != expected_desc:
                    raise ValueError('bitmap adapter differs from shared descriptor contract')
                fill_cases.append({'ui_format': fmt, 'low_format': fmt,
                                   'dimensions': [width, height, stride, allocated],
                                   'input_YCbCr': [y, cb, cr], 'descriptor_hex': desc.hex(),
                                   'combined_first_pair': list(actual[area:area + 2]),
                                   'padding_unchanged': True,
                                   'buffer_sha256': hashlib.sha256(actual).hexdigest()})

    # An independent original consumer verifies asymmetric pairs across two rows.
    obj, base, out = 0x10001000, 0x10002000, 0x10004000
    u.mem_write(obj, bitmap(2, base, 4, 2, 4, 2))
    u.mem_write(base, bytes([128] * 8 + [160, 128, 128, 160]))
    cpu.call(0x536d858c, [0, obj, out])
    actual = bytes(u.mem_read(out, 32))
    expected = bytes([128, 116, 184, 255] * 2 + [172, 105, 128, 255] * 2) * 2
    if actual != expected:
        raise ValueError('independent original semiplanar consumer differs')
    return {'schema': 'm10v-gr3-800t-chroma/v1', 'rtos_sha256': RTOS_SHA256,
            'execution': {'calls_stubbed': 0, 'original_CPU_only': True,
                          'unique_instruction_addresses': len(cpu.executed)},
            'anchors': [{'address': address, 'bytes': preimage, 'meaning': meaning}
                        for address, preimage, meaning in ANCHORS],
            'contract': {'low_formats': [1, 2], 'address_mode': 2,
                         'combined_order': 'CbCr', 'component_type': 'uint8',
                         'neutral': 128, 'storage_min': 0, 'storage_max': 255,
                         'pair_horizontal_pixels': 2,
                         'row_stride': 'allocated width in bytes'},
            'pixel_cases': pixel_cases, 'fill_adapter_cases': fill_cases,
            'independent_420_consumer_RGBA': [list(actual[i:i + 4]) for i in range(0, 32, 4)],
            'limits': ['Does not measure actual ISP output distributions',
                       'Does not prove shutter-only caller scope or RAW ownership',
                       'Does not emulate hardware/cache timing or authorize a firmware writer']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rtos', type=Path, help='decoded original RTOS binary')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    report = json.dumps(inspect_chroma(args.rtos.read_bytes()), indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
    print(report, end='')
