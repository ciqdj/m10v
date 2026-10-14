"""Pristine GR4 entries must preserve original instructions before wrapping."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'bin/fwdc248b-gr4-officical.bin'
sys.path.insert(0, str(ROOT / 'vendor/gr4'))


@unittest.skipUnless(SAMPLE.exists(), 'official GR4 sample missing')
class OfficialEntryTests(unittest.TestCase):
    def initializer(self):
        path = ROOT / 'vendor/gr4/gr4_editor/m10v_official_entries.py'
        self.assertTrue(path.exists(), 'official GR4 entry continuation compatibility is missing')
        spec = importlib.util.spec_from_file_location('gr4_editor.m10v_official_entries', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.initialize_filter_entries

    def test_native_entries_preserve_original_instruction_and_resume_at_next_word(self):
        initialize = self.initializer()
        from gr4_editor.firmware import load_image, _Memory
        from gr4_editor.slots import _Patch, _target, _restore_scalar_fallbacks, GETTERS, SETTERS, DEFAULT_ENTRIES
        original = load_image(SAMPLE).rtos
        patch = _Patch(original)
        report = initialize(patch)
        self.assertEqual(len(report['continuations']), 35)
        for row in report['continuations']:
            site, target = int(row['site'],16), int(row['continuation'],16)
            self.assertEqual(_target(site,patch.word(site)),target)
            self.assertEqual(patch.word(target),struct.unpack_from('<I',original,site-0x53000000)[0])
            self.assertEqual(_target(target+4,patch.word(target+4)),site+4)
        fallbacks = _restore_scalar_fallbacks(patch)
        self.assertEqual(len(fallbacks),len(GETTERS+SETTERS+DEFAULT_ENTRIES))

    def test_changed_preimage_rejects_before_any_entry_is_patched(self):
        initialize = self.initializer()
        from gr4_editor.firmware import load_image
        from gr4_editor.slots import _Patch
        data = bytearray(load_image(SAMPLE).rtos)
        struct.pack_into('<I',data,0x3b7130,0xe12fff1e)
        patch = _Patch(data); before = bytes(patch.image)
        with self.assertRaisesRegex(ValueError,'preimage|identity'):
            initialize(patch)
        self.assertEqual(bytes(patch.image),before)

    def test_continuations_match_original_registers_flags_and_link_register(self):
        initialize=self.initializer()
        from gr4_editor.firmware import load_image
        from gr4_editor.slots import _Patch
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
        from unicorn.arm_const import (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
            UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R12,UC_ARM_REG_CPSR)
        original=load_image(SAMPLE).rtos;patch=_Patch(original);report=initialize(patch)
        registers=(UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,
                   UC_ARM_REG_R12,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_CPSR)
        machines=[]
        for image in (original,bytes(patch.image)):
            machine=Uc(UC_ARCH_ARM,UC_MODE_ARM)
            machine.mem_map(0x53000000,(len(patch.image)+4095)&~4095)
            machine.mem_write(0x53000000,image);machines.append(machine)
        for row in report['continuations']:
            site=int(row['site'],16);states=[]
            for machine in machines:
                for register,value in zip(registers,(0x12340000,13,35,34,0x2222,0x55030000,0x60123456,0xa0000013)):
                    machine.reg_write(register,value)
                machine.emu_start(site,site+4,count=6)
                states.append(tuple(machine.reg_read(register) for register in registers))
            self.assertEqual(states[0],states[1],row['site'])

    def test_resource_rebuild_preserves_all_three_official_34_column_banks(self):
        from gr4_editor.firmware import load_image
        from gr4_editor.slots import _Patch, TABLES, _half
        from gr4_editor.official_scaffold import initialize_scaffold
        from gr4_editor.registry_resources import rebuild_resources
        image = load_image(SAMPLE)
        patch = _Patch(image.rtos); patch.official_base = True
        originals = {}
        for family, stride, low, high in TABLES:
            self.assertEqual(patch.word(stride),0xe3a02022)
            address = _half(patch.word(low)) | _half(patch.word(high)) << 16
            from gr4_editor.firmware import _Memory
            originals[family] = _Memory(image.rtos).read(address,408)
        initialize_scaffold(patch)
        try:
            icons, report = rebuild_resources(patch,image.icon_bytes,[])
        except ValueError as error:
            self.fail('official resource rebuild rejected its verified column layout: '+str(error))
        self.assertEqual(icons,image.icon_bytes)
        for family, row in report['tables'].items():
            self.assertEqual(row['columns'],34)
            at=row['address']-0x53000000
            self.assertEqual(bytes(patch.image[at:at+408]),originals[family])


if __name__ == '__main__':
    unittest.main()
