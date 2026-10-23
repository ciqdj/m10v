"""Fit live-preview surrogates; still JPEGs retain the full spectral LUT."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def native_header(manifest):
 arr=lambda x:'{'+','.join(map(str,x))+'}'
 frames=[];hues=[]
 for q in manifest['native_profiles_full']:
  frames.append('{'+arr([v for row in q['matrix_q13'] for v in row])+','+arr([v for row in q['post_q9'] for v in row])+',{'+','.join(arr(c) for c in q['curves'])+'}}')
  hues.append(arr([v for sector in q['hue_q10'] for row in sector for v in row]))
 return '/* Generated from spectral-reference.json; live approximation, never still completion. */\nstatic const m10v_isp_frame_target native_spectral_frame[2]={'+','.join(frames)+'};\nstatic const int16_t native_spectral_hue[2][108]={'+','.join(hues)+'};\n'

def generate():
 import numpy as np
 from scripts.fit_gr3_native_film_targets import fit,quantize,render_quantized
 from scripts.analyze_gr3_film_color_targets import metrics
 from scripts.build_gr3_harman_reference import sample_tetrahedral
 manifest=json.loads((ROOT/'native/gr3/spectral-reference.json').read_text());web=json.loads((ROOT/'web/gr3/spectral-luts.json').read_text())
 base=np.array(json.loads((ROOT/'native/gr3/native-film-fit-targets.json').read_text())['base_gamma_q14'])/16384
 train=np.random.default_rng(77298).uniform(0,1,(4096,3));grey=np.repeat(np.linspace(0,1,256)[:,None],3,axis=1)
 train=np.vstack([train,grey,grey,grey]);hold=np.random.default_rng(29877).uniform(0,1,(8192,3));profiles=[]
 for stock in web['stocks']:
  table=np.array(stock['values']).reshape(15,15,15,3)/255
  params,opt=fit(train,sample_tetrahedral(table,train),base,iterations=600);q=quantize(params)
  for key,lo,hi in [('hue_q10',-2048,2047),('native_cca_signed12',-2048,2047),('native_csp_signed9',-256,255)]:
   if np.min(q[key])<lo or np.max(q[key])>hi:raise ValueError(key+' overflow')
  score=metrics(sample_tetrahedral(table,hold),render_quantized(q,hold,base))
  q.update(film_id=stock['id'],holdout=score,optimization=opt,role='live-preview approximation only; exact still LUT is mandatory')
  profiles.append(q);print(stock['id'],score,flush=True)
 manifest['native_profiles_full']=profiles
 for path in ['scripts/fit_gr3_spectral_native.py','scripts/fit_gr3_native_film_targets.py','native/gr3/native-film-fit-targets.json']:
  manifest['files'][path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
 (ROOT/'native/gr3/spectral-reference.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (ROOT/'native/gr3/m10v_spectral_native_profiles.h').write_text(native_header(manifest))

if __name__=='__main__':
 if '--write-header' in sys.argv:
  manifest=json.loads((ROOT/'native/gr3/spectral-reference.json').read_text())
  manifest['files']['scripts/fit_gr3_spectral_native.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
  (ROOT/'native/gr3/spectral-reference.json').write_text(json.dumps(manifest,indent=2)+'\n')
  (ROOT/'native/gr3/m10v_spectral_native_profiles.h').write_text(native_header(manifest))
 else:generate()
