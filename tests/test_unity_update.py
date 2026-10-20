"""Exercise original model-specific checksum instructions and their comparison path."""
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]

def implementation():
    source=ROOT/'scripts/analyze_unity_update.py'
    if not source.exists():raise AssertionError('shared official updater analyzer is missing')
    spec=importlib.util.spec_from_file_location('unity_update_analysis',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def component(model,name):
    filename='rg2_v003.frm' if model=='gr2' else 'rg1_v051.frm'
    script="import {readFileSync} from 'node:fs';import {readUnityModelComponent} from './node/unity-firmware.mjs';process.stdout.write(readUnityModelComponent(readFileSync(process.argv[1]),process.argv[2],process.argv[3]));"
    return subprocess.run(['node','--input-type=module','-e',script,str(ROOT/'bin'/filename),model,name],cwd=ROOT,capture_output=True,check=True).stdout

class UnityChecksumTests(unittest.TestCase):
    def test_weighted_checksum_uses_byte_position_and_u32_wrap(self):
        fn=implementation().compute_update_checksum
        self.assertEqual(fn(bytes(range(8))),118)
        self.assertEqual(fn(bytes([1,2,3,4,5]),initial_position=0xfffffffe),52)
        self.assertEqual(fn(b''),0)
        with self.assertRaises(ValueError):fn(b'a',initial_position=-1)

    def test_original_components_match_all_four_literal_factory_checksums(self):
        fn=implementation().compute_update_checksum
        for model,name,expected in [('gr2','b01firm8',0x826a5e33),('gr2','b01firm6',0xa3a80234),('gr1','b01firm8',0x7b62e1a9),('gr1','b01firm6',0x7c565038)]:
            if not (ROOT/'bin'/('rg2_v003.frm' if model=='gr2' else 'rg1_v051.frm')).exists():self.skipTest('official sample missing')
            with self.subTest(model=model,component=name):
                self.assertEqual(fn(component(model,name)[512:]),expected)

    @unittest.skipUnless((ROOT/'bin/rg2_v003.frm').exists(),'official GR II sample missing')
    def test_gr2_original_cpu_accepts_correct_checksum_rejects_mutations_and_handles_short_reads(self):
        module=implementation();code=component('gr2','b01firm8')
        for length in (0,1,3,4,511,512,513,131073):
            payload=bytes(i%251 for i in range(length));expected=module.compute_update_checksum(payload)
            result=module.execute_update_checksum(code,'gr2',payload,expected,chunks=[1,3,511,512,513])
            self.assertTrue(result['accepted'],length);self.assertEqual(result['computed_checksum'],expected)
            rejected=module.execute_update_checksum(code,'gr2',payload,expected^1)
            self.assertFalse(rejected['accepted'],length)
        payload=b'abcdef'
        expected=module.compute_update_checksum(payload)
        self.assertFalse(module.execute_update_checksum(code,'gr2',b'xbcdef',expected)['accepted'])
        self.assertFalse(module.execute_update_checksum(code,'gr2',payload,expected,declared_size=7)['accepted'])
        self.assertFalse(module.execute_update_checksum(code,'gr2',payload+b'x',expected,declared_size=6)['accepted'])
        self.assertTrue(module.execute_update_checksum(code,'gr2',bytes([1,2,3,4,5]),52,initial_position=0xfffffffe)['accepted'])

    def test_each_model_executes_its_own_full_component_checksum_and_header(self):
        module=implementation()
        for model,entry in [('gr2','0xa0057684'),('gr1','0xa0053994')]:
            filename='rg2_v003.frm' if model=='gr2' else 'rg1_v051.frm'
            if not (ROOT/'bin'/filename).exists():self.skipTest('official sample missing')
            code=component(model,'b01firm8');report=module.analyze_update(code,model)
            self.assertEqual(report['header_check_entry'],entry)
            self.assertEqual([row['comparison_equal'] for row in report['cases']],[True,False,True])
            self.assertTrue(report['checksum_cpu']['accepted'])
            disk=component(model,'b01firm6');expected=int.from_bytes(disk[0x16c:0x170],'big')
            result=module.execute_update_checksum(code,model,disk[512:],expected)
            self.assertTrue(result['accepted']);self.assertEqual(result['computed_checksum'],expected)
            with self.assertRaisesRegex(ValueError,'identity'):module.analyze_update(code,'gr1' if model=='gr2' else 'gr2')

    def test_unrecognized_code_never_executes(self):
        with self.assertRaisesRegex(ValueError,'identity'):implementation().execute_update_checksum(bytes(4096),'gr2',b'',0)

if __name__=='__main__':unittest.main()
