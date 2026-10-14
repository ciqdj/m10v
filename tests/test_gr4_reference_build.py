"""Real pristine-input five-slot build and fresh component readback."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/gr4'))
SAMPLE = ROOT/'bin/fwdc248b-gr4-officical.bin'


@unittest.skipUnless(SAMPLE.exists(),'official GR4 sample missing')
class Gr4ReferenceBuildTests(unittest.TestCase):
    def test_pristine_official_image_builds_five_slots_with_independent_readback(self):
        from gr4_editor.toolchain import status
        from gr4_editor.service import Editor
        from gr4_editor.firmware import load_image
        from gr4_editor.filter_reader import read_filters
        from gr4_editor.slots import canonical_base
        if not status()['ready']:
            self.skipTest('ARM LLVM/LLD toolchain is unavailable')
        source=load_image(SAMPLE)
        with tempfile.TemporaryDirectory(prefix='m10v-gr4-build-test-') as folder:
            editor=Editor(Path(folder)/'data')
            project=editor.import_firmware(SAMPLE.read_bytes(),'fwdc248b.bin')
            template=next(row for row in project['filters'] if row['name']=='Positive Film')
            names=['M10V SLOT '+str(i+1) for i in range(5)]
            for name in names:
                project=editor.add_filter(project['id'],template['id'],name)
            try:
                result=editor.build(project['id'],version='1.11.10.10',allow_older=False)
            except (ValueError,TypeError) as error:
                self.fail('official five-slot build failed: '+str(error))
            output=load_image(result['firmware_path'])
            self.assertEqual(output.internal_version,'1.11.10.10')
            custom=[row for row in read_filters(output) if row['kind']=='custom']
            self.assertEqual([row['name'] for row in custom],names)
            self.assertEqual(canonical_base(output.rtos),source.rtos)
            self.assertEqual(result['report']['patch']['filter_readback']['status'],'passed')
            self.assertTrue(output.layout_proof['decoded_checksum_valid'])
            self.assertTrue(output.layout_proof['component_versions_consistent'])
            self.assertEqual(len(source.sections),len(output.sections))
            for original,new in zip(source.sections,output.sections):
                self.assertEqual(original['name'],new['name'])
                if original['name'] not in ('RTOS','CPU','SRIC','ICONBIN','RES'):
                    self.assertEqual(source.decoded[original['start']:original['end']],
                                     output.decoded[new['start']:new['end']],original['name'])


if __name__ == '__main__':
    unittest.main()
