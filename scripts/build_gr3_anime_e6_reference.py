"""Reproduce offline display references. No on-camera LUT or spectral claims.

Independent models are qualitative author interpretations. All numeric model
parameters are assumed, not digitized from manufacturer sensitometric curves.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
NAMES=['Makoto Shinkai','Ghibli','1970s','Fuji Provia 100F','Kodak Ektachrome E100','5294']
METADATA=[('SHINKAI','ANIME','#64a8db','makoto-shinkai'),('GHIBLI','ANIME','#7c9b69','ghibli'),('RETRO','1970s','#bd8d9b','retro-anime-1970s'),('PROVIA','100F','#378b70','fuji-provia-100f'),('EKTACHROME','E100','#cfab47','kodak-ektachrome-e100'),('EKTACHROME','5294','#b8954b','kodak-5294')]
def metadata(film_id):
 title,code,color,key=METADATA[film_id-306]
 return dict(title=title,code=code,color=color,key=key,ascii_name=NAMES[film_id-306])
# contrast cubic, saturation, channel mixing, black lift and white endpoint.
MODELS={306:dict(contrast=.20,saturation=1.16,mix=[[1,0,0],[-.015,1.025,-.01],[-.045,.01,1.035]],black=[.006,.012,.025],white=[1.,.995,1.]),
307:dict(contrast=-.12,saturation=.91,mix=[[1.015,.005,-.02],[.015,.99,-.005],[.02,.015,.965]],black=[.025,.024,.013],white=[.99,.985,.955]),
308:dict(contrast=.07,saturation=.78,mix=[[1.025,.005,-.03],[.02,.985,-.005],[.015,.025,.96]],black=[.045,.027,.018],white=[.97,.945,.90]),
310:dict(contrast=-.06,saturation=1.07,mix=[[1,0,0],[0,1,0],[0,0,1]],black=[.003,.003,.003],white=[.997,.997,.997]),
311:dict(contrast=.13,saturation=1.12,mix=[[1.012,-.006,-.006],[-.003,1.006,-.003],[-.008,.004,1.004]],black=[.002,.002,.002],white=[.995,.995,.995])}
def authored(rgb,parameters):
 import numpy as np
 p=parameters;x=np.asarray(rgb)@np.asarray(p['mix']).T
 y=x@np.array([.2126,.7152,.0722]);x=y[:,None]+p['saturation']*(x-y[:,None]);x=np.clip(x,0,1)
 x=x+p['contrast']*x*(1-x)*(2*x-1)
 return np.clip(np.array(p['black'])+x*(np.array(p['white'])-p['black']),0,1)
def cube(path):
 import numpy as np
 data=[];size=None
 for line in Path(path).read_text().splitlines():
  words=line.split()
  if not words or words[0].startswith('#'):continue
  if words[0]=='LUT_3D_SIZE':size=int(words[1])
  if len(words)==3:
   try:data.append(list(map(float,words)))
   except ValueError:pass
 if size is None or len(data)!=size**3:raise ValueError('cube extent differs')
 # .cube red changes fastest; internal RGB tables have blue fastest.
 return np.asarray(data).reshape(size,size,size,3).transpose(2,1,0,3)
def tables(root=ROOT):
 import numpy as np
 from scripts.build_gr3_harman_reference import sample_tetrahedral
 grid=np.stack(np.meshgrid(*[np.linspace(0,1,15)]*3,indexing='ij'),axis=-1).reshape(-1,3)
 out=[]
 for film_id,name in zip(range(306,312),NAMES):
  value=sample_tetrahedral(cube(Path(root)/'third_party/anime-e6/fuji_provia_100f.cube'),grid) if film_id==309 else authored(grid,MODELS[film_id])
  if not np.isfinite(value).all():raise ValueError('nonfinite output')
  out.append(dict(id=film_id,name=name,**metadata(film_id),values=np.rint(np.clip(value,0,1)*255).astype('uint8').reshape(-1).tolist(),approximation=True,official_lut=False,film_calibrated=False,camera_calibrated=False))
 return out
def generate(root=ROOT):
 root=Path(root);stocks=tables(root);sources=json.loads((root/'third_party/anime-e6/sources.json').read_text())
 specs=[]
 for stock in stocks:
  film_id=stock['id'];spec={k:v for k,v in stock.items() if k!='values'}
  spec.update(table_sha256=hashlib.sha256(bytes(stock['values'])).hexdigest(),source_kind='exact-name community LUT' if film_id==309 else 'independently authored qualitative approximation',model_parameters=MODELS.get(film_id),source_ids=['film-luts-provia','fuji-provia-official'] if film_id==309 else ['kodak-e100-official'] if film_id==310 else ['kodak-5294-official'] if film_id==311 else [],limitations='No calibrated physical-film or artwork match. Display RGB assumption; no scene/spectral reconstruction.')
  specs.append(spec)
 manifest=dict(schema='m10v-anime-e6-reference/v1',camera_validated=False,default_camera_renderer='quantized native ISP; no CPU color LUT',reference_domain='encoded display sRGB D65, normalized 0..1; output encoded sRGB',stocks=specs,sources=sources,files={},fitting='Run fit_gr3_anime_e6_native.py after reference generation; CPU LUTs offline/web only')
 (root/'web/gr3/anime-e6-luts.json').write_text(json.dumps(dict(size=15,bits=8,order='RGB, blue fastest',stocks=stocks),separators=(',',':'))+'\n')
 for name in ['scripts/build_gr3_anime_e6_reference.py','third_party/anime-e6/sources.json','third_party/anime-e6/Film-Luts-LICENSE','third_party/anime-e6/fuji_provia_100f.cube']:
  manifest['files'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
 (root/'native/gr3/anime-e6-reference.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':generate()
