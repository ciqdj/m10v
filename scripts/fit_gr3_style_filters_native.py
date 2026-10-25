"""Fit each independent new-stock display LUT to the extracted native gamma model.
Errors are approximation-to-target, never measured camera/film accuracy.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.fit_gr3_native_film_targets import fit,quantize,render_quantized,KNOTS
from scripts.analyze_gr3_film_color_targets import metrics
from scripts.build_gr3_harman_reference import sample_tetrahedral
manifest=json.loads((ROOT/'native/gr3/style-filters-reference.json').read_text());web=json.loads((ROOT/'web/gr3/style-filters-luts.json').read_text())
base=np.array(json.loads((ROOT/'native/gr3/native-film-fit-targets.json').read_text())['base_gamma_q14'])/16384
train=np.random.default_rng(290296).uniform(0,1,(4096,3));grey=np.repeat(np.linspace(0,1,256)[:,None],3,axis=1);train=np.vstack([train,grey,grey,grey]);hold=np.random.default_rng(296290).uniform(0,1,(8192,3));profiles=[]
for stock in web['stocks']:
 table=np.array(stock['values']).reshape(15,15,15,3)/255;params,opt=fit(train,sample_tetrahedral(table,train),base,iterations=600);q=quantize(params)
 # The same post*curve transform has multiple factorizations. Reserve native
 # signed9 CSP headroom by scaling the post down and the curves up equally.
 # This is lossless in float, never coefficient clipping or weakened validation.
 csp=np.asarray(q['native_csp_signed9']);scale=min(1.,254./max(1,int(csp.max())),255./max(1,-int(csp.min())))
 if scale<1:
  if np.max(params[18:18+3*KNOTS])>scale:raise ValueError('post/curve refactor would clip')
  params=params.copy();params[9:18]*=scale;params[18:18+3*KNOTS]/=scale
  q=quantize(params);q['post_curve_rebalance']=float(scale)
 score=metrics(sample_tetrahedral(table,hold),render_quantized(q,hold,base));q.update(film_id=stock['id'],holdout=score,optimization=opt)
 for key,lo,hi in [('hue_q10',-2048,2047),('native_cca_signed12',-2048,2047),('native_csp_signed9',-256,255)]:
  if np.min(q[key])<lo or np.max(q[key])>hi:raise ValueError(key+' overflow')
 profiles.append(q);print(stock['id'],score,flush=True)
manifest['native_profiles_full']=profiles
for path in ['scripts/fit_gr3_style_filters_native.py','scripts/fit_gr3_native_film_targets.py','native/gr3/native-film-fit-targets.json']:manifest['files'][path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
(ROOT/'native/gr3/style-filters-reference.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
