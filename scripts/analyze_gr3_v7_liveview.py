#!/usr/bin/env python3
"""Independent stock-ARM LiveView/QuickView state probes; no firmware mutation."""
import hashlib
import struct
from pathlib import Path

BASE = 0x53000000
ROM = Path(__file__).resolve().parents[1] / 'builds/gr3-extension-validation/official-rtos.bin'
EXPECTED = '8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'

def main():
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_SP
    raw = ROM.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(BASE, (len(raw) + 4095) & ~4095)
    u.mem_write(BASE, raw)
    RAM, STACK, STOP = 0x58000000, 0x58100000, 0x58200000
    u.mem_map(RAM, 0x10000)
    u.mem_map(STACK, 0x10000)
    u.mem_map(STOP, 0x1000)
    obj, msg = RAM, RAM + 0x1000
    calls, stubs = [], {}
    def put32(a, v): u.mem_write(a, struct.pack('<I', v))
    def get32(a): return struct.unpack('<I', u.mem_read(a, 4))[0]
    def hook(uc, a, size, data):
        if a == STOP:
            uc.emu_stop()
        elif a in stubs:
            calls.append((a, uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)))
            uc.reg_write(UC_ARM_REG_R0, stubs[a])
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE, hook)
    def run(pc, r1=msg):
        calls.clear()
        u.reg_write(UC_ARM_REG_R0, obj)
        u.reg_write(UC_ARM_REG_R1, r1)
        u.reg_write(UC_ARM_REG_SP, STACK+0xff00)
        u.reg_write(UC_ARM_REG_LR, STOP)
        u.emu_start(pc, STOP+4, count=20000)
        assert u.reg_read(UC_ARM_REG_PC) == STOP
    def reset(): u.mem_write(RAM, bytes(0x2000))
    # Real completion decoder, with explicitly bounded notification/consumer services.
    stubs.update({0x5323a5cc:0,0x5320ad88:0,0x5320aefc:0,0x532288b0:0,0x53239398:0})
    for code, state in [(1,2),(2,1),(3,4),(4,2)]:
        reset(); u.mem_write(obj+8, bytes([9,5,1])); u.mem_write(msg+4, bytes([code]))
        run(0x5323a7bc)
        assert bytes(u.mem_read(obj+8,3)) == bytes([state,5,0])
        assert calls[-1][0] == 0x53239398
    # The real request entries return success while merely setting pending when busy.
    stubs.clear()
    for entry, pending in [(0x5323830c,2),(0x53238b40,1),(0x5323900c,4),(0x532391d0,5)]:
        reset(); u.mem_write(obj+8, bytes([2,0,1])); run(entry)
        assert bytes(u.mem_read(obj+8,3)) == bytes([2,pending,1])
        assert u.reg_read(UC_ARM_REG_R0) == 1 and not calls
    # Pending consumer does nothing while inflight remains nonzero.
    reset(); u.mem_write(obj+8, bytes([2,4,1])); run(0x53239398)
    assert bytes(u.mem_read(obj+8,3)) == bytes([2,4,1])
    # Real QuickView timer callback. Exit is an OS/UI boundary, not emulated hardware.
    stubs.update({0x5316c9d8:0,0x5320ad88:0,0x5320aefc:0,0x532288b0:0})
    for state in range(6):
        reset(); put32(obj+0x178, 123); u.mem_write(obj+0x16c, bytes([state]))
        run(0x531ca86c, 123)
        assert get32(obj+0x178) == 0
        assert any(c[0] == 0x5316c9d8 for c in calls) == (state <= 1)
    # The second timer posts f2 only for state 2; other states only clear token.
    for state in range(6):
        reset(); put32(obj+0x17c, 124); u.mem_write(obj+0x16c, bytes([state]))
        run(0x531ca86c, 124)
        assert get32(obj+0x17c) == 0
        posted = [c for c in calls if c[0] == 0x532288b0]
        assert bool(posted) == (state == 2)
        if posted: assert posted[0][2] == 0xf2
    reset(); put32(obj+0x178, 123); put32(obj+0x17c,124)
    run(0x531ca86c, 999)
    assert get32(obj+0x178) == 123 and get32(obj+0x17c) == 124 and not calls
    # Real backend notification translator: internal 0408100a -> 22408e31.
    stubs.clear(); stubs[0x5382fb9c]=0
    reset(); u.reg_write(UC_ARM_REG_R0, obj)
    run(0x5382fc8c, 0x0408100a)
    assert any(a==0x5382fb9c and r1==0x22408e31 for a,r0,r1 in calls)
    # Real ShootingModel dispatcher + completion producer -> local UI169.
    stubs.clear();stubs.update({0x5320ad88:0,0x5320b73c:0,0x532af2c8:0,0x5320aefc:0,0x532288b0:0})
    reset();put32(msg,0x22408e31);u.mem_write(obj+0x2f,bytes([1,0,1]))
    run(0x5323a878)
    assert any(a==0x532288b0 and r1==0x169 for a,r0,r1 in calls)
    assert bytes(u.mem_read(obj+0x8a3,1))==b'\x01'
    assert bytes(u.mem_read(obj+0x2f,3))==b'\x00\x00\x00'
    print('PASS: 24 original ARM state probes; UI/OS services stubbed, no camera/hardware claim.')

if __name__ == '__main__': main()
