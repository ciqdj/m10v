"""Native ImageControl integration against the exact user-flashed RTOS.

These are optional evidence tests: they require the locally decoded firmware.
The controller, callback ownership/dispatch, list count/focus and selected-marker
logic execute stock ARM. Mocks stop at model/device, heap, and graphical leaves.
No mocked callback decides whether a native/private tone is safe.
"""
import json
import struct
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_PROT_READ, UC_PROT_EXEC
from unicorn.arm_const import *

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'builds/gr3-user-crash-analysis'
BASE = 0x53000000
MODEL, CONTROLLER, VIEW = 0x55068200, 0x55005000, 0x55010000
VECTOR, RECORDS, ROWS, VTABLE = 0x55018000, 0x55019000, 0x55020000, 0x55015000
STOP = 0x550ff000


@unittest.skipUnless((EVIDENCE/'RTOS-user.bin').exists(), 'decoded user firmware unavailable')
class NativeRedrawArmTests(unittest.TestCase):
    firmware_name = 'RTOS-user.bin'
    manifest_folder = 'rebuild'
    slot_five_caption = 822
    visible_film_count = 65
    slot_five_film_index = 32
    slot_one_film_index = 0
    choose_slot_index = 4

    @classmethod
    def setUpClass(cls):
        cls.firmware = (EVIDENCE/cls.firmware_name).read_bytes()
        cls.manifest = json.loads((EVIDENCE/cls.manifest_folder/'M10V-runtime-manifest.json').read_text())

    def word(self, address):
        return struct.unpack('<I', self.u.mem_read(address, 4))[0]

    def put(self, address, value):
        self.u.mem_write(address, struct.pack('<I', value))

    def setUp(self):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.u.mem_map(BASE, (len(self.firmware)+4095)&~4095)
        self.u.mem_write(BASE, self.firmware)
        self.u.mem_protect(BASE, (len(self.firmware)+4095)&~4095, UC_PROT_READ|UC_PROT_EXEC)
        self.u.mem_map(0x55000000, 0x100000)
        self.u.mem_write(MODEL, bytes([18])+bytes(35))
        self.put(CONTROLLER+0x174, VIEW)
        self.put(CONTROLLER+0x160, 0x55007000)
        row_count = self.visible_film_count + 2
        self.u.mem_write(CONTROLLER+0x1a9, bytes([row_count]))
        self.put(VIEW, VTABLE)
        self.put(VTABLE+0x18, 0x550ff100)
        self.put(VTABLE+0x5c, 0x53394600)
        self.put(VTABLE+0x58, 0x533945fc)
        self.put(VIEW+0xf4, VECTOR)
        self.put(VIEW+0xf8, VECTOR+row_count*4)
        self.put(VIEW+0x120, 60)
        for i in range(row_count):
            self.put(VECTOR+4*i, RECORDS+8*i)
            self.put(RECORDS+8*i, ROWS+0x200*i)
            self.put(ROWS+0x200*i, VTABLE)
        self.heap = 0x55040000
        self.tone = 18
        self.icons = {}; self.markers = {}; self.captions = []
        self.executed = set(); self.files = {}; self.assertions = []
        self.put(0x55004008, 0x55004100)
        self.put(0x55004100, 0x55004200)
        self.u.mem_write(0x55004220, b'\x01')
        self.u.hook_add(UC_HOOK_CODE, self.boundaries)

    def boundaries(self, u, address, size, data):
        self.executed.add(address)
        r = lambda n: u.reg_read(n)
        result = None
        if address == 0x536b93d0 and not r(UC_ARM_REG_R0):
            self.assertions.append((r(UC_ARM_REG_R0), r(UC_ARM_REG_R3)))
            self.fail('stock assertion: '+str(self.assertions[-1]))
        if address == 0x53820074:
            self.fail('stock stack protector')
        if address == 0x536b93d0: result = 0
        elif address == 0x5320ad88: result = 0x55006000
        elif address == 0x5320ba9c: result = MODEL
        elif address == 0x5320b67c: result = 0x55006000
        elif address == 0x532bd6b4: result = self.tone
        elif address == 0x532bd6d4: result = 0
        elif address == 0x532bd61c: result = 0
        elif address == 0x532c26c4:
            # Displaced prologue executed via the real native trampoline. The
            # device tone commit starts here; forbid every private menu ID.
            self.tone = r(UC_ARM_REG_R1)
            self.assertIn(self.tone, [11,12,13,14,15,16,22,17,18,19,20,21])
            result = 0
        elif address == 0x53828014: result = 0x55004000
        elif address == 0x53825648:
            ptr = r(UC_ARM_REG_R1)
            name = bytes(u.mem_read(ptr, 12)).split(b'\0')[0].decode()
            payload = self.files.get(name)
            if payload is not None:
                self.assertEqual(len(payload), r(UC_ARM_REG_R2))
                u.mem_write(r(UC_ARM_REG_R3), payload)
            result = int(payload is not None)
        elif address == 0x53825fa8:
            name = bytes(u.mem_read(r(UC_ARM_REG_R1), 12)).split(b'\0')[0].decode()
            self.files[name] = bytes(u.mem_read(r(UC_ARM_REG_R3), r(UC_ARM_REG_R2)))
            result = 1
        elif address == 0x536af2a8:
            result = self.heap; self.heap += (r(UC_ARM_REG_R0)+15)&~15
            self.assertLess(self.heap, 0x55060000)
        elif address in (0x536af2e4, 0x533ad308, 0x550ff100, 0x533a1734, 0x533a19b4):
            if address in (0x533a1734, 0x533a19b4):
                index = (r(UC_ARM_REG_R0)-ROWS)//0x200
                self.assertGreaterEqual(index, 0); self.assertLess(index, self.visible_film_count+2)
                self.assertEqual(r(UC_ARM_REG_R0), ROWS+0x200*index)
                (self.icons if address == 0x533a1734 else self.markers)[index] = r(UC_ARM_REG_R1)
            result = 0
        elif address == 0x53396f80:
            self.captions.append(r(UC_ARM_REG_R1)); result = 0
        elif address in (0x536b5580, 0x536b57d4, 0x536b57e4, 0x536b571c, 0x536b5724, 0x536b5604):
            result = r(UC_ARM_REG_R0)  # graphical rectangle leaves
        elif address == 0x533948c4: result = 0
        elif address == 0x536b57ec: result = 420
        elif address == 0x5313d850: result = r(UC_ARM_REG_R0)//r(UC_ARM_REG_R1)
        elif address == 0x5313d86c:
            dividend, divisor = r(UC_ARM_REG_R0), r(UC_ARM_REG_R1)
            u.reg_write(UC_ARM_REG_R1, dividend % divisor); result = dividend//divisor
        elif address == 0x5316ca28: result = 0  # controller exit into device event manager
        elif address in (0x53394948, 0x533951bc): result = 0  # final scroll animation
        if result is not None:
            u.reg_write(UC_ARM_REG_R0, result)
            u.reg_write(UC_ARM_REG_PC, r(UC_ARM_REG_LR))

    def call(self, address, *args):
        if isinstance(address, str): address = self.manifest['symbols'][address]
        for reg, value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3), args):
            self.u.reg_write(reg, value)
        self.u.reg_write(UC_ARM_REG_SP, 0x550fe000)
        self.u.reg_write(UC_ARM_REG_LR, STOP)
        self.u.emu_start(address, STOP, count=2000000)
        self.assertEqual(self.u.reg_read(UC_ARM_REG_PC), STOP)
        return self.u.reg_read(UC_ARM_REG_R0)

    def focus(self, index):
        self.call(0x53395430, VIEW, index)
        self.call(0x53394d34, VIEW)  # genuine view -> std::function -> controller

    def expected_slot_five_icon(self):
        return 703

    def test_slot_five_browsing_dispatch_and_native_markers(self):
        self.call(0x531ac074, CONTROLLER)
        self.focus(11)
        self.assertEqual(self.tone, 21)
        self.assertEqual(self.captions[-1], self.slot_five_caption)
        self.call(0x531ac074, CONTROLLER)
        self.assertEqual(self.icons[11], self.expected_slot_five_icon())
        self.assertEqual(self.markers[8], 1)  # original entry snapshot18
        self.assertIn(0x531ab2dc, self.executed)
        self.assertIn(0x531ab914, self.executed)
        self.assertIn(0x531ab918, self.executed)  # original focus body, after trampoline
        self.assertIn(0x53394b38, self.executed)
        self.assertIn(0x531ab1d4, self.executed)
        self.assertIn(0x531abe0c, self.executed)

    def test_open_library_and_full_65_film_list_native_redraw(self):
        self.call(0x531ac074, CONTROLLER)
        self.focus(11)
        self.focus(12)
        self.assertEqual(self.tone, 21)
        self.call('m10v_menu_confirm', CONTROLLER)
        self.assertEqual(bytes(self.u.mem_read(MODEL+0x1d, 1)), b'\x01')
        self.assertEqual(self.u.mem_read(VIEW+0x108, 1), b'\x09' if self.visible_film_count in (34,36) else b'\x08')
        self.focus(0)
        self.call('m10v_menu_confirm', CONTROLLER)
        self.assertEqual(self.u.mem_read(VIEW+0x108, 1), bytes([self.visible_film_count+2]))
        self.assertEqual(set(self.icons), set(range(self.visible_film_count+2)))
        for i in range(self.visible_film_count):
            self.focus(i)
            self.assertEqual(self.tone, 21)
        self.assertFalse(self.assertions)

    def test_stock_cancel_after_slot_five_browsing_restores_entry_tone(self):
        self.call(0x531ac074, CONTROLLER)
        self.focus(11)
        self.assertEqual(self.tone, 21)
        self.u.mem_write(0x55008000, struct.pack('<H', 0x89))
        self.call('m10v_menu_key', CONTROLLER, 0x55008000)
        self.assertEqual(self.tone, 18)
        self.assertIn(0x531ab3ac, self.executed)
        self.assertIn(0x532c282c, self.executed)

    @unittest.expectedFailure
    def test_known_flashed_bug_library_targets_highlighted_slot(self):
        # Exact flashed build mistakenly uses entry snapshot18 as its slot
        # cache. This is an integration reproduction, not a service stub.
        self.call(0x531ac074, CONTROLLER)
        self.focus(11)
        self.focus(12)
        self.call('m10v_menu_confirm', CONTROLLER)
        self.focus(0)
        self.call('m10v_menu_confirm', CONTROLLER)
        self.assertEqual(self.call(0x53394820, VIEW), self.slot_five_film_index)  # Slot5 has 800T ID33


