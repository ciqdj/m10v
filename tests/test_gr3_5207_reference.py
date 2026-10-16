"""Reference provenance and independent colour interpolation checks."""
import importlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Reference5207Tests(unittest.TestCase):
    def test_reference_generator_exists(self):
        self.assertTrue((ROOT / 'scripts/build_gr3_5207_reference.py').is_file(),
                        '5207 needs a reproducible reference generator')

    def test_neutrals_are_finite_monotone_and_colour_is_not_identity(self):
        import numpy as np
        m = importlib.import_module('scripts.build_gr3_5207_reference')
        reference = m.Reference5207()
        x = np.linspace(0, 1, 129)
        grey = reference.render(np.repeat(x[:, None], 3, axis=1))
        self.assertTrue(np.isfinite(grey).all())
        self.assertTrue(((grey >= 0) & (grey <= 1)).all())
        self.assertTrue((np.diff(grey, axis=0) >= -1e-5).all())
        self.assertLess(float(np.ptp(grey, axis=1).max()), .015)
        colours = np.array([[.8,.3,.2],[.1,.6,.25],[.2,.3,.9]])
        self.assertGreater(float(np.max(np.abs(reference.render(colours)-colours))), .01)

    def test_generated_table_matches_source_and_interpolates_held_out_samples(self):
        import json, hashlib
        import numpy as np
        m = importlib.import_module('scripts.build_gr3_5207_reference')
        manifest = json.loads((ROOT/'native/gr3/5207-reference.json').read_text())
        for name, digest in manifest['sources'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), digest)
        table = np.array(json.loads((ROOT/'web/gr3/5207-lut.json').read_text())['values']).reshape(15,15,15,3)/255
        samples = np.random.default_rng(5207).uniform(.04,.96,(1000,3))
        error = np.abs(m.sample_tetrahedral(table,samples)-m.Reference5207().render(samples))
        self.assertLess(float(np.quantile(error,.95)), .025)
        self.assertFalse(manifest['camera_calibrated'])
        self.assertFalse(manifest['film_calibrated'])


if __name__ == '__main__': unittest.main()
