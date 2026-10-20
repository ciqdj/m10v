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
  'reference':'Canon IXUS 70 / SD1000 daylight colour-inspired interpretation; not a measured camera transform',
  'official':'https://www.usa.canon.com/support/p/powershot-sd1000'},
]
PARAMETERS={
 'input':'encoded display sRGB D65 after ISP; no recovery of scene exposure',
 'output':'encoded display sRGB D65',
 'fuji_proxy_strength':.8,
 'ccd':{'target':'Canon DIGITAL IXUS 70 / PowerShot SD1000 (2007)',
        'model':'offline OKLab lightness and periodic OKLCh selective colour',
        'hue_degrees':[25,55,95,145,195,265,330],
        'hue_rotation_degrees':[3,1,-1,-1.5,5.5,0,-1],
        'chroma_gain':[1.09,1.02,1.025,1.04,1.045,1.04,1.01],
        'lightness_input':[0,.12,.30,.50,.75,.90,1],
        'lightness_output':[0,.115,.29,.505,.755,.89,1],
        'neutral_chroma_gate':[.015,.06],
        'highlight_chroma_gate':[.85,1.],
        'gamut_knee':.98,
        'parameter_status':'all numerical values are design assumptions, not camera measurements'},
 'lucky':{'contrast':.18,'shoulder':.025,'red_chroma':.13,'blue_chroma':.09,
          'green_shadow':.014,'magenta_highlight':.012},
 'status':'all adaptation strengths are design assumptions, not manufacturer measurements',
}
SOURCES=[
 {'url':'https://www.usa.canon.com/support/p/powershot-sd1000','use':'official IXUS 70 / SD1000 model and manual reference; no camera LUT copied'},
 {'url':'https://www.imaging-resource.com/cameras/canon-sd1000-review/','use':'original-camera test qualitative direction: stronger red, slightly stronger blue/green, cyan toward blue, some reds toward orange, warm skin; no measured coefficients copied'},
 {'url':'https://downloads.canon.com/cpr/software/camera/FULL_LINE_0113W698.pdf','use':'official My Colors selective-colour mode documentation; no manufacturer transform available'},
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

# Published OKLab transform; inverse matrices are computed from the exact forward
# constants so round trips do not accumulate independently rounded inverse errors.
_OKLAB_M1=np.array([[.4122214708,.5363325363,.0514459929],
 [.2119034982,.6806995451,.1073969566],[.0883024619,.2817188376,.6299787005]])
_OKLAB_M2=np.array([[.2104542553,.793617785,-.0040720468],
 [1.9779984951,-2.428592205,.4505937099],[.0259040371,.7827717662,-.808675766]])
def _smooth_gate(x,low,high):
 t=np.clip((x-low)/(high-low),0,1)
 return t*t*(3-2*t)

def render_ccd(rgb):
 """Perceptual display look baked offline; never a raw camera profile or ISP inverse."""
 from scipy.interpolate import CubicSpline,PchipInterpolator
 p=PARAMETERS['ccd'];rgb=np.asarray(rgb,float)
 linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
 lab=np.cbrt(linear@_OKLAB_M1.T)@_OKLAB_M2.T
 light=lab[:,0];chroma=np.hypot(lab[:,1],lab[:,2]);hue=np.degrees(np.arctan2(lab[:,2],lab[:,1]))%360
 anchors=np.array(p['hue_degrees']);axis=np.r_[anchors,anchors[0]+360]
 angle=np.where(hue<anchors[0],hue+360,hue)
 gate=_smooth_gate(chroma,*p['neutral_chroma_gate'])
 high=1-_smooth_gate(light,*p['highlight_chroma_gate'])
 rotation=CubicSpline(axis,np.r_[p['hue_rotation_degrees'],p['hue_rotation_degrees'][0]],bc_type='periodic')(angle)
 gain=CubicSpline(axis,np.r_[p['chroma_gain'],p['chroma_gain'][0]],bc_type='periodic')(angle)
 hue=np.radians(hue+rotation*gate)
 chroma=chroma*(1+(gain-1)*gate*high)
 light=PchipInterpolator(p['lightness_input'],p['lightness_output'])(np.clip(light,0,1))
 direction=np.column_stack([np.cos(hue),np.sin(hue)])
 def to_linear(c):
  v=np.column_stack([light,direction*c[:,None]])@np.linalg.inv(_OKLAB_M2).T
  return (v**3)@np.linalg.inv(_OKLAB_M1).T
 # Find the display gamut boundary on each constant-L/h ray. An exponential
 # shoulder below that boundary retains hue and avoids hard RGB channel clipping.
 lo=np.zeros(len(rgb));hi=np.full(len(rgb),1.)
 for _ in range(24):
  mid=(lo+hi)/2;v=to_linear(mid)
  inside=np.all((v>=0)&(v<=1),axis=1);lo=np.where(inside,mid,lo);hi=np.where(inside,hi,mid)
 boundary=lo;knee=boundary*p['gamut_knee'];span=np.maximum(boundary-knee,1e-12)
 compressed=knee+span*(-np.expm1(-np.maximum(chroma-knee,0)/span))
 chroma=np.where(chroma>knee,compressed,chroma)
 linear=np.clip(to_linear(chroma),0,1)
 out=np.where(linear<=.0031308,12.92*linear,1.055*np.maximum(linear,0)**(1/2.4)-.055)
 # Exactly neutral source ramps stay neutral even at numerical gamut endpoints.
 neutral=np.ptp(rgb,axis=1)<1e-12
 grey=np.where(light<=np.cbrt(.0031308),12.92*light**3,1.055*light**(3/2.4)-.055)
 out[neutral]=grey[neutral,None]
 return np.clip(out,0,1)

def render(film,rgb):
 x=np.clip(np.asarray(rgb,float),0,1)
 if film in (69,70):
  file='kodak_portra_160.cube' if film==69 else 'fuji_superia_100.cube'
  y=sample_tetrahedral(cube(ROOT/'third_party/curated-film-luts'/file),x)
  return y if film==69 else x+PARAMETERS['fuji_proxy_strength']*(y-x)
 if film==72:return render_ccd(x)
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
