#!/usr/bin/env python3
"""Pinned GR III 2.10 TopMenu structural audit; never writes firmware.

Unicorn runs the original descriptor loader. Its five RAM descriptor pointers
are supplied explicitly; this does not prove the firmware startup copy map.
Hardware-dependent row predicates are stubbed with a selectable boolean.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

BASE = 0x53000000
SHA256 = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
DESCRIPTORS = (0x53B36DEC, 0x53B37514, 0x53B37188, 0x53B3649C, 0x53B36A54)
SETUP = DESCRIPTORS[4]
LOADER = 0x5319A778
FACTORY = 0x5316F3B8
OWNER = 0x56001000
STOP = 0x57000000


def read_firmware(path):
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('unsupported RTOS SHA256; refusing address-based analysis')
    return data


def describe(data):
    result = []
    for address in DESCRIPTORS:
        d = data[address - BASE:address - BASE + 0x384]
        count, pages = d[0x8b], d[0x68]
        if not (count <= 38 and 0 < pages <= 11):
            raise ValueError('descriptor exceeds fixed capacities')
        starts = list(d[0x80:0x80 + pages])
        if starts != sorted(set(starts)) or starts[0] != 0 or starts[-1] >= count:
            raise ValueError('invalid page boundaries')
        rows = [dict(render=list(struct.unpack_from('<II', d, 0x8c + i*8)),
                     route=struct.unpack_from('<I', d, 0x1bc + i*4)[0],
                     predicate=list(struct.unpack_from('<II', d, 0x254 + i*8)))
                for i in range(count)]
        result.append(dict(address=address, count=count, pages=pages, starts=starts, rows=rows))
    return result


def emulate_loader(data, append=False, predicate=True):
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(BASE, (len(data)+4095)&~4095)
    uc.mem_write(BASE, data)
    uc.mem_map(0x55001000, 0x1000)
    uc.mem_write(0x55001eb8, struct.pack('<5I', *DESCRIPTORS))
    uc.mem_map(0x56000000, 0x10000)
    uc.mem_map(STOP, 0x1000)
    uc.mem_write(OWNER-16, b'\xa5'*16)
    uc.mem_write(OWNER+0x13bc, b'\xa5'*32)
    if append:
        # Synthetic addresses and routes exercise copying only, never invoked.
        uc.mem_write(SETUP+0x8b, b'\x20')
        for row in (30, 31):
            uc.mem_write(SETUP+0x8c+row*8, struct.pack('<II', STOP+0x100+row*4, 0))
            uc.mem_write(SETUP+0x1bc+row*4, struct.pack('<I', 0x0200f000+row))
    writes = []
    def code(machine, address, size, _):
        if address in (0x531966e4, 0x53196708):
            machine.reg_write(UC_ARM_REG_R0, int(predicate))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        elif not (0x5319a720 <= address < 0x5319aa68):
            raise RuntimeError(f'unexpected execution address {address:#x}')
    def write(machine, access, address, size, value, _):
        if not (OWNER+0x228 <= address and address+size <= OWNER+0x13bc) and not (0x56008000 <= address < 0x56010000):
            raise RuntimeError(f'out of bounds loader write {address:#x}')
        writes.append((address, size))
    uc.hook_add(UC_HOOK_CODE, code)
    uc.hook_add(UC_HOOK_MEM_WRITE, write)
    uc.reg_write(UC_ARM_REG_R0, OWNER)
    uc.reg_write(UC_ARM_REG_SP, 0x5600fff0)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.emu_start(LOADER, STOP, count=100000)
    if uc.reg_read(UC_ARM_REG_PC) != STOP:
        raise RuntimeError('loader did not return within instruction budget')
    if bytes(uc.mem_read(OWNER-16,16)) != b'\xa5'*16 or bytes(uc.mem_read(OWNER+0x13bc,32)) != b'\xa5'*32:
        raise RuntimeError('owner bounds guard changed')
    return bytes(uc.mem_read(OWNER,0x13bc)), writes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rtos')
    args = parser.parse_args()
    data = read_firmware(args.rtos)
    before, _ = emulate_loader(data)
    after, writes = emulate_loader(data, append=True)
    report = dict(sha256=SHA256, categories=describe(data),
                  setup_append_offsets=dict(count=SETUP+0x8b, renders=[SETUP+0x8c+i*8 for i in (30,31)],
                                            routes=[SETUP+0x1bc+i*4 for i in (30,31)]),
                  base_vtable_hex=data[0xb1f2d8:0xb1f314].hex(),
                  emulated=True, appended_runtime_count=after[4*0x384+0x2b3],
                  write_count=len(writes), camera_verified=False)
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()


def emulate_key_route(data, route, key=10):
    """Run original route selector until mapper selection/assertion (no I/O)."""
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(BASE, (len(data)+4095)&~4095); uc.mem_write(BASE, data)
    uc.mem_map(0x56000000, 0x10000)
    selected=[]
    def hook(machine,address,size,_):
        if address in (0x5320ad88,0x5320aefc,0x53228c4c):
            machine.reg_write(UC_ARM_REG_R0,route if address==0x53228c4c else OWNER)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
        elif 0x5320c000 <= address < 0x53221a1c or address==0x536b93d0:
            selected.append(address); machine.emu_stop()
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_ARM_REG_SP,0x5600fff0); uc.reg_write(UC_ARM_REG_R0,OWNER)
    uc.reg_write(UC_ARM_REG_R1,key); uc.emu_start(0x53221a1c,0,count=1000)
    if len(selected)!=1: raise RuntimeError('key selector did not choose known mapper/assertion')
    return selected[0]


def emulate_topmenu_key(data, key, image_control=False):
    """Run stock TopMenu mapper, stubbing getters and recording queued events."""
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP
    uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    uc.mem_map(BASE,(len(data)+4095)&~4095); uc.mem_write(BASE,data)
    uc.mem_map(0x56000000,0x10000); uc.mem_map(STOP,0x1000)
    events=[]
    def hook(machine,address,size,_):
        if address in (0x5320ad88,0x5320aefc,0x532288b0):
            if address==0x532288b0: events.append(machine.reg_read(UC_ARM_REG_R1))
            machine.reg_write(UC_ARM_REG_R0,OWNER)
            machine.reg_write(UC_ARM_REG_PC,machine.reg_read(UC_ARM_REG_LR))
        elif not ((0x53218fa4 <= address < 0x53219354) if image_control else (0x53215004 <= address < 0x53215320)):
            raise RuntimeError(f'unexpected key mapper execution {address:#x}')
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.reg_write(UC_ARM_REG_SP,0x5600fff0); uc.reg_write(UC_ARM_REG_R0,OWNER)
    uc.reg_write(UC_ARM_REG_R1,key); uc.reg_write(UC_ARM_REG_LR,STOP)
    uc.emu_start(0x53218fa4 if image_control else 0x53215004,STOP,count=1000)
    if uc.reg_read(UC_ARM_REG_PC)!=STOP: raise RuntimeError('key mapper did not return')
    return events
