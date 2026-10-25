"""Bake a restrained display-sRGB to display-sRGB 5207-inspired interpretation.

The input has already passed through the camera ISP. Its scene exposure,
illuminant spectrum and sensor response cannot be recovered by sRGB decoding.
This intentionally replaces the former uncalibrated spectral/APD inversion.
All numerical look parameters below are design assumptions, not Kodak data.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/m10v-5207-matplotlib')
import numpy as np
import colour

PARAMETERS = {
    'status': 'assumed display-domain interpretation; not a measured Kodak transform',
    'input': 'encoded display sRGB D65 after camera ISP; scene radiance not recovered',
    'output': 'encoded display sRGB D65',
    'mix_matrix': [[.985,.015,0.],[.006,.988,.006],[0.,.02,.98]],
    'warm_strength': .04,
    'toe_lift': .08,
    'shoulder_compression': .025,
    'tone': 'x + toe_lift*x*(1-x)^2 - shoulder_compression*x^4',
    'white_endpoint': .975,
    'neutral_axis': 'row-stochastic matrix; warmth vanishes on neutrals; common monotone curve',
    'rendering_intent': 'restrained warm colour, neutral greys, retained blue/cyan and soft highlights',
}
RESEARCH_SOURCES = [
    {'url':'https://github.com/JanLohse/spectral_film_lut',
     'use':'prior spectral/APD research only; no upstream numerical model or code used in this mapping',
     'license':'MIT; retained vendored attribution is independent of this assumed mapping'},
    {'url':'https://janlohse.github.io/spectral_film_lut/reference/film_spectral/',
     'use':'documents scene-referred input; motivates avoiding spectral exposure simulation on camera-rendered pixels'},
]


class Reference5207:
    """Bounded encoded-display mapping, not a physical negative/scan model."""
    def render(self,rgb):
        rgb = np.asarray(rgb,dtype=np.float64)
        if rgb.ndim == 0 or rgb.shape[-1] != 3 or not np.isfinite(rgb).all():
            raise ValueError('finite RGB triples required')
        # This is an explicit bounded display-domain operation. No EOTF/OETF
        # is added: these parameters describe encoded code-value appearance.
        x = np.clip(rgb,0,1) @ np.asarray(PARAMETERS['mix_matrix']).T
        # Small warm exposure bias only where red exceeds green; keep greys
        # neutral and add no warmth to blue/cyan. Both adjustments are bounded blends.
        warm = PARAMETERS['warm_strength'] * np.maximum(x[...,0]-x[...,1],0)
        x[...,0] += warm*(1-x[...,0])
        x[...,2] *= 1-warm
        # Positive slope throughout [0,1], with no internal clipping plateau.
        # At these declared settings f(0)=0, f(1)=.975 and f'(x)>=.90.
        return x + PARAMETERS['toe_lift']*x*(1-x)**2 - PARAMETERS['shoulder_compression']*x**4


def sample_tetrahedral(table,rgb):
    size=table.shape[0]; pos=np.clip(rgb,0,1)*(size-1)
    cell=np.minimum(pos.astype(int),size-2); fraction=pos-cell
    order=np.argsort(-fraction,axis=-1,kind='stable'); result=table[tuple(cell.T)].copy()
    previous=result.copy(); corner=cell.copy(); rows=np.arange(len(cell))
    for i in range(3):
        axis=order[:,i]; corner[rows,axis]+=1; current=table[tuple(corner.T)]
        result += fraction[rows,axis,None]*(current-previous); previous=current
    return result


def generate(root=ROOT):
    root=Path(root)
    model=Reference5207(); axis=np.linspace(0,1,15)
    grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1).reshape(-1,3)
    values=np.rint(model.render(grid)*255).astype(np.uint8)
    payload=values.tobytes()
    header='/* Assumed display-sRGB interpretation; not measured Kodak. See 5207-reference.json. */\n'
    header+='static const uint8_t m10v_5207_lut[3375][3] = {\n'
    header+=''.join('{%d,%d,%d},\n'%tuple(v) for v in values)+'};\n'
    (root/'native/gr3').mkdir(parents=True,exist_ok=True)
    (root/'web/gr3').mkdir(parents=True,exist_ok=True)
    (root/'native/gr3/film_5207_data.h').write_text(header)
    (root/'web/gr3/5207-lut.json').write_text(json.dumps({'size':15,'bits':8,'order':'RGB, blue fastest','values':values.reshape(-1).tolist()},separators=(',',':'))+'\n')
    source_paths=[Path(__file__).resolve()]
    samples=np.random.default_rng(5207).uniform(.04,.96,(4096,3))
    expected=model.render(samples); actual=sample_tetrahedral(values.reshape(15,15,15,3)/255,samples)
    delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(expected)),colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual)),method='CIE 2000')
    grey_levels=np.array([0.,.1,.18,.25,.5,.75,.9,.95,1.])
    grey=model.render(np.repeat(grey_levels[:,None],3,axis=1))
    quality={'intent':'display quality constraints, not measured stock accuracy',
        'grey_input':grey_levels.tolist(),'grey_output':grey[:,0].tolist(),
        'grey_max_channel_spread':float(np.ptp(grey,axis=1).max()),
        'grey_max_abs_change':float(np.max(np.abs(grey-grey_levels[:,None]))),
        'highlight_min_step_90_95_100':float(np.diff(grey[-3:,0]).min())}
    result={'schema':'m10v-5207-reference/v2','film':'5207-inspired restrained display interpretation',
        'input':PARAMETERS['input'],'output':PARAMETERS['output'],'print_stock':None,
        'model':'bounded-display-srgb-v1','parameters':PARAMETERS,'research_sources':RESEARCH_SOURCES,'quality_validation':quality,
        'spectral_calibrated':False,'official_lut':False,'scene_radiance_recovered':False,
        'inversion_gamma':None,'color_masking':None,'neutral_correction':'neutral axis preserved algebraically before quantization',
        'camera_calibrated':False,'film_calibrated':False,'table_size':15,'table_bits':8,'table_bytes':len(payload),'table_sha256':hashlib.sha256(payload).hexdigest(),
        'sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_paths)},
        'dependencies':{n:importlib.metadata.version(n) for n in ['numpy','colour-science']},
        'interpolation_validation':{'samples':4096,'seed':5207,'encoded_domain':[.04,.96],'delta_e_00_median':float(np.median(delta)), 'delta_e_00_p95':float(np.quantile(delta,.95)), 'rgb_abs_p95':float(np.quantile(np.abs(expected-actual),.95))}}
    (root/'native/gr3/5207-reference.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'interpolation':result['interpolation_validation'],'quality':quality}))
    return result


if __name__=='__main__':generate()
