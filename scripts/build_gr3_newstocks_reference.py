"""Independent, traceable display approximations. Never scene/film calibration.

The four available spectral-film-lut data sets supply their OWN sensitometric
curves and visible spectral sensitivity. Display-domain adaptation (below) is
explicitly assumed; an sRGB pixel cannot recover exposure or infrared reflectance.
ProImage is a separately authored qualitative interpretation, not another stock.
T-Max uses its named community G'MIC cube, with the retained MIT license.
"""
import hashlib,json,sys,importlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'third_party/spectral-film-lut/src')]
from scripts.build_gr3_curated_reference import cube
from scripts.build_gr3_harman_reference import sample_tetrahedral
STOCKS=[
 {'id':73,'key':'fuji-c200','name':'富士 C200','ascii_name':'Fuji C200','iso':200,'grain':1,'grain_size':1,'official':'https://asset.fujifilm.com/www/my/files/2020-09/cdc2d78497ca4ff6084f02188d175f10/films_c200_datasheet_01.pdf','data':'negative_film/fuji_c200.py','symbol':'FUJI_C200'},
 {'id':74,'key':'kodak-proimage-100','name':'ProImage 100','ascii_name':'ProImage 100','iso':100,'grain':1,'grain_size':0,'official':'https://www.bhphotovideo.com/lit_files/519169.pdf','reference':'Kodak E-4L page 3 manually digitized characteristic and spectral sensitivity curves, uncertainty recorded; display adaptation, no numerical LUT copied'},
 {'id':75,'key':'kodak-tmax-100','name':'T-Max 100','ascii_name':'T-Max 100','iso':100,'grain':1,'grain_size':0,'official':'https://www.kodakprofessional.com/sites/default/files/wysiwyg/pro/resources/f4016_TMax_100.pdf','reference':'named G MIC community Kodak T-Max 100 cube; assumed sRGB input; MIT notice retained'},
 {'id':76,'key':'aerochrome-iii-1443','name':'Aerochrome','ascii_name':'Aerochrome','iso':40,'speed_system':'aerial ISO A, not pictorial ISO; metadata only, never sets camera ISO','grain':1,'grain_size':1,'official':'https://www.kodak.com/content/pdfs/amc/Specifications-and-Characteristics-of-KODAK-Aerial-Films-datasheet-EN.pdf','data':'reversal_film/kodak_aerochrome_iii.py','symbol':'KODAK_AEROCHROME_III','approximation':True,'warning':'false-colour approximation: RGB contains no near-infrared reflectance; vegetation/material identity and real infrared response cannot be reproduced'},
 {'id':77,'key':'aerocolor-iv-2460','name':'2460','ascii_name':'2460','iso':125,'grain':1,'grain_size':0,'official':'https://www.kodak.com/content/pdfs/KODAK-AEROCOLOR-III-Negative-Film-2460-datasheet-en.pdf','data':'negative_film/kodak_aerocolor.py','symbol':'KODAK_AEROCOLOR','warning':'URL filename says III; document/model identifies IV 2460; no claim of measured production-batch matching'},
 {'id':78,'key':'vision3-50d-5203','name':'5203','ascii_name':'5203','iso':50,'grain':1,'grain_size':0,'official':'https://www.kodak.com/content/products-brochures/Film/VISION3-50D-Color-Negative-Film-7203-TECHNICAL-DATA.pdf','data':'negative_film/kodak_5203.py','symbol':'KODAK_5203'},
]
PARAMETERS={'input':'encoded display sRGB D65 after ISP','output':'encoded display sRGB D65','camera_calibrated':False,'film_calibrated':False,'official_lut':False,'spectral_reconstruction':False,
 'data_adaptation':{'status':'all adaptations below are design assumptions, NOT manufacturer measurements','curve_domain':'each stock/channel characteristic curve, normalized over recorded range; display code mapped linearly into log exposure range','curve_blend':.22,'visible_cross_talk_strength':.10,'rgb_gaussian_nm':[610,545,460],'gaussian_sigma_nm':35,'curve_white':.985},
 'proimage':{'status':'E-4L page 3 chart digitization with explicit visual reading uncertainty; same display adaptation as other colour negatives; NOT measured GR3 film matching'},
 'aerochrome':{'status':'experimental visible-only false-colour approximation; no infrared channel inferred','false_colour_matrix':[[.15,.85,0],[.80,.20,0],[0,.10,.90]],'curve_blend':.16},
 'tmax':'named community LUT, converted to exactly neutral monochrome; no developer/time/temperature match claimed',
 'grain':'shared procedural grain, not copied upstream RMS data (C200 upstream RMS is copied from 5207); low ISO has fine default grain, not measured granularity'}

