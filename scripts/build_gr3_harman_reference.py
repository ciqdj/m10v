"""Bake assumed HARMAN interpretations, never official/measured film LUTs.

Encoded sRGB input is an assumption; no GR3 ISP inversion or calibration.
All free parameters are explicitly assumed, informed by qualitative sources.
"""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/m10v-harman-matplotlib')
import numpy as np
import colour

ROOT = Path(__file__).resolve().parents[1]
SIZE = 15
PARAMETERS = {
    'status': 'assumed; qualitative interpretation, not measured film data',
    'input': 'encoded sRGB D65; scene spectrum and GR3 ISP not recovered',
    'phoenix_ii': {
        'status': 'assumed restrained display interpretation; not measured film data',
        'input': 'encoded display sRGB D65 after camera ISP',
        'output': 'encoded display sRGB D65',
        'model': 'bounded-display-srgb-v1',
        'warm_strength': .025,
        'blue_cyan_strength': .16,
        'blue_fill': .75,
        'toe_lift': .04,
        'shoulder_compression': .018,
        'tone': 'x + toe_lift*x*(1-x)^2 - shoulder_compression*x^4',
        'neutral_axis': 'all chromatic changes vanish on neutral RGB; common monotone curve',
        'calibration': 'no GR3 calibration, no scene reconstruction, no measured stock matching',
        'ei': {'base':200,'options':[200,120],
               'adapter':'decode sRGB; g=200/EI; y=g*x/(1+(g-1)*x); encode sRGB before display look',
               'status':'assumed display exposure adapter with white-preserving shoulder; not recovered scene exposure or measured EI120 stock data'},
    },
    'red': {
        'status': 'all numeric parameters assumed; official channel topology only',
        'record_matrix': [[1.,0.,.65],[0.,.78,.45],[0.,0.,.035]],
        'density_knee': [.24,.32,.4], 'density_scale': [1.65,1.65,1.65],
        'scan_power': [.92,1.18,1.32], 'scan_gain': [1.,.72,.24],
        'exposure': 'linear record exposure multiplied by 125/EI before density',
        'grain_relative': {'64': .85, '125': 1., '250': 1.2},
    },
    'spatial_effects': 'grain, diffusion and leaks use shared user controls; no baked halation',
}
STOCKS = [
    {'id':67,'name':'HARMAN Phoenix II 200','model':'phoenix-ii','ei':200},
    {'id':68,'name':'HARMAN RED 125','model':'red','ei':125},
    {'id':68,'name':'HARMAN RED 125','model':'red','ei':64},
    {'id':68,'name':'HARMAN RED 125','model':'red','ei':250},
    {'id':67,'name':'HARMAN Phoenix II 200','model':'phoenix-ii','ei':120},
]
SOURCES = [
    {'url':'https://www.harmanphoto.co.uk/amfile/file/download/file/1965/product/2170/',
     'description':'RED technical information, June 2025, 5 pages; channel topology and qualitative exposure behavior; curves not digitized'},
    {'url':'https://www.harmantechnology.com/harman-red-125-a-brand-new-professionally-finished-redscale-film/',
     'description':'Official RED launch: original Phoenix emulsion reversed, C41, no anti-halation'},
    {'url':'https://www.harmanphoto.co.uk/amfile/file/download/file/1968/product/2208/',
     'description':'Official Phoenix II technical information, Jul 2025, 5 pages: second generation, possible high-contrast halation, no orange mask; qualitative constraints only'},
    {'url':'https://www.harmanphoto.co.uk/harman-phoenix-ii-35mm',
     'description':'Official Phoenix II product: qualitative color/contrast/grain direction only'},
]


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def red_record_exposure(linear_rgb, ei=125):
    if not np.isfinite(ei) or ei <= 0:
        raise ValueError('EI must be positive and finite')
    return np.maximum(np.asarray(linear_rgb,dtype=float),0) @ np.array(PARAMETERS['red']['record_matrix']).T * (125/ei)


class ReferenceHarman:
    def __init__(self, stock='phoenix-ii', ei=None):
        if stock not in ('phoenix-ii','red'):
            raise ValueError('unknown Harman stock')
        if ei is None: ei = 200 if stock == 'phoenix-ii' else 125
        if not np.isfinite(ei) or ei <= 0 or (stock == 'phoenix-ii' and ei not in (120,200)):
            raise ValueError('EI must be positive and finite')
        self.stock, self.ei = stock, ei

    def render(self,rgb):
        rgb = np.asarray(rgb,dtype=float)
        if rgb.shape[-1] != 3 or not np.isfinite(rgb).all():
            raise ValueError('finite RGB triples required')
        if self.stock == 'phoenix-ii':
            p = PARAMETERS['phoenix_ii']
            # Parameters describe already-rendered display code values. There
            # is no attempted inverse ISP or conversion into scene exposure.
            x = np.clip(rgb,0,1).copy()
            if self.ei != 200:
                # Display-domain adaptation only: missing sensor/scene spectra
                # cannot be reconstructed from rendered RGB. The shoulder
                # keeps white and highlight detail instead of hard clipping.
                linear = colour.cctf_decoding(x,function='sRGB')
                gain = 200/self.ei
                x = colour.cctf_encoding(gain*linear/(1+(gain-1)*linear),function='sRGB')
            warm = p['warm_strength']*np.maximum(x[...,0]-x[...,1],0)
            x[...,0] += warm*(1-x[...,0])
            x[...,2] *= 1-warm
            # A bounded chromatic blend strengthens blue/cyan without a fixed
            # blue offset. Neutrals and warm skin never activate this branch.
            cool = p['blue_cyan_strength']*np.maximum(x[...,2]-x[...,0],0)
            x[...,0] *= 1-cool
            x[...,2] += p['blue_fill']*cool*(1-x[...,2])
            # Derivative is positive over [0,1]; white is .982 rather than a
            # prematurely clipped plateau. No internal hard gamut clipping.
            return x+p['toe_lift']*x*(1-x)**2-p['shoulder_compression']*x**4
        else:
            # Preserve all RED computation and ordering exactly.
            linear = colour.cctf_decoding(np.clip(rgb,0,1),function='sRGB')
            p = PARAMETERS['red']
            exposure = red_record_exposure(linear,self.ei)
            # Assumed saturating density response; scanning inverts negative
            # transmission to a positive density signal, with fixed scan balance.
            density = np.log1p(exposure/np.array(p['density_knee']))
            density /= np.log1p(np.array(p['density_scale'])/np.array(p['density_knee']))
            positive = density**np.array(p['scan_power'])*np.array(p['scan_gain'])
        return np.clip(colour.cctf_encoding(np.clip(positive,0,1),function='sRGB'),0,1)


