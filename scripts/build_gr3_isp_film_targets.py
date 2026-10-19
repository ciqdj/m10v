"""Compile explicit offline targets to an experimental Standard-relative ISP factorization.

No JPEG inverse ISP is performed. Scene targets use synthetic paired scene XYZ
and sRGB-encoded reference RGB, never a claim that the synthetic reference is GR3
Standard. Debug-candidate validity and target-fit fidelity are reported separately
from the always-unverified camera calibration; no release-quality claim is made.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/m10v-isp-target-mpl')
import colour
import numpy as np
from scipy.optimize import minimize
from scipy.optimize import isotonic_regression

ROOT = Path(__file__).resolve().parents[1]


def quantize(matrix, curves, post):
    matrix, curves, post = map(lambda x: np.asarray(x, dtype=float), (matrix, curves, post))
    if matrix.shape != (3, 3) or post.shape != (3, 3) or curves.shape != (3, 256):
        raise ValueError('expected matrix(3,3), curves(3,256), post(3,3)')
    if not all(np.isfinite(x).all() for x in (matrix, curves, post)):
        raise ValueError('finite coefficients required')
    if np.any(np.diff(curves, axis=1) < -1e-12) or curves.min() < 0 or curves.max() > 1:
        raise ValueError('bounded monotonic curves required')
    m, p = np.rint(matrix*8192).astype(int), np.rint(post*512).astype(int)
    if np.max(np.abs(m)) > 32767 or np.max(np.abs(p)) > 32767:
        raise ValueError('signed16 coefficient overflow')
    return {'matrixQ13': m.reshape(-1).tolist(), 'postQ512': p.reshape(-1).tolist(),
            'curves': np.rint(curves*16383).astype(int).tolist()}


def evaluate(record, rgb, return_unclipped=False):
    """Floating reference factorization; NOT an emulation of unknown ISP pixels.

    Matrix and post use column-vector convention (RGB @ M.T). Curve knots
    represent 256 equally spaced normalized points; native Q14 writer indexing
    must be validated separately before deployment.
    """
    x = np.asarray(rgb, dtype=float) @ (np.asarray(record['matrixQ13']).reshape(3, 3)/8192).T
    curves = np.asarray(record['curves'])/16383
    z = np.column_stack([np.interp(x[:, c], np.linspace(0, 1, 256), curves[c]) for c in range(3)])
    out = z @ (np.asarray(record['postQ512']).reshape(3, 3)/512).T
    return out if return_unclipped else np.clip(out, 0, 1)


def fit_target(x, target, iterations=8):
    """Fit both matrices and monotonic channel curves, independently quantized.

    Optimizes 3x3 pre/post matrices and 33 knots per channel. Analytic gradients
    keep the offline compiler inexpensive; final isotonic projection is explicit.
    """
    x, target = np.asarray(x, float), np.asarray(target, float)
    n, knots = len(x), 33
    axis = np.linspace(0, 1, knots)
    initial = np.concatenate([np.eye(3).ravel(), np.eye(3).ravel(), np.tile(axis, 3)])

    def loss(params):
        m, p, curves = params[:9].reshape(3, 3), params[9:18].reshape(3, 3), params[18:].reshape(3, knots)
        raw = x @ m.T
        pos = np.clip(raw, 0, 1)*(knots-1)
        index = np.minimum(pos.astype(int), knots-2)
        frac = pos-index
        z = np.empty_like(x); slopes = np.empty_like(x)
        for c in range(3):
            low, high = curves[c, index[:, c]], curves[c, index[:, c]+1]
            z[:, c] = low*(1-frac[:, c])+high*frac[:, c]
            slopes[:, c] = (high-low)*(knots-1)*((raw[:, c] > 0)&(raw[:, c] < 1))
        residual = (z @ p.T-target)
        value = np.sum(residual**2)/n
        gradout = 2*residual/n
        gradz = gradout @ p
        gm = (gradz*slopes).T @ x
        gp = gradout.T @ z
        gc = np.zeros_like(curves)
        for c in range(3):
            np.add.at(gc[c], index[:, c], gradz[:, c]*(1-frac[:, c]))
            np.add.at(gc[c], index[:, c]+1, gradz[:, c]*frac[:, c])
        # Bound drift, discourage reversals; final projection always enforces them.
        regular = 1e-5
        value += regular*(np.sum((m-np.eye(3))**2)+np.sum((p-np.eye(3))**2))
        gm += 2*regular*(m-np.eye(3)); gp += 2*regular*(p-np.eye(3))
        diff = np.diff(curves, axis=1); backward = np.minimum(diff, 0)
        value += 10*np.sum(backward**2)
        gc[:, :-1] -= 20*backward; gc[:, 1:] += 20*backward
        return value, np.concatenate([gm.ravel(), gp.ravel(), gc.ravel()])

    fitted = minimize(loss, initial, method='L-BFGS-B', jac=True,
                      bounds=[(-.75, 1.75)]*18+[(0, 1)]*(3*knots),
                      options={'maxiter': iterations*40, 'ftol': 1e-13, 'gtol': 1e-8})
    m, p = fitted.x[:9].reshape(3, 3), fitted.x[9:18].reshape(3, 3)
    curves = fitted.x[18:].reshape(3, knots)
    dense = np.array([np.interp(np.linspace(0, 1, 256), axis, isotonic_regression(c).x) for c in curves])
    q = quantize(m, dense, p)
    q['float_reference'] = {'matrix': m.tolist(), 'post': p.tolist(), 'curves': dense.tolist()}
    q['optimization'] = {'success': bool(fitted.success), 'iterations': fitted.nit,
                         'message': str(fitted.message), 'objective': float(fitted.fun)}
    return q


def assumed_phoenix_target(rgb):
    """Explicit creative display target, not a measured/official Phoenix II LUT.

    Shared S-curve preserves neutrals; positive row-stochastic mixing avoids
    arbitrary blue offsets and out-of-gamut saturation. Every numeric value is
    a declared design assumption, not a manufacturer measurement.
    """
    x = np.clip(np.asarray(rgb, float), 0, 1)
    x = x @ np.array([[.94, .04, .02], [.03, .95, .02], [.01, .05, .94]]).T
    return .985*(x+.65*x*(1-x)*(2*x-1))


def fit_gate(metrics, calibrated):
    reasons = []
    if metrics['clipped_fraction'] > .01 or not metrics['curves_monotonic']:
        reasons.append('clipping or monotonicity gate failed')
    return {'deployable': not reasons, 'camera_calibrated': calibrated,
            'deployable_meaning': 'mathematically bounded debug candidate only; NOT camera fidelity or hardware coefficient certification',
            'fidelity_pass': metrics['de00_p95'] <= 3 and metrics['de00_max'] <= 8,
            'requires_camera_validation': True,
            'calibration_note': 'needs measured GR3 Standard scene/output pairs and native ISP pixel-stage validation',
            'blocked_reason': '; '.join(reasons) or None}


def summarize(record, x, target):
    raw = evaluate(record, x, return_unclipped=True)
    y = np.clip(raw, 0, 1)
    de = colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(target)), colour.XYZ_to_Lab(colour.sRGB_to_XYZ(y)), method='CIE 2000')
    identity = colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(x)), colour.XYZ_to_Lab(colour.sRGB_to_XYZ(target)), method='CIE 2000')
    float_reference = record['float_reference']
    u = x @ np.asarray(float_reference['matrix']).T
    z = np.column_stack([np.interp(u[:, c], np.linspace(0, 1, 256), float_reference['curves'][c]) for c in range(3)])
    float_output = np.clip(z @ np.asarray(float_reference['post']).T, 0, 1)
    quantization_de = colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(float_output)), colour.XYZ_to_Lab(colour.sRGB_to_XYZ(y)), method='CIE 2000')
    return {'samples': len(x), 'de00_median': float(np.median(de)), 'de00_p95': float(np.quantile(de, .95)),
            'de00_max': float(de.max()), 'rgb_abs_p95': float(np.quantile(np.abs(y-target), .95)),
            'clipped_fraction': float(np.mean(np.any((raw < 0)|(raw > 1), axis=1))),
            'curves_monotonic': bool(np.all(np.diff(record['curves'], axis=1) >= 0)),
            'target_vs_identity_de00_median': float(np.median(identity)),
            'target_vs_identity_de00_p95': float(np.quantile(identity, .95)),
            'quantization_vs_float_de00_p95': float(np.quantile(quantization_de, .95)),
            'quantization_vs_float_de00_max': float(quantization_de.max())}


def spectral_target(scene_xyz):
    sys.path.insert(0, str(ROOT/'third_party/spectral-film-lut/src'))
    from spectral_film_lut.film_spectral import FilmSpectral
    from spectral_film_lut.negative_film.kodak_5207 import KODAK_5207
    from spectral_film_lut.print_film.kodak_2383 import KODAK_2383
    from spectral_film_lut.utils import film_conversion
    return film_conversion(np.asarray(scene_xyz, np.float32), FilmSpectral(KODAK_5207), FilmSpectral(KODAK_2383),
                           input_colorspace=None, exp_kelvin=6500, projector_kelvin=6500,
                           output_gamut='Rec. 709', gamma_func='sRGB', color_masking=None,
                           inversion=False, sat_adjust=1, shadow_comp=0, upsampling_method='SFL upsampling')


def bake_cpu_table(render):
    axis = np.linspace(0, 1, 15)
    encoded_reference = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1).reshape(-1, 3)
    values = np.asarray(render(encoded_reference), float)
    if values.shape != (3375, 3) or not np.isfinite(values).all() or values.min() < 0 or values.max() > 1:
        raise ValueError('CPU target must provide finite bounded RGB table')
    return np.rint(values*255).astype(np.uint8)


def generate_cpu_candidates(output):
    """Full 15^3 mappings, not the lossy matrix/curve/post factorization.

    The synthetic reference's known inverse sRGB encoding defines an ASSUMED
    display adapter; this is explicitly not GR3 JPEG inverse-ISP recovery.
    """
    def synthetic_reference_5207(encoded_reference):
        scene = colour.cctf_decoding(encoded_reference, function='sRGB')
        return spectral_target(colour.RGB_to_XYZ(scene, 'sRGB', apply_cctf_decoding=False))
    from analyze_gr3_film_color_targets import native_table_rgb, metrics
    renders = {'5207': synthetic_reference_5207, 'phoenix_ii': assumed_phoenix_target}
    codes = np.random.default_rng(52076715).integers(0, 256, (4096, 3), dtype=np.uint8)
    encoded = codes/255
    header = '/* Generated FULL CPU colour candidates; no spatial effect disabled.\n * 5207 source: spectral-film-lut, MIT Jan Lohse; retain its LICENSE.\n * Display-adapter assumption, NOT measured GR3/film calibration. */\n'
    header += '#ifndef M10V_FILM_COLOR_CANDIDATES_H\n#define M10V_FILM_COLOR_CANDIDATES_H\n#include <stdint.h>\n'
    report = {}
    for name, render in renders.items():
        table = bake_cpu_table(render)
        actual = native_table_rgb(table.reshape(15, 15, 15, 3), codes)/255
        expected = render(encoded)
        header += f'static const uint8_t m10v_{name}_candidate_lut[3375][3] = {{\n'
        header += ''.join('{%d,%d,%d},\n'%tuple(v) for v in table)+'};\n'
        report[name] = {'table_size': 15, 'table_bits': 8, 'order': 'RGB axes, blue fastest',
                        'table_sha256': hashlib.sha256(table.tobytes()).hexdigest(),
                        'input': 'encoded display RGB assumed sRGB D65; assumed synthetic-reference adapter, not recovered scene radiance',
                        'output': 'encoded display sRGB D65', 'camera_calibrated': False, 'film_calibrated': False, 'official_lut': False,
                        'status': 'spectral-data-derived with assumed display adapter' if name == '5207' else 'assumed constrained Phoenix II inspired design',
                        'holdout_seed': 52076715,
                        'interpolation': metrics(expected, actual), 'target_vs_identity': metrics(encoded, expected)}
    header += '#endif\n'
    (output/'m10v_film_color_candidates.h').write_text(header)
    return report


def generate(output=ROOT/'native/gr3'):
    # Generate scene data FIRST. These are paired synthetic reference samples,
    # not JPEGs decoded and misrepresented as recovered scene radiance.
    rng = np.random.default_rng(52076766)
    scene_train = rng.uniform(0, 1, (1600, 3))**2.2
    scene_test = np.random.default_rng(671864).uniform(0, 1, (2048, 3))**2.2
    grey = np.repeat(np.linspace(0, 1, 256)[:, None], 3, axis=1)
    scene_train = np.vstack([scene_train, colour.cctf_decoding(np.tile(grey, (3, 1)), function='sRGB')])
    train, test = colour.cctf_encoding(scene_train, function='sRGB'), colour.cctf_encoding(scene_test, function='sRGB')
    # Full spectral reference is called directly; no finite-domain cube sampling.
    scene = np.vstack([scene_train, scene_test])
    xyz = colour.RGB_to_XYZ(scene, 'sRGB', apply_cctf_decoding=False)
    target5207 = spectral_target(xyz)
    sys.path.insert(0, str(ROOT/'scripts'))
    from build_gr3_harman_reference import ReferenceHarman
    specs = [(66, 250, '5207+2383 spectral research target', target5207[:len(train)], target5207[len(train):], 'spectral-data-derived; synthetic baseline adapter uncalibrated'),
             (67, 200, 'Phoenix II inspired constrained display target', assumed_phoenix_target(train), assumed_phoenix_target(test), 'assumed creative interpretation; NOT measured film')]
    for ei in (64, 125, 250):
        model = ReferenceHarman('red', ei)
        specs.append((68, ei, f'HARMAN RED inspired EI{ei}', model.render(train), model.render(test), 'assumed prior RED model; NOT measured film'))
    rows = []
    for film, ei, name, expected_train, expected_test, status in specs:
        record = fit_target(train, expected_train)
        heldout = summarize(record, test, expected_test)
        neutral = evaluate(record, grey)
        heldout['grey_max_channel_spread'] = float(np.ptp(neutral, axis=1).max())
        heldout['grey_output_min_step'] = float(np.diff(neutral, axis=0).min())
        record.update(film_id=film, ei=ei, name=name, status=status, holdout=heldout,
                      gate=fit_gate(heldout, calibrated=False))
        rows.append(record)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    cpu_candidates = generate_cpu_candidates(output)
    for row in rows:
        row['relative_matrixQ13'] = row['matrixQ13'][:]
    report = {'schema': 'm10v-gr3-isp-film-targets/v1', 'camera_calibrated': False,
              'input': 'synthetic Standard surrogate: sRGB encoded known scene-linear Rec709 D65, NOT measured GR3 Standard',
              'factorization': 'relative Standard-reference RGB column vectors: clip(P * curves(clip(M*x))); matrices are RELATIVE corrections, not absolute sensor CCM',
              'hardware_pixel_model_verified': False,
              'native_parameter_writer_validated': False,
              'assumed_phoenix_parameters': {'mix_matrix': [[.94, .04, .02], [.03, .95, .02], [.01, .05, .94]],
                                             'shared_tone': '.985*(x+.65*x*(1-x)*(2*x-1))',
                                             'status': 'all numerical parameters are design assumptions, not official film measurements'},
              'hardware_contract_blocker': 'matrixQ13 must compose at the verified Standard-relative boundary; Q14 gamma knot positions and physical matrix/curve/post order require hardware calibration',
              'curve_scaling': 'uint16 normalized by16383; 256 equally spaced reference knots; native writer indexing uncalibrated',
              'sources': [
                  {'url': 'https://github.com/JanLohse/spectral_film_lut', 'license': 'MIT Jan Lohse; third_party/spectral-film-lut/LICENSE', 'use': '5207 and 2383 spectral scene simulation'},
                  {'url': 'https://www.kodak.com/content/products-brochures/motion-picture/KODAK-VISION3-250D-5207-7207-technical-information.pdf', 'use': 'official stock characteristics; vendor profile edition not pinned'},
                  {'url': 'https://www.harmanphoto.co.uk/amfile/file/download/file/1968/product/2208/', 'use': 'qualitative Phoenix II constraints only; no claimed measured positive transform'},
              ],
              'training_seed': 52076766, 'holdout_seed': 671864,
              'sources_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
                  'scripts/build_gr3_isp_film_targets.py', 'scripts/build_gr3_harman_reference.py',
                  'third_party/spectral-film-lut/src/spectral_film_lut/negative_film/kodak_5207.py',
                  'third_party/spectral-film-lut/src/spectral_film_lut/print_film/kodak_2383.py']},
              'targets': rows, 'cpu_candidates': cpu_candidates}
    (output/'isp-film-targets.json').write_text(json.dumps(report, indent=2)+'\n')
    header = '/* Generated experimental ISP targets. NOT camera-calibrated.\n * 5207 spectral reference: MIT Jan Lohse; retain third_party/spectral-film-lut/LICENSE.\n * Relative Standard corrections; see isp-film-targets.json for blocked conditions. */\n'
    header += '#ifndef M10V_ISP_FILM_TARGETS_H\n#define M10V_ISP_FILM_TARGETS_H\n#include <stdint.h>\n'
    header += 'typedef struct { uint16_t film_id,ei; int16_t matrixQ13[9],postQ512[9]; uint16_t curves[768]; uint8_t deployable; } m10v_isp_film_target;\n'
    header += 'static const m10v_isp_film_target m10v_isp_film_targets[5] = {\n'
    for row in rows:
        def seq(v): return '{'+','.join(map(str, v))+'}'
        header += '{%d,%d,%s,%s,%s,%d},\n'%(row['film_id'], row['ei'], seq(row['matrixQ13']), seq(row['postQ512']), seq(np.asarray(row['curves']).reshape(-1)), int(row['gate']['deployable']))
    header += '};\n#define M10V_ISP_FILM_TARGET_COUNT 5\n#endif\n'
    (output/'m10v_isp_film_targets.h').write_text(header)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'native/gr3')
    args = parser.parse_args()
    report = generate(args.out)
    print(json.dumps([{'film': r['film_id'], 'ei': r['ei'], 'holdout': r['holdout'], 'gate': r['gate']} for r in report['targets']], indent=2))