def data(spec):
 if spec['id']==74:
  from types import SimpleNamespace
  j=json.loads((ROOT/'docs/research/newstocks-sources/proimage-100-digitized.json').read_text());return SimpleNamespace(log_sensitivity=[dict(v) for v in j['sensitivity_rgb']],sensiometric_curve=[dict(zip(j['log_exposure'],v)) for v in j['density_rgb']])
 return getattr(importlib.import_module('spectral_film_lut.'+spec['data'][:-3].replace('/','.')),spec['symbol'])

def render(film,rgb):
 x=np.clip(np.asarray(rgb,float),0,1);s=next(s for s in STOCKS if s['id']==film)
 if film==75:
  y=sample_tetrahedral(cube(ROOT/'third_party/curated-film-luts/kodak_t-max_100.cube'),x)
  return np.repeat((y@np.array([.2126,.7152,.0722]))[:,None],3,axis=1)
 d=data(s);p=PARAMETERS['data_adaptation'];waves=np.arange(400,701);sens=[]
 for channel in d.log_sensitivity:
  a=sorted(channel.items());sens.append(10**np.interp(waves,*np.array(a).T,left=-6,right=-6))
 prim=np.exp(-.5*((waves[:,None]-np.array(p['rgb_gaussian_nm']))/p['gaussian_sigma_nm'])**2)
 m=np.array(sens)@prim;m/=m.sum(axis=1,keepdims=True);mix=(1-p['visible_cross_talk_strength'])*np.eye(3)+p['visible_cross_talk_strength']*m
 z=x@mix.T;y=np.empty_like(z)
 for c,channel in enumerate(d.sensiometric_curve):
  a=np.array(sorted(channel.items()));density=a[:,1]
  # Positive stock's characteristic density falls with exposure.
  positive=(density-density[0])/(density[-1]-density[0])
  y[:,c]=np.interp(z[:,c],(a[:,0]-a[0,0])/(a[-1,0]-a[0,0]),positive)
 y=(1-p['curve_blend'])*z+p['curve_blend']*y;y*=p['curve_white']
 if film==76:
  # Merely a colour topology; not an NIR material classifier.
  p=PARAMETERS['aerochrome'];false=x@np.array(p['false_colour_matrix']).T
  y=(1-p['curve_blend'])*false+p['curve_blend']*y
 return np.clip(y,0,1)

def generate():
 import colour
 axis=np.linspace(0,1,15);grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),-1).reshape(-1,3);hold=np.random.default_rng(7378).uniform(0,1,(8192,3));tables=[];stocks=[];reports=[]
 for spec in STOCKS:
  raw=np.rint(render(spec['id'],grid)*255).astype(np.uint8);tables.append(raw);stocks.append(dict(spec,values=raw.ravel().tolist()))
  expected=render(spec['id'],hold);actual=sample_tetrahedral(raw.reshape(15,15,15,3)/255,hold)
  delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(expected)),colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual)),method='CIE 2000')
  reports.append(dict(spec,table_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),table_bytes=raw.size,approximation=True,interpolation={'samples':8192,'seed':7378,'delta_e00_median':float(np.median(delta)),'delta_e00_p95':float(np.quantile(delta,.95)),'rgb_abs_p95':float(np.quantile(abs(expected-actual),.95))}))
 header='/* Generated independent display approximations; see newstocks-reference.json. */\nstatic const uint8_t m10v_newstocks_luts[6][3375][3]={\n'+''.join('{\n'+''.join('{%d,%d,%d},\n'%tuple(v) for v in t)+'},\n' for t in tables)+'};\n'
 (ROOT/'native/gr3/film_newstocks_data.h').write_text(header);(ROOT/'web/gr3/newstocks-luts.json').write_text(json.dumps({'size':15,'bits':8,'order':'RGB, blue fastest','stocks':stocks},ensure_ascii=False,separators=(',',':'))+'\n')
 paths=['docs/research/newstocks-sources/proimage-100-digitized.json','scripts/build_gr3_newstocks_reference.py','third_party/curated-film-luts/kodak_t-max_100.cube','third_party/curated-film-luts/LICENSE','third_party/spectral-film-lut/LICENSE']+['third_party/spectral-film-lut/src/spectral_film_lut/'+s['data'] for s in STOCKS if 'data' in s]
 result={'schema':'m10v-newstocks-reference/v1','camera_calibrated':False,'film_calibrated':False,'official_lut':False,'parameters':PARAMETERS,'stocks':reports,'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'limits':'Interpolation/native fit errors measure only encoding against these designed display targets. Actual film error is unknown; no scene/IR/GR3 camera calibration.'}
 (ROOT/'native/gr3/newstocks-reference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':generate()
