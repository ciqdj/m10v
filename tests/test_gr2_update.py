"""Verify the original big-endian GR II header checker, not a checksum guess."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
SAMPLE=ROOT/'bin/rg2_v003.frm'


@unittest.skipUnless(SAMPLE.exists(),'official GR II sample missing')
class Gr2UpdateTests(unittest.TestCase):
    def analyzer(self):
        path=ROOT/'scripts/analyze_gr2_update.py'
        self.assertTrue(path.exists(),'GR II updater instruction analysis is missing')
        spec=importlib.util.spec_from_file_location('gr2_update_analysis',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module.analyze

    def test_native_header_checker_masks_high_bits_but_rejects_low_bit_changes(self):
        analyze=self.analyzer()
        code="import {readFileSync} from 'node:fs'; import {readGr2Component} from './node/gr2-firmware.mjs'; process.stdout.write(readGr2Component(readFileSync(process.argv[1]),'b01firm8'));"
        data=subprocess.run(['node','--input-type=module','-e',code,str(SAMPLE)],cwd=ROOT,capture_output=True,check=True).stdout
        result=analyze(data)
        self.assertEqual(result['header_check_entry'],'0xa0057684')
        self.assertEqual(result['byte_order'],'big-endian')
        self.assertEqual(result['header']['file_bytes'],6132308)
        self.assertEqual(result['header']['data_bytes'],6131796)
        self.assertEqual(result['header']['update_checksum'],'0x826a5e33')
        self.assertEqual([row['comparison_equal'] for row in result['cases']],[True,False,True])
        self.assertTrue(all(row['returned'] for row in result['cases']))
        self.assertTrue(result['modified_checksum_proved'])
        self.assertTrue(result['checksum_cpu']['accepted'])

    def test_unrecognized_updater_is_rejected_before_executing_cpu_code(self):
        with self.assertRaisesRegex(ValueError,'identity'):
            self.analyzer()(bytes(4096))


if __name__=='__main__':
    unittest.main()
