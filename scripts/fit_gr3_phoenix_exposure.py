"""Fit the assumed Phoenix EI120 display target to extracted native gamma.

This measures implementation error against an assumed target, never real film.
"""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.fit_gr3_native_film_targets import fit,quantize,render_quantized
from scripts.analyze_gr3_film_color_targets import metrics
from scripts.build_gr3_harman_reference import sample_tetrahedral

def generate():
    web=json.loads((ROOT/'web/gr3/harman-luts.json').read_text())
    stock=next(s for s in web['stocks'] if s['id']==67 and s['ei']==120)
    table=np.array(stock['values']).reshape(15,15,15,3)/255
    base=np.array(json.loads((ROOT/'native/gr3/native-film-fit-targets.json').read_text())['base_gamma_q14'])/16384
    train=np.random.default_rng(67120).uniform(0,1,(4096,3))
    grey=np.repeat(np.linspace(0,1,256)[:,None],3,axis=1)
    train=np.vstack([train,grey,grey,grey]);hold=np.random.default_rng(12067).uniform(0,1,(8192,3))
    params,opt=fit(train,sample_tetrahedral(table,train),base,iterations=600)
    q=quantize(params)
    for key in ('hue_q10','native_cca_signed12'):
        if np.min(q[key])<-2048 or np.max(q[key])>2047:raise ValueError(key+' overflow')
    if np.min(q['native_csp_signed9'])<-256 or np.max(q['native_csp_signed9'])>255:raise ValueError('CSP overflow')
    score=metrics(sample_tetrahedral(table,hold),render_quantized(q,hold,base))
    result={'schema':'m10v-phoenix-exposure-native/v1','film_id':67,'ei':120,
      'camera_calibrated':False,'film_calibrated':False,'official_lut':False,
      'parameters':q,'holdout':score,'optimization':opt,
      'files':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
        'scripts/fit_gr3_phoenix_exposure.py','web/gr3/harman-luts.json',
        'scripts/fit_gr3_native_film_targets.py','native/gr3/native-film-fit-targets.json']}}
    (ROOT/'native/gr3/phoenix-exposure-native.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(score,indent=2),flush=True)
if __name__=='__main__':generate()
