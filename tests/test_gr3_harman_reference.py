"""RED exposure/channel behavior and independently verified four-stock assets."""
import importlib
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HarmanReferenceTests(unittest.TestCase):
    def model(self):
        self.assertTrue((ROOT/'scripts/build_gr3_harman_reference.py').is_file(),
                        'Harman needs its own reproducible reference generator')
        return importlib.import_module('scripts.build_gr3_harman_reference')

    def test_phoenix_neutral_axis_and_chromatic_response(self):
        import numpy as np
        m = self.model()
        x = np.linspace(0, 1, 257)
        rgb = np.repeat(x[:, None], 3, axis=1)
        out = m.ReferenceHarman('phoenix-ii').render(rgb)
        self.assertTrue(np.isfinite(out).all())
        self.assertTrue((np.diff(out, axis=0) >= -1e-7).all())
        self.assertLess(float(np.ptp(out, axis=1).max()), .005)
        colors = np.array([[.8,.3,.2],[.2,.7,.3],[.1,.25,.9]])
        result = m.ReferenceHarman('phoenix-ii').render(colors)
        # Non-identity is required; a minimum aggressive grade is not. The
        # display-domain quality suite independently checks hue and highlights.
        self.assertGreater(float(np.max(np.abs(result-colors))), .005)
        self.assertGreater(result[0,0], result[0,1])
        self.assertGreater(result[1,1], result[1,0])
        self.assertGreater(result[2,2], result[2,0])

    def test_blue_exposes_both_red_and_green_instead_of_being_discarded(self):
        import numpy as np
        m = self.model()
        records = m.red_record_exposure(np.array([[0,0,0],[0,0,.5]]), 125)
        self.assertGreater(records[1,0]-records[0,0], .15)
        self.assertGreater(records[1,1]-records[0,1], .1)
        self.assertLess(records[1,2], records[1,1]*.15)
        out = m.ReferenceHarman('red').render(np.array([[0,0,.7]]))[0]
        self.assertGreater(out[0], out[1])
        self.assertGreater(out[1], out[2])

    def test_ei_changes_color_response_and_precedes_nonlinearity(self):
        import numpy as np
        m = self.model()
        rgb = np.array([[.2,.35,.6],[.65,.65,.65]])
        low = m.ReferenceHarman('red', 64).render(rgb)
        normal = m.ReferenceHarman('red', 125).render(rgb)
        high = m.ReferenceHarman('red', 250).render(rgb)
        self.assertTrue((low > normal).all())
        self.assertTrue((normal > high).all())
        self.assertTrue((low[:,1]/low[:,0] > high[:,1]/high[:,0]).all())
        self.assertGreater(float(np.max(np.abs(low-normal*(125/64)))), .05)
        record = m.red_record_exposure(np.array([[.2,.3,.4]]), 64)
        np.testing.assert_allclose(record, m.red_record_exposure(np.array([[.2,.3,.4]]),125)*(125/64))

    def test_generated_assets_verify_and_reject_mutations(self):
        m = self.model()
        verify = importlib.import_module('scripts.verify_gr3_harman_reference').verify
        payloads = verify(ROOT)
        self.assertEqual([len(p) for p in payloads], [10125]*4)
        self.assertEqual(len(set(payloads)), 4)
        manifest = json.loads((ROOT/'native/gr3/harman-reference.json').read_text())
        self.assertFalse(manifest['camera_calibrated'])
        self.assertFalse(manifest['film_calibrated'])
        for item in manifest['stocks']:
            self.assertLess(item['interpolation_validation']['rgb_abs_p95'], .025)
            self.assertLess(item['interpolation_validation']['delta_e_00_p95'], 3.0)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['scripts/build_gr3_harman_reference.py','native/gr3/film_harman_data.h',
                         'native/gr3/harman-reference.json','web/gr3/harman-luts.json']:
                (root/name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, root/name)
            self.assertEqual(verify(root),payloads)
            path = root/'web/gr3/harman-luts.json'
            original = path.read_bytes()
            data = json.loads(original)
            for bad in [-1, 256, 1.5, True]:
                data['stocks'][0]['values'][0] = bad
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError): verify(root)
            path.write_bytes(original)
            data = json.loads(original); data['stocks'][1]['ei'] = 400
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError): verify(root)
            path.write_bytes(original)
            manifest_path = root/'native/gr3/harman-reference.json'
            manifest_original = manifest_path.read_bytes()
            changed = json.loads(manifest_original)
            changed['parameters']['red']['record_matrix'][0][2] = 0
            changed['parameters_sha256'] = hashlib.sha256(json.dumps(changed['parameters'], sort_keys=True, separators=(',',':')).encode()).hexdigest()
            manifest_path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError): verify(root)
            manifest_path.write_bytes(manifest_original)
            header = root/'native/gr3/film_harman_data.h'
            header_original = header.read_text()
            header.write_text(header_original.replace('{0,0,0}', '{1,0,0}', 1))
            with self.assertRaises(ValueError): verify(root)
            header.write_text(header_original)
            source = root/'scripts/build_gr3_harman_reference.py'
            source.write_text(source.read_text()+'\n# corrupted\n')
            with self.assertRaises(ValueError): verify(root)


if __name__ == '__main__': unittest.main()