def sample_tetrahedral(table,rgb):
    """RGB axes with blue fastest, matching the native firmware LUT sampler."""
    table=np.asarray(table,dtype=float); rgb=np.asarray(rgb,dtype=float)
    pos=np.clip(rgb,0,1)*(table.shape[0]-1)
    cell=np.minimum(pos.astype(int),table.shape[0]-2); fraction=pos-cell
    order=np.argsort(-fraction,axis=-1,kind='stable')
    result=table[tuple(cell.T)].copy(); previous=result.copy(); corner=cell.copy()
    rows=np.arange(len(cell))
    for i in range(3):
        axis=order[:,i]; corner[rows,axis]+=1; current=table[tuple(corner.T)]
        result+=fraction[rows,axis,None]*(current-previous); previous=current
    return result


def generate(root=ROOT):
    root=Path(root); axis=np.linspace(0,1,SIZE)
    grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),axis=-1).reshape(-1,3)
    # Separate deterministic holdout points, not LUT nodes or fitting data.
    samples=np.random.default_rng(68125).uniform(0,1,(8192,3))
    tables=[]; web_stocks=[]; manifest_stocks=[]
    for spec in STOCKS:
        model=ReferenceHarman(spec['model'],spec['ei'])
        values=np.rint(model.render(grid)*255).astype(np.uint8); tables.append(values)
        actual=sample_tetrahedral(values.reshape(SIZE,SIZE,SIZE,3)/255,samples)
        expected=model.render(samples)
        delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(expected)),
            colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual)),method='CIE 2000')
        stats={'samples':8192,'seed':68125,'encoded_domain':[0,1],
               'rgb_abs_p95':float(np.quantile(np.abs(expected-actual),.95)),
               'rgb_abs_max':float(np.max(np.abs(expected-actual))),
               'delta_e_00_median':float(np.median(delta)),
               'delta_e_00_p95':float(np.quantile(delta,.95)),
               'delta_e_00_max':float(np.max(delta))}
        web_stocks.append(dict(spec,values=values.reshape(-1).tolist()))
        manifest_stocks.append(dict(spec,table_bytes=values.size,
            table_sha256=hashlib.sha256(values.tobytes()).hexdigest(),interpolation_validation=stats))
        if spec['model']=='phoenix-ii':
            levels=np.array([0.,.1,.25,.5,.75,.9,.95,1.])
            gray=model.render(np.repeat(levels[:,None],3,axis=1))
            manifest_stocks[-1]['display_mapping']={
                'model':PARAMETERS['phoenix_ii']['model'],
                'input':PARAMETERS['phoenix_ii']['input'],
                'output':PARAMETERS['phoenix_ii']['output'],
                'scene_radiance_recovered':False,
                'intent':'restrained neutral/warm display look with selective blue/cyan; not a measured stock match',
                'grey_input':levels.tolist(),'grey_output':gray[:,0].tolist(),
                'grey_max_abs_change':float(np.max(np.abs(gray-levels[:,None]))),
                'highlight_min_step_90_95_100':float(np.diff(gray[-3:,0]).min())}

    header='/* Generated assumed HARMAN models; see harman-reference.json. Not official LUTs. */\n'
    header+='static const uint8_t m10v_harman_luts[5][3375][3] = {\n'
    for values in tables:
        header+='{\n'+''.join('{%d,%d,%d},\n'%tuple(v) for v in values)+'},\n'
    header+='};\n'
    (root/'native/gr3').mkdir(parents=True,exist_ok=True)
    (root/'web/gr3').mkdir(parents=True,exist_ok=True)
    (root/'native/gr3/film_harman_data.h').write_text(header)
    web={'size':SIZE,'bits':8,'order':'RGB, blue fastest','stocks':web_stocks}
    (root/'web/gr3/harman-luts.json').write_text(json.dumps(web,separators=(',',':'))+'\n')
    manifest={'schema':'m10v-harman-reference/v1','table_size':SIZE,'table_bits':8,
        'order':'RGB, blue fastest','camera_calibrated':False,'film_calibrated':False,
        'spectral_calibrated':False,'official_lut':False,
        'parameters':PARAMETERS,'parameters_sha256':hashlib.sha256(canonical(PARAMETERS)).hexdigest(),
        'sources':SOURCES,'sources_sha256':hashlib.sha256(canonical(SOURCES)).hexdigest(),
        'generator':{'path':'scripts/build_gr3_harman_reference.py','sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'dependencies':{n:importlib.metadata.version(n) for n in ['numpy','colour-science']},
        'stocks':manifest_stocks}
    (root/'native/gr3/harman-reference.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps([{'model':s['model'],'ei':s['ei'],**s['interpolation_validation']} for s in manifest_stocks],indent=2))
    return manifest


if __name__=='__main__': generate()
