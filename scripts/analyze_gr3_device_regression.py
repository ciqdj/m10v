"""Execute official ARM seams from extracted RTOS files; never emits firmware.
Run after extracting official/uploaded RTOS with the repository decoder.
The GUI callback probe stubs model services, but executes real callback/count/index code.
The clock probe executes the official getter and property/date helpers, stubbing only assert.
"""
import argparse
import json
import struct
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

BASE = 0x53000000
STOP = 0x551ff000

def machine(code):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(BASE, 0x1200000)
    u.mem_map(0x55000000, 0x200000)
    u.mem_write(BASE, code)
    u.reg_write(UC_ARM_REG_SP, 0x551fe000)
    u.reg_write(UC_ARM_REG_LR, STOP)
    return u

def run(u, entry):
    u.emu_start(entry, STOP, count=100000)
    if u.reg_read(UC_ARM_REG_PC) != STOP:
        raise RuntimeError('probe did not return')
    return u.reg_read(UC_ARM_REG_R0)

def menu_probe(code):
    u = machine(code)
    u.mem_write(0x55068200, bytes([18]) + bytes(31))
    calls = []
    u.mem_write(0x55006004, struct.pack('<I', 0x55007000))
    def services(uc, address, size, data):
        if address == 0x5320ad88: result = 0x55006000
        elif address == 0x5320ba9c: result = 0x55068200
        elif address == 0x5320b31c: result = 0x55006000
        elif address == 0x532c26c0:
            calls.append({'function': hex(address), 'value': uc.reg_read(UC_ARM_REG_R1)})
            return
        elif address == 0x532750f8:
            calls.append({'function': hex(address), 'stored_tone': bytes(uc.mem_read(0x550071c2, 1))[0]})
            result = 0
        elif address == 0x532bd6b4: result = 21
        elif address == 0x532bd6d4: result = 0
        elif address == 0x532bd61c:
            calls.append({'function': hex(address), 'value': uc.reg_read(UC_ARM_REG_R1)})
            result = 0
        else: return
        uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE, services)
    u.reg_write(UC_ARM_REG_R0, 0x55005000)
    u.reg_write(UC_ARM_REG_R1, 12)
    run(u, 0x531a0ba0)
    return calls

def clock_probe(code, ready):
    u = machine(code)
    service, output = 0x55064dc8, 0x55008000
    date = struct.pack('<H6BH', 2026, 10, 15, 10, 28, 17, 0, 0)
    u.mem_write(service + 0x18c + 0x48 * 4, struct.pack('<I', ready))
    u.mem_write(service + 0x3c0, date)
    u.mem_write(output, bytes(12))
    assertions = []
    def assert_leaf(uc, address, size, data):
        if address != 0x536b93d0: return
        assertions.append(uc.reg_read(UC_ARM_REG_R0))
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE, assert_leaf)
    u.reg_write(UC_ARM_REG_R0, service)
    u.reg_write(UC_ARM_REG_R1, output)
    result = run(u, 0x532b36cc)
    return {'property_0x48': ready, 'return': result,
            'output_hex': bytes(u.mem_read(output, 10)).hex(), 'assert_conditions': assertions}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    a = p.parse_args()
    official = (a.directory / 'official-rtos.bin').read_bytes()
    uploaded = (a.directory / 'uploaded-rtos.bin').read_bytes()
    report = {'secondary_callback': {'address': '0x531a0ba0', 'index': 12,
              'official': menu_probe(official), 'uploaded': menu_probe(uploaded)},
              'official_clock': [clock_probe(official, v) for v in (0, 1, 2)],
              'limits': ['GUI model services are substituted; not an observed camera crash.',
                         'Clock property values are controlled inputs; camera log does not record this property.']}
    assert report['secondary_callback']['uploaded'][-2] == {'function': '0x532c26c0', 'value': 128}
    assert report['secondary_callback']['uploaded'][-1] == {'function': '0x532750f8', 'stored_tone': 128}
    assert report['secondary_callback']['official'] == [{'function': '0x532bd61c', 'value': 1}]
    assert [r['return'] for r in report['official_clock']] == [0, 1, 0]
    (a.directory / 'arm-probes.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()
