"""Fit curated LUTs to the extracted Standard gamma model; no camera calibration.
Run after build_gr3_curated_reference.py, before native profile generation.
"""
import sys,json,hashlib
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from scripts.fit_gr3_native_film_targets import fit,quantize,render_quantized
from scripts.analyze_gr3_film_color_targets import metrics
from scripts.build_gr3_harman_reference import sample_tetrahedral
manifest=json.loads((root/'native/gr3/curated-reference.json').read_text());web=json.loads((root/'web/gr3/curated-luts.json').read_text())
base=np.array(json.loads((root/'native/gr3/native-film-fit-targets.json').read_text())['base_gamma_q14'])/16384
rng=np.random.default_rng(697071);train=rng.uniform(0,1,(4096,3));grey=np.repeat(np.linspace(0,1,256)[:,None],3,axis=1);train=np.vstack([train,grey,grey,grey]);hold=np.random.default_rng(716970).uniform(0,1,(8192,3))
profiles=[]
for stock in web['stocks']:
 table=np.array(stock['values']).reshape(15,15,15,3)/255
 params,opt=fit(train,sample_tetrahedral(table,train),base,iterations=600);q=quantize(params)
 score=metrics(sample_tetrahedral(table,hold),render_quantized(q,hold,base));q['film_id']=stock['id'];q['holdout']=score;q['optimization']=opt
 for key,lo,hi in [('hue_q10',-2048,2047),('native_cca_signed12',-2048,2047),('native_csp_signed9',-256,255)]:
  if np.min(q[key])<lo or np.max(q[key])>hi:raise ValueError(key+' overflow')
 profiles.append(q);print(stock['id'],score,flush=True)
manifest['native_profiles_full']=profiles;manifest['native_profile_domain']='extracted Standard gamma inverse model, relative matrices, 12-sector hue; camera calibration unverified'
for path in ['scripts/fit_gr3_curated_native.py','scripts/fit_gr3_native_film_targets.py','native/gr3/native-film-fit-targets.json']:
 manifest['files'][path]=hashlib.sha256((root/path).read_bytes()).hexdigest()
manifest['native_fit_generator']={'path':'scripts/fit_gr3_curated_native.py','sha256':hashlib.sha256((root/'scripts/fit_gr3_curated_native.py').read_bytes()).hexdigest()}
(root/'native/gr3/curated-reference.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
