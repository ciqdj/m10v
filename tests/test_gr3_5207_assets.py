import importlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class FilmAssetsTests(unittest.TestCase):
    def test_build_has_independent_payload_verifier(self):
        self.assertTrue((ROOT/'scripts/verify_gr3_5207_reference.py').exists())

    def test_changed_header_and_stale_model_sources_are_rejected(self):
        verify=importlib.import_module('scripts.verify_gr3_5207_reference').verify
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest=json.loads((ROOT/'native/gr3/5207-reference.json').read_text())
            for name in [*manifest['sources'],'native/gr3/5207-reference.json','native/gr3/film_5207_data.h','web/gr3/5207-lut.json']:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
            self.assertEqual(len(verify(root)),10125)
            header=root/'native/gr3/film_5207_data.h';original=header.read_text()
            header.write_text(original.replace('{','{255,0,0},\n{',1))
            with self.assertRaises(ValueError):verify(root)
            header.write_text(original)
            source=root/'scripts/build_gr3_5207_reference.py';source.write_text(source.read_text()+'\n# stale\n')
            with self.assertRaises(ValueError):verify(root)
