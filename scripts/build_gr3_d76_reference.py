"""Seven explicit display-sRGB B/W targets, never physical film calibration.

Official speed/development notes constrain identity only. They do not determine
RGB weights, tone curves, grain or an inverse camera transform. Authored
coefficients below are deliberately labelled design assumptions.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_gr3_curated_reference import cube
from scripts.build_gr3_harman_reference import sample_tetrahedral
ASSETS=ROOT/'third_party/d76-film-luts'
REVISION='af957b631a304e6be94778b96cb3395de3438e9f'
STOCKS=[
 dict(id=299,key='trix-400',name='Tri-X 400',iso=400,cube='kodak_tri-x_400.cube',title='TRI-X',code='400',color='#49443b',official='https://www.kodakprofessional.com/sites/default/files/wysiwyg/pro/resources/f4017_trix_320400_0.pdf',official_note='400TX, not 320TXP. D-76 stock 20 C small tank 6.75 min; publication F-4017. Community emulsion generation and developer are undocumented.'),
 dict(id=300,key='ilford-delta-100',name='Ilford Delta 100',iso=100,cube='ilford_delta_100.cube',title='DELTA',code='100',color='#777b83',official='https://www.ilfordphoto.com/amfile/file/download/file/3/product/681/',official_note='Delta 100 Professional, ISO 100, fine-grain core-shell stock; D-76 stock 20 C 9 min at EI 100 (ID-11 stock is 8.5 min). Apr 2023 technical sheet.'),
 dict(id=301,key='ilford-pan-400',name='Ilford Pan 400',iso=400,title='PAN',code='400',color='#b19b51',official='https://125px.com/docs/unsorted/ilford/ilford_pan100_400.pdf',official_note='ILFORD manufacturer fact sheet, March 2002, archived by 125px. PAN 400, not Kentmere, HP5 or Pan F. D-76 stock 20 C 7 min at EI 400; 1+1 13 min. No spectral/density curve supplied.'),
 dict(id=302,key='rollei-infrared-400',name='Rollei Infrared 400',iso=400,cube='rollei_ir_400.cube',title='INFRARED',code='400 IR',color='#9c473b',official='https://www.rolleianalog.com/wp-content/uploads/2021/07/INFRARED_Data-Sheet_EN_R210701.pdf',official_note='R210701: hyperpanchromatic, nominal ISO 200-400; extended response 650-750 nm; recommended filters 715-730 nm. D-76/ID-11 stock 20 C 10:50, gamma 0.65 guideline.',infrared_style=True),
 dict(id=303,key='ilford-sfx-200',name='Ilford SFX 200',iso=200,title='SFX',code='200 IR',color='#923f40',official='https://www.ilfordphoto.com/amfile/file/download/file/1907/product/701/',official_note='Nov 2018 SFX 200 extended-red stock. Deep-red filtered target: dark blue sky and bright green foliage. D-76 stock 20 C 10 min, 1+1 14.5 min at EI 200.',infrared_style=True),
 dict(id=304,key='fomapan-400',name='Fomapan 400',iso=400,title='FOMAPAN',code='400',color='#387e9e',official='https://www.foma.cz/en/fomapan-400',official_note='Fomapan 400 Action, nominal ISO 400. Official 04/23 sheet: D-76/ID-11 stock 20 C 7-8 min. Published characteristic curve and RMS 17.5 concern Microphen, not a D-76 measurement.'),
 dict(id=305,key='catlabs-x-film-80-mkii',name='CatLABS X Film 80',iso=80,title='X FILM',code='80 MKII',color='#71916f',official='https://www.catlabs.info/product/clxf80ii',official_note='User-delegated choice: MKII formulation; exact display name unchanged. Maker describes fine grain, moderate contrast and broad tones; D-76/ID-11 stock 20 C 8 min at EI 80, 1+1 11 min. No full density/spectral curve published.',formulation='MKII'),
]
PARAMETERS={
 'input':'encoded display sRGB D65 after camera ISP; not scene-linear, log or spectral exposure',
 'status':'all RGB weights, tone knots and foliage boost are authored design assumptions, not digitized manufacturer curves',
 'tone_in':[0,.03,.08,.18,.4,.7,1],
 'pan400':{'weights':[.27,.61,.12],'tone_out':[0,.018,.06,.18,.43,.76,.99]},
 'sfx200':{'weights':[.42,.56,.02],'tone_out':[0,.015,.045,.16,.45,.81,1],'green_boost':.22},
 'fomapan400':{'weights':[.28,.61,.11],'tone_out':[.004,.013,.043,.16,.44,.80,.985]},
 'catlabs80':{'weights':[.29,.60,.11],'tone_out':[.012,.033,.09,.21,.44,.72,.96]},
 'infrared':'visible-RGB filtered-look approximation only. No recovery of near-IR reflection or semantic vegetation mask; arbitrary green objects may brighten too.',
 'grain':'LUTs contain no spatial grain, sharpness, MTF or resolution emulation; existing user-controlled native grain is unchanged',
 'community_encoding':'upstream input encoding/developer/printing workflow unspecified; display sRGB is an explicit adaptation assumption',
}

def render(film,rgb):
 from scipy.interpolate import PchipInterpolator
 x=np.clip(np.asarray(rgb,float),0,1);s=next(s for s in STOCKS if s['id']==film)
 if 'cube' in s:
  out=sample_tetrahedral(cube(ASSETS/s['cube']),x)
  # These three source cubes are already exactly monochrome.
  if np.max(np.ptp(out,axis=1))>1e-8:raise ValueError('community source is not neutral')
  return out
 p=PARAMETERS[{301:'pan400',303:'sfx200',304:'fomapan400',305:'catlabs80'}[film]]
 l=x@np.array(p['weights'])
 if film==303:l+=p['green_boost']*np.maximum(x[:,1]-np.maximum(x[:,0],x[:,2]),0)
 y=PchipInterpolator(PARAMETERS['tone_in'],p['tone_out'])(np.clip(l,0,1))
 return np.repeat(np.clip(y,0,1)[:,None],3,axis=1)

def generate():
 import colour
 grid=np.stack(np.meshgrid(*[np.linspace(0,1,15)]*3,indexing='ij'),-1).reshape(-1,3)
 hold=np.random.default_rng(299305).uniform(0,1,(8192,3));tables=[];stocks=[];reports=[]
 for spec in STOCKS:
  raw=np.rint(render(spec['id'],grid)*255).astype(np.uint8);tables.append(raw)
  reference=('same-stock G MIC community LUT; adaptation assumes display sRGB' if 'cube' in spec else 'independent official-informed tonal interpretation; no verified same-stock community LUT or physical calibration')
  stock=dict(spec,reference=reference,grain=0,grain_size=0,approximation=True,official_lut=False,camera_calibrated=False,film_calibrated=False,description='Infrared filter style approximation; visible RGB only' if spec.get('infrared_style') else 'Community display interpretation' if 'cube' in spec else 'Official-informed style approximation')
  stocks.append(dict(stock,values=raw.ravel().tolist()))
  target=render(spec['id'],hold);actual=sample_tetrahedral(raw.reshape(15,15,15,3)/255,hold)
  delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(target)),colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual)),method='CIE 2000')
  error=dict(samples=8192,seed=299305,delta_e00_median=float(np.median(delta)),delta_e00_p95=float(np.quantile(delta,.95)),delta_e00_max=float(np.max(delta)),max_code_error=float(np.max(np.abs(target-actual))*255))
  reports.append(dict(stock,table_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),interpolation=error));print(spec['id'],error,flush=True)
 for table in tables:
  if not np.all(table==table[:,0,None]):raise ValueError('D76 target is not neutral')
 for bank,part in enumerate([tables[:4],tables[4:]]):
  text='/* Generated D76 display targets; see d76-reference.json. */\nstatic const uint8_t m10v_d76_luts_%d[%d][3375]={\n'%(bank,len(part))
  text+=''.join('{\n'+''.join('%d,\n'%int(v[0]) for v in table)+'},\n' for table in part)+'};\n'
  (ROOT/f'native/gr3/film_d76_{bank}_data.h').write_text(text)
  (ROOT/f'native/gr3/film_d76_{bank}.c').write_text('#include <stdint.h>\n#include "film_d76_%d_data.h"\nconst uint8_t *m10v_d76_%d_table(uint32_t v){return v<%d?&m10v_d76_luts_%d[v][0]:0;}\n'%(bank,bank,len(part),bank))
 (ROOT/'web/gr3/d76-luts.json').write_text(json.dumps(dict(size=15,bits=8,order='RGB, blue fastest',stocks=stocks),separators=(',',':'))+'\n')
 files=['scripts/build_gr3_d76_reference.py','scripts/build_gr3_curated_reference.py','scripts/build_gr3_harman_reference.py']+[str(p.relative_to(ROOT)) for p in sorted(ASSETS.iterdir()) if p.is_file()]
 ref=dict(schema='m10v-d76-reference/v1',community_revision=REVISION,parameters=PARAMETERS,stocks=reports,camera_calibrated=False,film_calibrated=False,official_lut=False,files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},limits='Errors measure LUT implementation against its declared display target, NOT accuracy against real film. No 100 percent physical-replication claim.')
 ref['native_storage']=dict(channels=1,entries_per_stock=3375,bytes_per_stock=3375,expanded_rgb_bytes_per_stock=10125,lossless_neutral_rgb=True)
 previous=ROOT/'native/gr3/d76-reference.json'
 if previous.exists():
  old=json.loads(previous.read_text())
  for key in ('native_profiles_full','native_profiles'):
   if key in old:ref[key]=old[key]
 (ROOT/'native/gr3/d76-reference.json').write_text(json.dumps(ref,indent=2)+'\n')

if __name__=='__main__':generate()
