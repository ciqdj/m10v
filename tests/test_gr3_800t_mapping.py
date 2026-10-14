import struct
import unittest
from scripts.analyze_gr3_800t_mapping import LOAD, inspect_mapping, section_mapping


class StartupMappingTests(unittest.TestCase):
    def test_section_translates_low_address_bits_and_permissions(self):
        data = bytearray(0x8000)
        struct.pack_into('<I', data, 0x5500, 0x5401c826)
        row = section_mapping(data, LOAD + 0x4000, 0x540b6000)
        self.assertEqual(row['physical'], 0x540b6000)
        self.assertFalse(row['execute_never'])
        self.assertEqual(row['access_permissions'], 2)
        self.assertTrue(row['access_permissions_extension'])

    def test_coarse_supersection_and_truncated_table_are_rejected(self):
        for word in (0, 1, 0x5405c826):
            data = bytearray(0x8000)
            struct.pack_into('<I', data, 0x5500, word)
            with self.assertRaises(ValueError):
                section_mapping(data, LOAD + 0x4000, 0x540b6000)
        with self.assertRaises(ValueError):
            section_mapping(bytes(16), LOAD + 0x4000, 0x540b6000)

    def test_unlocked_rtos_cannot_be_used_as_proof(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            inspect_mapping(bytes(0x8000))
