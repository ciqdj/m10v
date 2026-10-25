"""Bake the complete same-stock spectral negative -> paper -> sRGB pipeline.

The input is rendered sRGB, not recovered scene radiance. The model and its
paper/exposure choices are reproducible references, never physical calibration.
"""
import hashlib,json,sys,os
from functools import cache
from pathlib import Path
os.environ.setdefault('NUMBA_NUM_THREADS','4')
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'third_party/spectral-film-lut/src')]
STOCKS=[
 {'id':77,'key':'aerocolor-iv-2460','name':'2460','symbol':'KODAK_AEROCOLOR','data':'negative_film/kodak_aerocolor.py','official':'https://www.kodak.com/content/pdfs/amc/KODAK-AEROCOLOR-IV-Negative-Film-2460-datasheet-en.pdf','physical_process':'C-41 4:15 at38C / AN-6 equivalent','edition':'AS-2652 October 2009; official vector medium contrast curves','nominal_iso_a':125,'medium_contrast_iso_a':100,'iso_a_is_not_pictorial_iso':True},
 {'id':298,'key':'vision3-200t-5213','name':'5213','symbol':'KODAK_5213','data':'negative_film/kodak_5213.py','official':'https://www.kodak.com/content/products-brochures/Film/VISION3-200T-Color-Negative-Film-7213-TECHNICAL-DATA.pdf','physical_process':'ECN-2','edition':'H-1-5213t July 2015; historical remjet stock'},
]
PARAMETERS={'input':'encoded display sRGB D65 after ISP; not recovered scene radiance',
 'output':'encoded sRGB / Rec.709 primaries','mode':'full','paper':'Kodak Portra Endura Paper',
 'exp_kelvin':6500,'projector_kelvin':6500,'exp_comp':0,'white_clip':False,'white_balance':0,
 'apd_intermediate':True,'reference_negative':'same stock','upsampling_method':'SFL upsampling',
 'color_masking':{'77':0.0,'298':1.0},'grain':'not baked; upstream copied grain values are not used',
 'aerocolor_2460':{'characteristic_curves':'Kodak AS-2652 page6 original PDF vectors, independent R/G/B','process':'C-41 4:15 at38C; medium contrast','iso_a_reference':100,'exposure_normalization':'ISO A value used as model exposure anchor; not a calibrated pictorial ISO conversion','source':'docs/research/aerocolor-2460/official-medium-curves.json'},
 'official_lut':False,'camera_calibrated':False,'film_calibrated':False}

@cache
def models(film):
 import importlib
 from spectral_film_lut.film_spectral import FilmSpectral
 from spectral_film_lut.print_film.kodak_portra_endura import KODAK_PORTRA_ENDURA
 spec=next(s for s in STOCKS if s['id']==film)
 stock=getattr(importlib.import_module('spectral_film_lut.'+spec['data'][:-3].replace('/','.')),spec['symbol'])
 if film==77:
  from dataclasses import replace
  official=json.loads((ROOT/'docs/research/aerocolor-2460/official-medium-curves.json').read_text())
  stock=replace(stock,iso=official['iso_a_equivalent'],sensiometric_curve=[dict(c) for c in official['rgb_log_exposure_density']])
 return FilmSpectral(stock),FilmSpectral(KODAK_PORTRA_ENDURA)

def render(film,rgb):
 from spectral_film_lut.utils import film_conversion
 negative,paper=models(film)
 result=film_conversion(np.asarray(rgb,float),negative,paper,input_colorspace='sRGB',
  output_gamut='Rec. 709',gamma_func='sRGB',mode='full',
  exp_kelvin=6500,projector_kelvin=6500,exp_comp=0,white_clip=False,white_balance=0,
  color_masking=PARAMETERS['color_masking'][str(film)],apd_intermediate=True,
  reference_negative=negative,upsampling_method='SFL upsampling')
 if not np.isfinite(result).all():raise ValueError('non-finite spectral result')
 return np.clip(result,0,1)

def generate():
 import colour
 from scripts.build_gr3_harman_reference import sample_tetrahedral
 grid=np.stack(np.meshgrid(*[np.linspace(0,1,15)]*3,indexing='ij'),-1).reshape(-1,3)
 hold=np.random.default_rng(77298).uniform(0,1,(8192,3));stocks=[];reports=[]
 for spec in STOCKS:
  raw=np.rint(render(spec['id'],grid)*255).astype(np.uint8)
  expected=render(spec['id'],hold);actual=sample_tetrahedral(raw.reshape(15,15,15,3)/255,hold)
  delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(expected)),colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual)),method='CIE 2000')
  reports.append(dict(spec,table_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),table_bytes=raw.size,
   interpolation={'samples':8192,'seed':77298,'delta_e00_median':float(np.median(delta)),
    'delta_e00_p95':float(np.quantile(delta,.95)),'delta_e00_max':float(delta.max()),
    'rgb_abs_max':float(np.max(abs(expected-actual)))},camera_calibrated=False,film_calibrated=False))
  stocks.append(dict(spec,values=raw.ravel().tolist()))
 web={'size':15,'bits':8,'order':'RGB, blue fastest','stocks':stocks}
 (ROOT/'web/gr3/spectral-luts.json').write_text(json.dumps(web,separators=(',',':'))+'\n')
 extra=np.array(stocks[1]['values']).reshape(-1,3)
 (ROOT/'native/gr3/film_spectral_data.h').write_text('/* Complete same-stock spectral 5213 pipeline; see spectral-reference.json. */\nstatic const uint8_t m10v_spectral_5213_lut[3375][3]={\n'+''.join('{%d,%d,%d},\n'%tuple(v) for v in extra)+'};\n')
 # Keep all five other tables byte-identical; replace only the old 2460 target.
 current=json.loads((ROOT/'web/gr3/newstocks-luts.json').read_text())
 old=next(s for s in current['stocks'] if s['id']==77);old.update(stocks[0])
 old['reference']='complete own-stock spectral negative / Portra Endura pipeline; see spectral-reference.json'
 (ROOT/'web/gr3/newstocks-luts.json').write_text(json.dumps(current,ensure_ascii=False,separators=(',',':'))+'\n')
 (ROOT/'native/gr3/film_newstocks_data.h').write_text('/* Generated independent display approximations; see newstocks-reference.json. */\nstatic const uint8_t m10v_newstocks_luts[6][3375][3]={\n'+''.join('{\n'+''.join('{%d,%d,%d},\n'%tuple(v) for v in np.array(s['values']).reshape(-1,3))+'},\n' for s in current['stocks'])+'};\n')
 previous=json.loads((ROOT/'native/gr3/newstocks-reference.json').read_text())
 previous['stocks'][4].update(reports[0]);previous['parameters']['aerocolor_2460']=PARAMETERS
 previous['files']['scripts/build_gr3_newstocks_reference.py']=hashlib.sha256((ROOT/'scripts/build_gr3_newstocks_reference.py').read_bytes()).hexdigest()
 (ROOT/'native/gr3/newstocks-reference.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n')
 sources=[ROOT/'docs/research/aerocolor-2460/official-medium-curves.json',ROOT/'scripts/build_gr3_spectral_reference.py',ROOT/'third_party/spectral-film-lut/LICENSE',*sorted((ROOT/'third_party/spectral-film-lut/src').rglob('*.py'))]
 manifest={'schema':'m10v-spectral-reference/v1','parameters':PARAMETERS,'stocks':reports,
  'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
  'limits':'All errors compare implementation with the declared community model. Actual film and GR camera errors are unknown.'}
 (ROOT/'native/gr3/spectral-reference.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(reports,indent=2))

if __name__=='__main__':generate()
