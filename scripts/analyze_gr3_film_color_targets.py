"""Measure current display mappings against identity; never regenerate production LUTs.

Run with .venv/bin/python scripts/analyze_gr3_film_color_targets.py.
Outputs are research artifacts under ignored builds/gr3-isp-research/color/.
No film accuracy claim can be inferred from these identity-distance metrics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/m10v-color-targets-mpl')
import colour
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_gr3_5207_reference import Reference5207
from build_gr3_harman_reference import ReferenceHarman


def native_table_rgb(table, codes):
    """Exact integer tetrahedral colour table stage for 8-bit RGB input.

    Does not include firmware YCbCr conversion, grain, halation or leaks.
    """
    table = np.asarray(table, dtype=np.int64)
    q = np.asarray(codes, dtype=np.int64) * (len(table) - 1)
    cell = np.minimum(q // 255, len(table) - 2)
    fraction = q - cell * 255
    order = np.argsort(-fraction, axis=-1, kind='stable')
    rows = np.arange(len(cell))
    f = np.take_along_axis(fraction, order, axis=1)
    weights = np.column_stack((255-f[:, 0], f[:, 0]-f[:, 1], f[:, 1]-f[:, 2], f[:, 2]))
    corner = cell.copy()
    total = weights[:, 0, None] * table[tuple(corner.T)]
    for i in range(3):
        corner[rows, order[:, i]] += 1
        total += weights[:, i+1, None] * table[tuple(corner.T)]
    return ((total + 127) // 255).astype(np.uint8)


def delta_e(a, b):
    lab_a = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(a))
    lab_b = colour.XYZ_to_Lab(colour.sRGB_to_XYZ(b))
    return colour.delta_E(lab_a, lab_b, method='CIE 2000')


def metrics(a, b):
    diff = np.abs(b-a)*255
    de = delta_e(a, b)
    return {
        'samples': len(a), 'rgb_code_abs_mean': float(np.mean(diff)),
        'rgb_code_abs_p95': float(np.quantile(diff, .95)),
        'rgb_code_abs_max': float(np.max(diff)),
        'de00_mean': float(np.mean(de)), 'de00_median': float(np.median(de)),
        'de00_p95': float(np.quantile(de, .95)), 'de00_max': float(np.max(de)),
        'fraction_de00_below_1': float(np.mean(de < 1)),
        'fraction_de00_below_2': float(np.mean(de < 2)),
        'fraction_rgb_all_channels_unchanged': float(np.mean(np.max(diff, axis=1) < 1e-9)),
    }


def spectral_probe(output, export_cube=False):
    """Synthetic scene XYZ only. Never decode a rendered JPEG into this path."""
    sys.path.insert(0, str(ROOT/'third_party/spectral-film-lut/src'))
    from spectral_film_lut.film_spectral import FilmSpectral
    from spectral_film_lut.negative_film.kodak_5207 import KODAK_5207
    from spectral_film_lut.print_film.kodak_2383 import KODAK_2383
    from spectral_film_lut.utils import film_conversion
    negative, positive = FilmSpectral(KODAK_5207), FilmSpectral(KODAK_2383)
    stops = np.arange(-6, 6.01, .5)
    white = colour.xy_to_XYZ(colour.CCS_ILLUMINANTS['CIE 1931 2 Degree Standard Observer']['D65'])
    scene_xyz = (white[None, :]*.18*2.0**stops[:, None]).astype(np.float32)
    parameters = dict(mode='full', input_colorspace=None, exp_kelvin=6500,
                      projector_kelvin=6500, exp_comp=0, tint=0,
                      color_masking=None, red_light=0, green_light=0, blue_light=0,
                      output_gamut='Rec. 709', gamma_func='sRGB', white_clip=True,
                      white_balance=1, sat_adjust=1, shadow_comp=0,
                      inversion=False, idealized_curve=False,
                      upsampling_method='SFL upsampling')
    rendered = film_conversion(scene_xyz.copy(), negative_film=negative,
                               print_film=positive, **parameters)
    if not np.isfinite(rendered).all():
        raise RuntimeError('nonfinite spectral research output')
    source_paths = [ROOT/'third_party/spectral-film-lut/src/spectral_film_lut'/p for p in
                    ['negative_film/kodak_5207.py', 'print_film/kodak_2383.py', 'utils.py', 'film_spectral.py']]
    (output/'spectral-scene-probe.json').write_text(json.dumps({
        'scope': 'synthetic scene-linear XYZ D65, NOT GR3 JPEG input and NOT camera-calibrated',
        'target': 'upstream digitized Kodak 5207 + Kodak 2383 print simulation',
        'license': 'MIT, Jan Lohse; preserve third_party/spectral-film-lut/LICENSE',
        'limitations': ['upstream 5207 profile year=2009; source PDF edition not pinned',
                        'spectral upsampling, interlayer and printing are approximations',
                        'no claim of measured stock accuracy or GR3 match'],
        'parameters': parameters, 'scene_middle_grey_Y': .18,
        'stops': stops.tolist(), 'input_scene_xyz': scene_xyz.tolist(),
        'output_display_srgb': rendered.tolist(),
        'channels_at_or_above_one': int(np.sum(rendered >= 1)),
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    }, indent=2)+'\n')
    (output/'spectral-reference-LICENSE.txt').write_text((ROOT/'third_party/spectral-film-lut/LICENSE').read_text())
    if export_cube:
        # .cube traversal is blue outermost, red fastest; unlike the production
        # RGB-axis table's blue-fastest order. Domain is scene-linear, NOT sRGB.
        axis = np.linspace(0, 4, 33)
        b, g, r = np.meshgrid(axis, axis, axis, indexing='ij')
        linear_rgb = np.stack((r, g, b), axis=-1).reshape(-1, 3)
        xyz = colour.RGB_to_XYZ(linear_rgb, 'sRGB', apply_cctf_decoding=False).astype(np.float32)
        result = film_conversion(xyz, negative_film=negative, print_film=positive, **parameters)
        if not np.isfinite(result).all():
            raise RuntimeError('nonfinite spectral reference LUT')
        filename = '5207-2383-scene-linear-rec709-d65-domain0-4.cube'
        text = '# MIT Jan Lohse; see spectral-reference-LICENSE.txt\n'
        text += '# RESEARCH ONLY. Scene-linear Rec709 primaries D65, Y=.18 middle grey. NOT rendered JPEG.\n'
        text += '# Kodak 5207 digitized upstream profile + 2383 print; output encoded sRGB D65.\n'
        text += '# 33^3 uniform scene-linear grid can undersample shadows; not camera-calibrated.\n'
        text += 'TITLE "5207 2383 synthetic scene reference"\nLUT_3D_SIZE 33\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 4 4 4\n'
        text += ''.join('%.9f %.9f %.9f\n'%tuple(v) for v in result)
        (output/filename).write_text(text)
        (output/'spectral-cube-contract.json').write_text(json.dumps({
            'file': filename, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
            'input': 'scene-linear RGB, Rec709/sRGB primaries, D65, no transfer encoding, reference grey RGB=.18',
            'domain_min': [0, 0, 0], 'domain_max': [4, 4, 4], 'size': 33,
            'order': 'red fastest', 'output': 'encoded display sRGB D65',
            'parameters': parameters,
            'status': 'offline research reference only; uniform linear grid undersamples shadows; no GR3 calibration',
            'calibration_required': 'compare and fit relative to measured GR3 Standard baseline; never apply directly to JPEG or additive ISP slots'
        }, indent=2)+'\n')


def verify_native(output, models, seed):
    """Cross-check Python integer sampler against compiled firmware C functions."""
    import ctypes
    import subprocess
    sources = [ROOT/'native/gr3/film_5207.c', ROOT/'native/gr3/film_harman.c']
    library = output.resolve()/'libfilm_color_check.dylib'
    subprocess.run(['cc', '-shared', '-fPIC', '-O2', *map(str, sources), '-o', str(library)], check=True)
    lib = ctypes.CDLL(str(library))
    u8 = ctypes.c_uint8*3
    samples = np.vstack((np.random.default_rng(seed).integers(0, 256, (4096, 3), dtype=np.uint8),
                         np.array([[0, 0, 0], [255, 255, 255], [255, 0, 0], [0, 255, 0], [0, 0, 255]], dtype=np.uint8)))
    report = {}
    for name, (_, table) in models.items():
        actual = []
        for pixel in samples:
            inp, out = u8(*map(int, pixel)), u8()
            if name == '5207':
                lib.m10v_5207_rgb(inp, out)
            else:
                lib.m10v_harman_rgb(0, inp, out)
            actual.append(list(out))
        error = int(np.max(np.abs(np.asarray(actual)-native_table_rgb(table, samples))))
        report[name] = {'samples': len(samples), 'max_channel_code_error': error}
        if error:
            raise RuntimeError(f'{name} native sampler differs: {error}')
    report['source_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (output/'native-sampler-verification.json').write_text(json.dumps(report, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'builds/gr3-isp-research/color')
    parser.add_argument('--seed', type=int, default=520767)
    parser.add_argument('--random-samples', type=int, default=65536)
    parser.add_argument('--spectral-probe', action='store_true',
                        help='optional synthetic scene XYZ exposure ramp through vendored 5207+2383')
    parser.add_argument('--spectral-cube', action='store_true', help='also export research-only 33-cube with scene-linear Rec709 D65 input domain [0,4]')
    parser.add_argument('--verify-native', action='store_true', help='compile current C colour samplers and cross-check 4101 RGB inputs')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    chart = colour.CCS_COLOURCHECKERS['ColorChecker 2005']
    # Published reference xyY under chart illuminant -> Bradford D65 -> encoded sRGB.
    # Quantize to represent RGB codes presented to the current colour-table stage.
    chart_rgb = colour.XYZ_to_sRGB(colour.xyY_to_XYZ(list(chart.data.values())),
                                   illuminant=chart.illuminant,
                                   chromatic_adaptation_transform='Bradford')
    chart_codes = np.floor(np.clip(chart_rgb, 0, 1)*255+.5).astype(np.uint8)
    grey = np.repeat(np.arange(256, dtype=np.uint8)[:, None], 3, axis=1)
    random_codes = np.random.default_rng(args.seed).integers(0, 256, (args.random_samples, 3), dtype=np.uint8)
    sets = {'grey_256': grey, 'colorchecker_2005_24': chart_codes, 'random_rgb8': random_codes}
    p5207 = ROOT/'web/gr3/5207-lut.json'
    ph = ROOT/'web/gr3/harman-luts.json'
    data = json.loads(p5207.read_text())
    hdata = json.loads(ph.read_text())
    phoenix = next(s for s in hdata['stocks'] if s['model'] == 'phoenix-ii')
    models = {'5207': (Reference5207(), np.asarray(data['values']).reshape(data['size'], data['size'], data['size'], 3)),
              'phoenix_ii': (ReferenceHarman('phoenix-ii'), np.asarray(phoenix['values']).reshape(hdata['size'], hdata['size'], hdata['size'], 3))}
    sources = [p5207, ph, ROOT/'scripts/build_gr3_5207_reference.py', ROOT/'scripts/build_gr3_harman_reference.py', Path(__file__)]
    report = {
        'schema': 'gr3-color-target-distance/v1', 'seed': args.seed,
        'scope': 'RGB table colour stage only; current display mapping distance to identity, NOT film matching accuracy',
        'input_contract': 'encoded display sRGB D65, integer RGB8 after ISP (assumed, uncalibrated)',
        'delta_e_contract': 'sRGB EOTF -> XYZ D65 -> Lab D65 -> CIEDE2000, kL=kC=kH=1',
        'chart_contract': 'colour-science ColorChecker 2005 xyY, Bradford adaptation to D65, sRGB encoding, round RGB8',
        'chart_clipped_channels_before_quantization': int(np.sum((chart_rgb < 0) | (chart_rgb > 1))),
        'dependencies': {p: importlib.metadata.version(p) for p in ['numpy', 'colour-science']},
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        'models': {}, 'interstock': {},
    }
    csv_rows = []
    for name, (model, table) in models.items():
        report['models'][name] = {}
        for set_name, codes in sets.items():
            rgb = codes.astype(float)/255
            actual = native_table_rgb(table, codes).astype(float)/255
            analytic = model.render(rgb)
            report['models'][name][set_name] = {
                'baked_rgb8_vs_identity': metrics(rgb, actual),
                'analytic_float_vs_identity': metrics(rgb, analytic),
                'baked_rgb8_vs_analytic': metrics(analytic, actual),
            }
            if set_name != 'random_rgb8':
                names = list(chart.data) if set_name.startswith('colorchecker') else [str(i) for i in range(256)]
                for patch, inp, out, de in zip(names, codes, np.rint(actual*255).astype(int), delta_e(rgb, actual)):
                    csv_rows.append([name, set_name, patch, *map(int, inp), *map(int, out), float(de)])
        report['models'][name]['grey_selected'] = [
            {'input': int(v), 'output': native_table_rgb(table, grey[[v]])[0].tolist()}
            for v in [0, 26, 46, 64, 128, 191, 230, 242, 255]]
    for set_name, codes in sets.items():
        report['interstock'][set_name] = metrics(
            native_table_rgb(models['5207'][1], codes)/255,
            native_table_rgb(models['phoenix_ii'][1], codes)/255)
    with (args.output/'patches.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['model', 'set', 'patch', 'input_r', 'input_g', 'input_b', 'output_r', 'output_g', 'output_b', 'de00'])
        writer.writerows(csv_rows)
    (args.output/'identity-distance.json').write_text(json.dumps(report, indent=2)+'\n')
    # Large flat patches aid visual comparison; they are synthetic reference chips.
    try:
        from PIL import Image, ImageDraw
        image = Image.new('RGB', (6*160, 3*(4*95+30)), 'white')
        draw = ImageDraw.Draw(image)
        for row, name in enumerate(['identity', '5207', 'phoenix_ii']):
            draw.text((8, row*410+8), name+' (synthetic sRGB ColorChecker)', fill='black')
            out = chart_codes if name == 'identity' else native_table_rgb(models[name][1], chart_codes)
            for i, rgb in enumerate(out):
                x, y = (i % 6)*160, row*410+30+(i//6)*95
                draw.rectangle((x+4, y+4, x+156, y+91), fill=tuple(map(int, rgb)))
        image.save(args.output/'colorchecker-comparison.png')
    except ImportError:
        pass
    if args.spectral_probe or args.spectral_cube:
        spectral_probe(args.output, args.spectral_cube)
    if args.verify_native:
        verify_native(args.output, models, args.seed)
    print(json.dumps({'output': str(args.output), 'baked_rgb8_vs_identity': {
        n: {s: report['models'][n][s]['baked_rgb8_vs_identity'] for s in sets} for n in models},
        'interstock': report['interstock']}, indent=2))


if __name__ == '__main__':
    main()