@unittest.skipUnless((EVIDENCE/'RTOS-fixed.bin').exists(), 'decoded fixed firmware unavailable')
class FixedNativeRedrawArmTests(NativeRedrawArmTests):
    firmware_name = 'RTOS-fixed.bin'
    manifest_folder = 'names-fixed'
    slot_five_caption = 860

    def test_known_flashed_bug_library_targets_highlighted_slot(self):
        # The counterpart deliberately removes expectedFailure: genuine stock
        # list focus now opens Slot5 ID33 and preserves the cancellation value.
        super().test_known_flashed_bug_library_targets_highlighted_slot()
        self.assertEqual(self.u.mem_read(MODEL, 1), b'\x12')
        self.assertEqual(self.u.mem_read(MODEL+0x1e, 1), b'\x15')

    def test_cancel_after_opening_library_restores_entry_tone(self):
        self.call(0x531ac074, CONTROLLER)
        self.focus(11)
        self.focus(12)
        self.call('m10v_menu_confirm', CONTROLLER)
        self.u.mem_write(0x55008000, struct.pack('<H', 0x89))
        self.call('m10v_menu_key', CONTROLLER, 0x55008000)
        self.assertEqual(self.tone, 18)
        self.assertEqual(self.u.mem_read(MODEL, 1), b'\x12')


    def test_choose_slot_updates_private_target_and_preserves_cancel_snapshot(self):
        self.call(0x531ac074, CONTROLLER)
        self.focus(11)
        self.focus(12)
        self.call('m10v_menu_confirm', CONTROLLER)
        self.focus(self.choose_slot_index)
        self.call('m10v_menu_confirm', CONTROLLER)  # Choose Slot
        self.assertEqual(self.call(0x53394820, VIEW), 4)
        self.focus(0)
        self.call('m10v_menu_confirm', CONTROLLER)  # Slot1
        self.assertEqual(self.tone, 12)
        self.assertEqual(self.u.mem_read(MODEL+0x1e, 1), b'\x0c')
        self.assertEqual(self.u.mem_read(MODEL, 1), b'\x12')
        self.focus(0)
        self.call('m10v_menu_confirm', CONTROLLER)  # Choose Film for Slot1
        self.assertEqual(self.call(0x53394820, VIEW), self.slot_one_film_index)
        self.u.mem_write(0x55008000, struct.pack('<H', 0x89))
        self.call('m10v_menu_key', CONTROLLER, 0x55008000)
        self.assertEqual(self.tone, 18)


@unittest.skipUnless((EVIDENCE/'RTOS-diagnostic.bin').exists(), 'decoded diagnostic firmware unavailable')
class DiagnosticNativeRedrawArmTests(FixedNativeRedrawArmTests):
    firmware_name = 'RTOS-diagnostic.bin'
    manifest_folder = 'stock-icons-diagnostic'

    def expected_slot_five_icon(self):
        return self.call(self.manifest['base']+0x30, 0x55006000, 21)

    def test_diagnostic_wrapper_preserves_stock_icons_and_private_catalog(self):
        for tone in range(11, 23):
            expected = self.call(self.manifest['base']+0x30, 0x55006000, tone)
            actual = self.call('m10v_menu_icon', 0x55006000, tone)
            self.assertEqual(actual, expected)
        for film in range(1, 66):
            tone = 143+film if film<=32 else 213 if film==33 else 222+film
            self.assertEqual(self.call('m10v_menu_icon', 0x55006000, tone), 670+film)
        self.assertEqual(self.call('m10v_menu_name', 0x55006000, 21), 860)
        self.assertFalse(self.assertions)
