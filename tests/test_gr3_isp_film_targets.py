"""Independent mathematical checks for the offline ISP target compiler."""
import unittest
import json
from pathlib import Path
import numpy as np
from scripts.build_gr3_isp_film_targets import (
    evaluate, fit_target, quantize, fit_gate, assumed_phoenix_target,
    bake_cpu_table,
)


class FilmTargetTests(unittest.TestCase):
    def test_identity_quantization_and_endpoints(self):
        curves = np.repeat(np.linspace(0, 1, 256)[None], 3, axis=0)
        q = quantize(np.eye(3), curves, np.eye(3))
        x = np.random.default_rng(71).uniform(0, 1, (1000, 3))
        np.testing.assert_allclose(evaluate(q, x), x, atol=1/16383)
        self.assertEqual(q['matrixQ13'], [8192, 0, 0, 0, 8192, 0, 0, 0, 8192])

    def test_fit_known_crosschannel_nonlinear_target_on_holdout(self):
        rng = np.random.default_rng(401)
        train = rng.uniform(.01, .99, (800, 3))
        test = rng.uniform(.01, .99, (300, 3))
        matrix = np.array([[.88, .12, 0], [.02, .94, .04], [.06, .02, .92]])
        target = lambda x: (x @ matrix.T)**np.array([.85, 1.05, .95])
        fitted = fit_target(train, target(train), iterations=4)
        error = np.mean(np.abs(evaluate(fitted, test)-target(test)))
        self.assertLess(error, .009)

    def test_phoenix_preserves_neutral_and_skin_constraints_but_is_visible(self):
        x = np.repeat(np.linspace(0, 1, 256)[:, None], 3, axis=1)
        y = assumed_phoenix_target(x)
        self.assertLess(float(np.ptp(y, axis=1).max()), 1e-12)
        self.assertTrue(np.all(np.diff(y[:, 0]) >= 0))
        self.assertGreater(float(np.max(np.abs(y-x))), .035)
        self.assertLess(float(y.max()), 1)
        self.assertGreater(float(y[-1, 0]), .97)
        skin = np.array([[.72, .48, .36], [.45, .28, .18]])
        self.assertLess(float(np.max(np.abs(assumed_phoenix_target(skin)-skin))), .06)

    def test_gate_does_not_confuse_small_fit_error_with_camera_calibration(self):
        metrics = {'de00_p95': .1, 'de00_max': .4, 'clipped_fraction': 0., 'curves_monotonic': True}
        gate = fit_gate(metrics, calibrated=False)
        self.assertTrue(gate['deployable'])
        self.assertFalse(gate['camera_calibrated'])
        self.assertTrue(gate['requires_camera_validation'])
        self.assertIn('measured', gate['calibration_note'])
        metrics['de00_p95'] = 9
        self.assertFalse(fit_gate(metrics, calibrated=True)['fidelity_pass'])
        metrics['clipped_fraction'] = .2
        self.assertFalse(fit_gate(metrics, calibrated=True)['deployable'])

    def test_quantization_rejects_nonmonotonic_curve(self):
        curves = np.repeat(np.linspace(0, 1, 256)[None], 3, axis=0)
        curves[0, 128] = 0
        with self.assertRaises(ValueError):
            quantize(np.eye(3), curves, np.eye(3))

    def test_cpu_table_preserves_full_mapping_and_blue_fastest_order(self):
        table = bake_cpu_table(lambda x: x**2)
        self.assertEqual(table.shape, (3375, 3))
        self.assertEqual(table.dtype, np.uint8)
        self.assertEqual(table[0].tolist(), [0, 0, 0])
        self.assertEqual(table[14].tolist(), [0, 0, 255])
        self.assertEqual(table[14*15].tolist(), [0, 255, 0])
        self.assertEqual(table[-1].tolist(), [255, 255, 255])

    def test_generated_candidates_declare_calibration_limits_and_visible_change(self):
        report = json.loads((Path(__file__).resolve().parents[1]/'native/gr3/isp-film-targets.json').read_text())
        self.assertFalse(report['hardware_pixel_model_verified'])
        self.assertEqual([(r['film_id'], r['ei']) for r in report['targets']], [(66, 250), (67, 200), (68, 64), (68, 125), (68, 250)])
        for record in report['targets']:
            self.assertEqual(record['relative_matrixQ13'], record['matrixQ13'])
            self.assertFalse(record['gate']['camera_calibrated'])
            self.assertTrue(np.all(np.diff(record['curves'], axis=1) >= 0))
            self.assertGreater(record['holdout']['samples'], 1000)
        for candidate in report['cpu_candidates'].values():
            self.assertFalse(candidate['official_lut'])
            self.assertFalse(candidate['camera_calibrated'])
            self.assertLess(candidate['interpolation']['de00_p95'], 1.2)
        self.assertGreater(report['cpu_candidates']['5207']['target_vs_identity']['de00_median'], 5)
        self.assertGreater(report['cpu_candidates']['phoenix_ii']['target_vs_identity']['de00_p95'], 4)


if __name__ == '__main__':
    unittest.main()
