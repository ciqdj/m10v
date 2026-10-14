"""Execute the final original trampoline and worker chain; hardware calls are stubs."""
import ast
import struct
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm_const as reg
from scripts.build_gr3_camera_adapter import build_adapter
from scripts.build_gr3_halation import build

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime/grlife'
TRAMPOLINE, WRAPPER, ADAPTER, CORE = 0x540b936c, 0x540bb000, 0x540bb020, 0x540bb800
SEND, TIMESTAMP, STOP = 0x536abd28, 0x540ba254, 0x536afffc
APSR_MASK = 0xf80f0000


def worker_chain(timestamp):
    """Read the actual worker's literal wrapper, rather than duplicate its words."""
    tree = ast.parse((ROOT / 'node/gr3-800t-worker.py').read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'construct_800t')
    initial = next(n.value for n in function.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'chain' for t in n.targets))
    tail = next(n.value for n in function.body if isinstance(n, ast.AugAssign)
                and isinstance(n.target, ast.Name) and n.target.id == 'chain')
    if not isinstance(tail, ast.IfExp):
        raise AssertionError('worker chain no longer has reviewed timestamp branch')
    words = ast.literal_eval(initial) + ast.literal_eval(tail.body if timestamp else tail.orelse)
    return struct.pack('<' + 'I' * len(words), *words)


@unittest.skipUnless((RUNTIME / 'reconstruction/firmware_store/browser_engine.py').exists(),
                     'requires locked local original trampoline runtime')
class FinalTrampolineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(RUNTIME))
        try:
            from reconstruction.firmware_store.browser_engine import _template, _program, _timestamp_tune
            template, _ = _template()
            cls.programs = {}
            for timestamp in (False, True):
                base, _ = _program(template, [], ('timestamp',) if timestamp else (),
                                   tune=_timestamp_tune(template) if timestamp else None)
                program = bytearray(base + bytes(32768 - len(base)))
                expected = bytes.fromhex('b30300eb' if timestamp else '45f7ffeb')
                if program[0x3380:0x3384] != expected:
                    raise AssertionError('original trampoline BL preimage differs')
                if struct.unpack_from('<I', program, 0x3398)[0] != SEND:
                    raise AssertionError('original trampoline send tail target differs')
                struct.pack_into('<I', program, 0x3380, 0xeb00071e)
                chain = worker_chain(timestamp)
                program[0x5000:0x5000 + len(chain)] = chain
                cls.programs[timestamp] = bytes(program)
        finally:
            sys.path.remove(str(RUNTIME))
        with TemporaryDirectory() as folder:
            build(folder)
            cls.core = (Path(folder) / 'halation-arm.bin').read_bytes()
        cls.adapter = build_adapter(1, 18, 2)

    def run_chain(self, timestamp, tone=18, allocation=True, raw_alias=False, metadata_alias=False):
        u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for address, size in ((0x540b6000, 49152), (0x536ab000, 4096),
                              (0x536af000, 4096), (0x5383c000, 4096),
                              (0x55000000, 32768), (0x56000000, 4096),
                              (0x57000000, 4096), (0x58000000, 65536), (0x59000000, 8192)):
            u.mem_map(address, size)
        u.mem_write(0x540b6000, self.programs[timestamp])
        u.mem_write(ADAPTER, self.adapter)
        u.mem_write(CORE, self.core)
        ctx = bytearray(0x60)
        struct.pack_into('<I', ctx, 0, 0x53d0fbe0)
        for offset, value in ((0x30, 0x550001a8), (0x34, 0x55006000), (0x38, 0x55005000),
                              (0x3c, 0x550000b0), (0x48, 0x55000110), (0x4c, 0x55000130)):
            struct.pack_into('<I', ctx, offset, value)
        u.mem_write(0x550009b8, bytes(ctx))
        for address, value in ((0x55000018, 0), (0x5500005c, 0x55005000),
                               (0x550044c8, 0x55006000), (0x55005000, 0x53d0fe60),
                               (0x55000060, 0x56000000 if raw_alias else 0x59000000),
                               (0x55000230, 0x55007000)):
            u.mem_write(address, struct.pack('<I', value))
        u.mem_write(0x5500500c, b'\x01\x01')  # RAW+JPEG, CFA must stay untouched.
        u.mem_write(0x5500677c, bytes([tone]))
        for offset,value in ((0x77d,4),(0x77e,4),(0x77f,4),(0x781,4),(0x784,0)):
            u.mem_write(0x55006000+offset,bytes((value,)))
        u.mem_write(0x55000140, b'\x01')
        # Module7 has not been set up yet at module6's JPEG send hook.
        u.mem_write(0x55000a50, struct.pack('<I', 0x53d0fc30))
        u.mem_write(0x55007000, struct.pack('<HH', 6112, 4064))
        width, height, stride, allocated = 32, 17, 40, 18
        capacity = stride * allocated
        image = 0x55000000 if metadata_alias else 0x56000000
        for address, source in ((0x550000b0, image), (0x55000110, 0x5a000000)):
            u.mem_write(address, struct.pack('<4I8H', 1, source, source + capacity, 0,
                                            width, height, stride, allocated, 0, 0, 2, 0))
        pixels = bytearray([24] * capacity + [128] * capacity)
        pixels[8 * stride + 16] = 255
        before = bytes(pixels)
        u.mem_write(0x56000000, before)
        cfa = bytes((i * 37 + 19) & 255 for i in range(8192))
        u.mem_write(0x59000000, cfa)
        metadata = bytes(u.mem_read(0x55000000, 32768))
        registers = [getattr(reg, f'UC_ARM_REG_R{i}') for i in range(13)]
        original = [0x60000000 + i * 0x1111 for i in range(13)]
        original[4] = 0x550009b8
        # Select user mode before installing its banked SP/LR.
        original_cpsr = 0xa80a0010
        u.reg_write(reg.UC_ARM_REG_CPSR, original_cpsr)
        for register, value in zip(registers, original):
            u.reg_write(register, value)
        u.reg_write(reg.UC_ARM_REG_SP, 0x5800fff0)
        u.reg_write(reg.UC_ARM_REG_LR, STOP)
        events, visited = [], set()

        def caller_clobbers(uc):
            for i in (0, 1, 2, 3, 12):
                uc.reg_write(registers[i], 0x70000000 + i)
            cpsr = uc.reg_read(reg.UC_ARM_REG_CPSR)
            uc.reg_write(reg.UC_ARM_REG_CPSR, (cpsr & ~APSR_MASK) | 0x50050000)

        def external(uc, address, size, _):
            if address==0x540be000:
                result=0 if uc.reg_read(reg.UC_ARM_REG_R0)==5 else 0x80040444
                uc.reg_write(reg.UC_ARM_REG_R0,result);uc.reg_write(reg.UC_ARM_REG_PC,uc.reg_read(reg.UC_ARM_REG_LR));return
            visited.add(address)
            if address not in (0x536af2a8, 0x536af2e4, 0x5383c8a8, TIMESTAMP, SEND):
                return
            args = (uc.reg_read(reg.UC_ARM_REG_R0), uc.reg_read(reg.UC_ARM_REG_R1))
            events.append((address, *args))
            if address == SEND:
                self.assertEqual([uc.reg_read(r) for r in registers], original)
                self.assertEqual(uc.reg_read(reg.UC_ARM_REG_SP), 0x5800fff0)
                self.assertEqual(uc.reg_read(reg.UC_ARM_REG_LR), STOP)
                self.assertEqual(uc.reg_read(reg.UC_ARM_REG_CPSR) & APSR_MASK,
                                 original_cpsr & APSR_MASK)
            else:
                if address == TIMESTAMP:
                    self.assertEqual(args[0], original[4])
                    at_timestamp = bytes(uc.mem_read(0x56000000, 2 * capacity))
                    if tone == 18 and allocation and not raw_alias and not metadata_alias:
                        self.assertNotEqual(at_timestamp, before)
                    else:
                        self.assertEqual(at_timestamp, before)
                caller_clobbers(uc)
                if address == 0x536af2a8:
                    uc.reg_write(reg.UC_ARM_REG_R0, 0x57000000 if allocation else 0)
            # Explicit allocation/cache/free/timestamp/send stubs; no hardware claim.
            uc.reg_write(reg.UC_ARM_REG_PC, uc.reg_read(reg.UC_ARM_REG_LR))

        def write_guard(uc, access, address, size, value, _):
            if 0x58000000 <= address and address + size <= 0x5800fff0:
                return
            if 0x57000000 <= address and address + size <= 0x57000000 + 6 * width * height:
                return
            if 0x56000000 <= address and address + size <= 0x56000000 + 2 * capacity:
                offset = (address - 0x56000000) % capacity
                if offset // stride < height and offset % stride + size <= width:
                    return
            self.fail(f'final chain wrote outside stack/scratch/visible JPEG: {address:#x}')

        u.hook_add(UC_HOOK_CODE, external)
        u.hook_add(UC_HOOK_MEM_WRITE, write_guard)
        u.emu_start(TRAMPOLINE, STOP, count=2000000)
        self.assertEqual(u.reg_read(reg.UC_ARM_REG_PC), STOP)
        self.assertEqual([u.reg_read(r) for r in registers], original)
        self.assertEqual(u.reg_read(reg.UC_ARM_REG_SP), 0x5800fff0)
        self.assertEqual(u.reg_read(reg.UC_ARM_REG_LR), STOP)
        self.assertEqual(u.reg_read(reg.UC_ARM_REG_CPSR) & APSR_MASK, original_cpsr & APSR_MASK)
        self.assertEqual(bytes(u.mem_read(0x59000000, 8192)), cfa)
        self.assertEqual(bytes(u.mem_read(0x55000000, 32768)), metadata)
        self.assertIn(TRAMPOLINE, visited)
        self.assertIn(WRAPPER, visited)
        self.assertIn(ADAPTER, visited)
        self.assertEqual(sum(row[0] == SEND for row in events), 1)
        self.assertEqual(sum(row[0] == TIMESTAMP for row in events), int(timestamp))
        return before, bytes(u.mem_read(0x56000000, 2 * capacity)), events, visited

    def test_success_cache_and_free_precede_timestamp_and_one_send(self):
        for timestamp in (False, True):
            with self.subTest(timestamp=timestamp):
                before, after, events, visited = self.run_chain(timestamp)
                self.assertNotEqual(before, after)
                self.assertIn(CORE, visited)
                expected = [0x536af2a8]+[0x5383c8a8]*4+[0x536af2e4]
                expected += [TIMESTAMP] if timestamp else []
                self.assertEqual([row[0] for row in events], expected + [SEND])
                self.assertEqual([row[1:] for row in events[1:5]],[(0x56000000,672),(0x560002d0,672)]*2)
                self.assertEqual(events[5][1], 0x57000000)

    def test_tone_skip_preserves_state_with_timestamp_on_and_off(self):
        for timestamp in (False, True):
            with self.subTest(timestamp=timestamp):
                before, after, events, visited = self.run_chain(timestamp, tone=12)
                self.assertEqual(before, after)
                self.assertNotIn(CORE, visited)
                self.assertEqual([row[0] for row in events], ([TIMESTAMP] if timestamp else []) + [SEND])

    def test_allocation_failure_preserves_state_with_timestamp_on_and_off(self):
        for timestamp in (False, True):
            with self.subTest(timestamp=timestamp):
                before, after, events, visited = self.run_chain(timestamp, allocation=False)
                self.assertEqual(before, after)
                self.assertNotIn(CORE, visited)
                self.assertEqual([row[0] for row in events], [0x536af2a8] +
                                 ([TIMESTAMP] if timestamp else []) + [SEND])

    def test_cfa_and_metadata_aliases_skip_before_allocation(self):
        for timestamp in (False, True):
            for kwargs in ({'raw_alias': True}, {'metadata_alias': True}):
                with self.subTest(timestamp=timestamp, **kwargs):
                    before, after, events, visited = self.run_chain(timestamp, **kwargs)
                    self.assertEqual(before, after)
                    self.assertNotIn(CORE, visited)
                    self.assertEqual([row[0] for row in events],
                                     ([TIMESTAMP] if timestamp else []) + [SEND])
