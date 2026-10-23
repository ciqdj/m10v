"""Seven traceable display-sRGB interpretations; never camera/film calibration."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_gr3_curated_reference import cube
from scripts.build_gr3_harman_reference import sample_tetrahedral
ASSETS=ROOT/'third_party/style-filter-luts'
STOCKS=[
 {'id':291,'key':'leica-monochrome','name':'Leica Monochrome','ascii_name':'Leica Monochrome','reference':'Street Monochrome Eerie community LUT, neutralised; Leica-inspired tonal interpretation, no sensor response emulation','cube':'Street Monochrome Eerie.cube','official':'https://leica-camera.com/en-US/photography/cameras/m/m11-monochrom','title':'LEICA','code':'MONO','color':'#71767a'},
 {'id':292,'key':'lomography','name':'Lomography','ascii_name':'Lomography','reference':'independent Color Negative 400-inspired interpretation; no verified same-stock LUT found; X-Pro 200 and Redscale are NOT substituted','official':'https://www.lomography.com/magazine/244515-lomopedia-lomography-color-negative-400-iso-35mm','title':'LOMO','code':'400','color':'#df624b'},
 {'id':293,'key':'polaroid','name':'Polaroid','ascii_name':'Polaroid','reference':'community Impossible/Polaroid PX-680 LUT as an explicit 600-compatible instant-colour proxy, NOT a measured modern 600 or i-Type transform','cube':'polaroid_px-680.cube','official':'https://www.polaroid.com/en_us/products/color-itype-instant-film','title':'POLAR','code':'600','color':'#d5bd9b'},
 {'id':294,'key':'fujifilm-velvia-50','name':'Fujifilm Velvia 50','ascii_name':'Fujifilm Velvia 50','reference':'same-name community Fuji Velvia 50 cube; RVP50 official curves are qualitative checks, not measured GR conversion','cube':'fuji_velvia_50.cube','official':'https://asset.fujifilm.com/master/emea/files/2020-10/a71dda63e2662f012b3b74110794918a/films_velvia-50_datasheet_01.pdf','title':'VELV','code':'50','color':'#74983c'},
 {'id':295,'key':'cyberpunk','name':'Cyberpunk','ascii_name':'Cyberpunk','reference':'independent cyan-shadow/magenta-neon artistic LUT; no canonical film or licensed reference transform','title':'CYBER','code':'NEON','color':'#9b4ad2'},
 {'id':296,'key':'cyanotype','name':'Cyanotype','ascii_name':'Cyanotype','reference':'independent Prussian-blue to paper-white positive print interpretation; no scanned print calibration or negative correction LUT','official':'https://www.jacquardproducts.com/cyanotype','title':'CYANO','code':'BLUE','color':'#275a91'},
 {'id':297,'key':'german-cool','name':'德系冷调','ascii_name':'German Cool','reference':'independent restrained cool-grey artistic look with skin gate; no unique German manufacturer standard','title':'COOL','code':'DE','color':'#6b8792'},
]
PARAMETERS={
 'domain':'encoded display sRGB D65 after ISP, not log or scene-linear input',
 'status':'all authored numerical parameters are design assumptions; no physical calibration',
 'lomography':{'luma_weights':[.2126,.7152,.0722],'tone_in':[0,.08,.25,.5,.75,.92,1],'tone_out':[0,.055,.23,.52,.80,.95,1],'saturation':1.18,'midtone_warm_rgb':[.022,.004,-.019]},
 'cyberpunk':{'tone_in':[0,.08,.25,.5,.75,1],'tone_out':[0,.035,.19,.49,.80,1],'saturation':1.16,'shadow_rgb':[-.035,.018,.055],'highlight_rgb':[.04,-.025,.03],'green_to_cyan':.22,'red_to_magenta':.16},
 'cyanotype':{'luma_weights':[.2126,.7152,.0722],'tone_in':[0,.1,.25,.5,.75,.9,1],'tone_out':[0,.025,.14,.46,.80,.95,1],'ink_rgb':[.025,.09,.22],'paper_rgb':[.98,.975,.96]},
 'german_cool':{'tone_in':[0,.08,.25,.5,.75,.92,1],'tone_out':[0,.045,.22,.50,.77,.94,1],'saturation':.82,'shadow_rgb':[-.016,.003,.024],'skin_gate':'red>green>blue, red-green 0.02..0.14; reduces cold tint and restores saturation'},
 'leica':'neutralise community output using Rec.709 encoded RGB weights; cannot emulate monochrome sensor detail, spectral response or dynamic range',
 'polaroid':'PX-680 is an explicit historical proxy; no Polachrome, 669 peel-apart, expired-film LUT or added white border',
 'textures':'off by default; LUT alone cannot add grain, bloom, vignetting or print texture',
}

def render(film,rgb):
 x=np.clip(np.asarray(rgb,float),0,1);spec=next(s for s in STOCKS if s['id']==film)
 if 'cube' in spec:
  out=sample_tetrahedral(cube(ASSETS/spec['cube']),x)
  return np.repeat((out@np.array([.2126,.7152,.0722]))[:,None],3,axis=1) if film==291 else out
 l=x@np.array([.2126,.7152,.0722]);l3=l[:,None]
 if film==292:
  p=PARAMETERS['lomography'];t=np.interp(l,p['tone_in'],p['tone_out'])[:,None]
  return np.clip(t+(x-l3)*p['saturation']+(4*l*(1-l))[:,None]*p['midtone_warm_rgb'],0,1)
 if film==295:
  p=PARAMETERS['cyberpunk'];t=np.interp(l,p['tone_in'],p['tone_out'])[:,None];out=t+(x-l3)*p['saturation']
  green=np.maximum(x[:,1]-np.maximum(x[:,0],x[:,2]),0);red=np.maximum(x[:,0]-np.maximum(x[:,1],x[:,2]),0)
  out[:,2]+=green*p['green_to_cyan']+red*p['red_to_magenta']
  out+=(4*l*(1-l))[:,None]*((1-l3)*p['shadow_rgb']+l3*p['highlight_rgb'])
  return np.clip(out,0,1)
 if film==296:
  p=PARAMETERS['cyanotype'];t=np.interp(l,p['tone_in'],p['tone_out'])[:,None]
  return np.array(p['ink_rgb'])+(np.array(p['paper_rgb'])-p['ink_rgb'])*t
 if film==297:
  p=PARAMETERS['german_cool'];skin=(x[:,0]>x[:,1])*(x[:,1]>x[:,2])*np.clip((x[:,0]-x[:,1]-.02)/.12,0,1)
  sat=p['saturation']+(1-p['saturation'])*skin;t=np.interp(l,p['tone_in'],p['tone_out'])[:,None]
  return np.clip(t+(x-l3)*sat[:,None]+(4*l*(1-l)*(1-.85*skin))[:,None]*p['shadow_rgb'],0,1)
 raise ValueError('unknown style filter')

def generate():
 import colour
 axis=np.linspace(0,1,15);grid=np.stack(np.meshgrid(axis,axis,axis,indexing='ij'),-1).reshape(-1,3)
 hold=np.random.default_rng(290296).uniform(0,1,(8192,3));tables=[];stocks=[];reports=[]
 for spec in STOCKS:
  raw=np.rint(render(spec['id'],grid)*255).astype(np.uint8);tables.append(raw)
  stocks.append(dict(spec,grain=0,grain_size=0,camera_calibrated=False,film_calibrated=False,official_lut=False,approximation=True,values=raw.ravel().tolist()))
  expected=render(spec['id'],hold);actual=sample_tetrahedral(raw.reshape(15,15,15,3)/255,hold)
  delta=colour.delta_E(colour.XYZ_to_Lab(colour.sRGB_to_XYZ(expected)),colour.XYZ_to_Lab(colour.sRGB_to_XYZ(actual)),method='CIE 2000')
  reports.append(dict(spec,table_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),table_bytes=raw.size,interpolation={'samples':8192,'seed':290296,'delta_e00_median':float(np.median(delta)),'delta_e00_p95':float(np.quantile(delta,.95))}))
 for bank,part in enumerate([tables[:4],tables[4:]]):
  header='/* Generated by build_gr3_style_filters_reference.py; see style-filters-reference.json. */\nstatic const uint8_t m10v_style_filters_luts_%d[%d][3375][3]={\n'%(bank,len(part))
  header+=''.join('{\n'+''.join('{%d,%d,%d},\n'%tuple(v) for v in table)+'},\n' for table in part)+'};\n'
  (ROOT/f'native/gr3/film_style_filters_{bank}_data.h').write_text(header)
 (ROOT/'web/gr3/style-filters-luts.json').write_text(json.dumps({'size':15,'bits':8,'order':'RGB, blue fastest','stocks':stocks},ensure_ascii=False,separators=(',',':'))+'\n')
 paths=['scripts/build_gr3_style_filters_reference.py','scripts/build_gr3_curated_reference.py','scripts/build_gr3_harman_reference.py']+[str(p.relative_to(ROOT)) for p in sorted(ASSETS.iterdir()) if p.is_file()]
 result={'schema':'m10v-style-filters-reference/v1','camera_calibrated':False,'film_calibrated':False,'official_lut':False,'parameters':PARAMETERS,'stocks':reports,'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},'limits':'Errors compare implementation to its designed display target only. Real camera/film error unknown. No claim of 100 percent replication.'}
 (ROOT/'native/gr3/style-filters-reference.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{k:v for k,v in r.items() if k in ['id','interpolation']} for r in reports],indent=2))
if __name__=='__main__':generate()
