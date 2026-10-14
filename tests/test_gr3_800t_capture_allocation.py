import os
import unittest
from pathlib import Path

from scripts.analyze_gr3_800t_capture_allocation import analyze


class OriginalAllocationTests(unittest.TestCase):
    def test_rejects_unlocked_firmware(self):
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            analyze(b'not original firmware')

    def test_original_allocation_planes_and_byte_padding(self):
        path = Path(os.environ.get('GR3_RTOS_PATH', '/tmp/m10v-800t-analysis/rtos.bin'))
        if not path.exists():
            self.skipTest('Set GR3_RTOS_PATH to the locked original decoded RTOS')
        report = analyze(path.read_bytes())
        self.assertEqual(len(report['cases']), 2)
        for case in report['cases']:
            self.assertTrue(case['returned'])
            self.assertEqual(case['helperCalls'], ['0x536a2f10'])
            source, main = case['source'], case['main']
            for desc in (source, main):
                self.assertEqual(desc['allocatedHeight'], case['input']['height'])
                self.assertEqual(desc['stride'], case['input']['stride'])
                self.assertEqual(desc['gapBytes'], 144*desc['stride']+64)
                self.assertNotEqual(desc['planeSeparation'], desc['planeBytes'])
                self.assertEqual(desc['enumByte'], 2)
                self.assertEqual(desc['paddingBytes'], 'a5a5a5')
                self.assertNotEqual(desc['enumWord'], 2)
            self.assertEqual(source['planeSeparation'], main['planeSeparation'])
            enum_writes = [w for w in case['descriptorWrites'] if w['offset'] in ('0x8c', '0xcc')]
            self.assertEqual([(w['phase'], w['size']) for w in enum_writes], [('constructor', 1), ('constructor', 1)])
        full = report['cases'][0]['source']
        self.assertEqual(full['planeBytes'], 24064000)
        self.assertEqual(full['planeSeparation'], 24930368)
        self.assertEqual(full['gapBytes'], 866368)
        evidence = {item['address']: item['instruction'] for item in report['instructionEvidence']}
        self.assertTrue(evidence['0x536a3db8'].startswith('ldrb'))
        self.assertTrue(evidence['0x536a3de4'].startswith('strb'))


if __name__ == '__main__':
    unittest.main()
