"""Reproducible display-sRGB interpretations; no measured camera/film claim.

Portra uses the modern community Portra 160 cube (not NC/VC). Fuji uses
Superia 100 as an explicitly labelled proxy, not industrial-film measurements.
Lucky uses a NEW C200 community-look interpretation, never old Super 200 data.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_gr3_harman_reference import sample_tetrahedral

STOCKS=[
 {'id':69,'key':'portra-160','name':'Portra 160','iso':160,'grain':1,'grain_size':0,
  'reference':'community Portra 160 display LUT; official E-4051 qualitative constraints',
  'official':'https://www.kodakprofessional.com/sites/default/files/2025-07/e4051.pdf'},
 {'id':70,'key':'fuji-industrial-100','name':'富士业务用 100','iso':100,'grain':1,'grain_size':0,
  'reference':'Superia 100 community LUT proxy at 80%; NOT measured Industrial 100',
  'official':'https://www.fujifilm.com.hk/products/consumer_film/color_negativefilms_35mm/100/index.html'},
 {'id':71,'key':'lucky-c200-new','name':'乐凯 C200','iso':200,'grain':2,'grain_size':1,
  'reference':'new C200 community-look interpretation; no downloaded Lucky LUT or official density curves available',
  'official':'https://www.lucky.cn/'},
 {'id':72,'key':'ccd-classic','name':'CCD Classic','iso':100,'grain':0,'grain_size':0,
  'reference':'GR DIGITAL low-ISO Standard/Vivid-inspired interpretation; no measured GR DIGITAL transform',
  'official':'https://www.ricoh-imaging.co.jp/english/r_dc/support/faq/bp/grd4/gr04404.html'},
]
PARAMETERS={
 'input':'encoded display sRGB D65 after ISP; no recovery of scene exposure',
 'output':'encoded display sRGB D65',
 'fuji_proxy_strength':.8,
 'ccd':{'contrast':.32,'saturation':1.065,'blue_gain':.055,'green_gain':.025,
        'red_gain':.015,'highlight_saturation_reduction':.18},
 'lucky':{'contrast':.18,'shoulder':.025,'red_chroma':.13,'blue_chroma':.09,
          'green_shadow':.014,'magenta_highlight':.012},
 'status':'all adaptation strengths are design assumptions, not manufacturer measurements',
}
SOURCES=[
 {'url':'https://github.com/YahiaAngelo/Film-Luts','use':'G MIC community cubes; attribution and MIT notice retained in third_party/curated-film-luts'},
 {'url':'https://www.rossandhisjpegs.com/lumix/lucky-color-200','use':'new Color 200 community LUT-based look direction only; Firebird/Daisy assets NOT copied; LUMIX controls not treated as GR3 equivalents'},
]
def cube(path):
 rows=[];size=None
 for line in path.read_text().splitlines():
  line=line.split('#',1)[0].strip()
  if not line:continue
  if line.startswith('LUT_3D_SIZE'):size=int(line.split()[1]);continue
  if line.startswith(('TITLE','DOMAIN_')):continue
  rows.append([float(v) for v in line.split()])
 a=np.asarray(rows)
 if size is None or a.shape!=(size**3,3) or not np.isfinite(a).all() or a.min()<0 or a.max()>1:raise ValueError('invalid community cube')
 # .cube red varies fastest; firmware blue varies fastest.
 return a.reshape(size,size,size,3).transpose(2,1,0,3)

def render(film,rgb):
 x=np.clip(np.asarray(rgb,float),0,1)
 if film in (69,70):
  file='kodak_portra_160.cube' if film==69 else 'fuji_superia_100.cube'
  y=sample_tetrahedral(cube(ROOT/'third_party/curated-film-luts'/file),x)
  return y if film==69 else x+PARAMETERS['fuji_proxy_strength']*(y-x)
 if film==72:
  # Neutral-preserving bounded contrast. Chroma-axis weights protect orange
  # skin tones and neutral highlights; no fake film base or spatial artifacts.
  p=PARAMETERS['ccd'];x=x+p['contrast']*x*(1-x)*(2*x-1)
  l=x@np.array([.2126,.7152,.0722]);chroma=x-l[:,None]
  spread=np.max(x,axis=1)-np.min(x,axis=1)
  blue=np.maximum(x[:,2]-np.maximum(x[:,0],x[:,1]),0)
  green=np.maximum(x[:,1]-np.maximum(x[:,0],x[:,2]),0)
  red=np.maximum(x[:,0]-np.maximum(x[:,1],x[:,2]),0)
  strength=p['saturation']+p['blue_gain']*blue+p['green_gain']*green+p['red_gain']*red
  strength-=p['highlight_saturation_reduction']*np.maximum((l-.75)/.25,0)**2*spread
  return np.clip(l[:,None]+chroma*strength[:,None],0,1)
 if film!=71:raise ValueError('unknown curated stock')
 p=PARAMETERS['lucky'];x=x+p['contrast']*x*(1-x)*(2*x-1)
 # Explicit, bounded community-inspired chromatic adjustments, not a spectral model.
 r=np.maximum(x[:,0]-x[:,1],0)*p['red_chroma']
 b=np.maximum(x[:,2]-x[:,0],0)*p['blue_chroma']
 x=x.copy();x[:,0]+=r*(1-x[:,0]);x[:,2]+=b*(1-x[:,2])
 l=x@np.array([.2126,.7152,.0722]);shadow=p['green_shadow']*(1-l)**2;high=p['magenta_highlight']*l**3
 x[:,1]+=shadow*(1-x[:,1]);x[:,1]*=1-high
 return np.clip(x-p['shoulder']*x**4,0,1)

def generate():
 from scripts.build_gr3_isp_film_targets import fit_target,summarize
 axis=np.linspace(0,1,15);grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),-1).reshape(-1,3)
 test=np.random.default_rng(697071).uniform(0,1,(8192,3))
 stocks=[];manifest=[];tables=[];profiles=[]
 for spec in STOCKS:
  values=np.rint(render(spec['id'],grid)*255).astype(np.uint8);tables.append(values)
  stocks.append(dict(spec,values=values.ravel().tolist()))
  approx=sample_tetrahedral(values.reshape(15,15,15,3)/255,test)
  import colour
  delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(render(spec['id'],test))),colour.XYZ_to_Lab(colour.sRGB_to_XYZ(approx)),method='CIE 2000')
  manifest.append(dict(spec,table_sha256=hashlib.sha256(values.tobytes()).hexdigest(),table_bytes=values.size,
    interpolation={'samples':len(test),'seed':697071,'delta_e00_p95':float(np.quantile(delta,.95))}))
  # Native matrices/curves are a bounded approximation of the same display LUT.
  # This surrogate input does NOT constitute measured GR3 ISP calibration.
  q=fit_target(grid,values/255,iterations=10)
  q['holdout']=summarize(q,test,approx);q['film_id']=spec['id'];profiles.append(q)
 header='/* Generated curated display LUTs. See curated-reference.json and third-party notices. */\nstatic const uint8_t m10v_curated_luts[4][3375][3]={\n'
 header+=''.join('{\n'+''.join('{%d,%d,%d},\n'%tuple(v) for v in t)+'},\n' for t in tables)+'};\n'
 (ROOT/'native/gr3/film_curated_data.h').write_text(header)
 (ROOT/'web/gr3/curated-luts.json').write_text(json.dumps({'size':15,'bits':8,'order':'RGB, blue fastest','stocks':stocks},ensure_ascii=False,separators=(',',':'))+'\n')
 source_paths=['scripts/build_gr3_curated_reference.py','scripts/build_gr3_isp_film_targets.py','scripts/build_gr3_harman_reference.py',
  'third_party/curated-film-luts/kodak_portra_160.cube','third_party/curated-film-luts/fuji_superia_100.cube','third_party/curated-film-luts/LICENSE']
 result={'schema':'m10v-curated-reference/v1','camera_calibrated':False,'film_calibrated':False,'official_lut':False,
  'parameters':PARAMETERS,'sources':SOURCES,'stocks':manifest,'native_profiles':profiles,
  'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}}
 (ROOT/'native/gr3/curated-reference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{'id':q['film_id'],'native_fit':q['holdout']} for q in profiles],indent=2))
if __name__=='__main__':generate()
