"""Standard-library-only verification for build/export machines."""
import hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def flat(value):
 if isinstance(value,list):
  for v in value:yield from flat(v)
 else:yield value
def verify_profile(q):
 for key,shape,lo,hi in [('matrix_q13',(3,3),-8192,16384),('post_q9',(3,3),-512,1024),('curves',(3,256),0,16383),('hue_q10',(12,3,3),-2048,2047),('native_cca_signed12',(3,3),-2048,2047),('native_csp_signed9',(3,3),-256,255)]:
  def dims(v,s):return isinstance(v,list) and len(v)==s[0] and (all(dims(x,s[1:]) for x in v) if len(s)>1 else True)
  if not dims(q[key],shape) or any(type(v)is not int or not lo<=v<=hi for v in flat(q[key])):raise ValueError('native coefficient bounds/shape: '+key)
 for curve in q['curves']:
  if any(a>b for a,b in zip(curve,curve[1:])):raise ValueError('nonmonotonic curve')
 if any(sum(row)!=1024 for sector in q['hue_q10'] for row in sector):raise ValueError('neutral hue row sum')
 if 'holdout' in q and any(not math.isfinite(v) for v in q['holdout'].values()):raise ValueError('nonfinite metrics')
def verify(root=ROOT):
 root=Path(root);ref=json.loads((root/'native/gr3/anime-e6-reference.json').read_text());web=json.loads((root/'web/gr3/anime-e6-luts.json').read_text())
 if (web['size'],web['bits'],web['order'])!=(15,8,'RGB, blue fastest'):raise ValueError('reference domain')
 if ref['camera_validated'] or ref['default_camera_renderer']!='quantized native ISP; no CPU color LUT':raise ValueError('unsupported camera claim')
 if [s['id'] for s in ref['stocks']]!=list(range(306,312)) or [s['id'] for s in web['stocks']]!=list(range(306,312)):raise ValueError('inventory')
 for p,h in ref['files'].items():
  if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('source changed: '+p)
 if ref['sources']!=json.loads((root/'third_party/anime-e6/sources.json').read_text()):raise ValueError('source manifest divergence')
 for source in ref['sources']:
  for pathkey,hashkey in [('path','sha256'),('license_path','license_sha256')]:
   if pathkey in source and hashlib.sha256((root/source[pathkey]).read_bytes()).hexdigest()!=source[hashkey]:raise ValueError('pinned source digest')
 payloads=[]
 for spec,stock in zip(ref['stocks'],web['stocks']):
  if len(stock['values'])!=10125 or any(type(v)is not int or not 0<=v<=255 for v in stock['values']):raise ValueError('table bounds')
  for entry in [spec,stock]:
   if entry['camera_calibrated'] or entry['film_calibrated'] or entry['official_lut'] or not entry['approximation']:raise ValueError('unsupported fidelity claim')
  p=bytes(stock['values'])
  if hashlib.sha256(p).hexdigest()!=spec['table_sha256']:raise ValueError('table digest')
  native=stock.get('native_values',[])
  if len(native)!=10125 or any(type(v)is not int or not 0<=v<=255 for v in native) or hashlib.sha256(bytes(native)).hexdigest()!=spec['native_preview_sha256']:raise ValueError('native preview digest/bounds')
  payloads.append(p)
 if len(set(payloads))!=6:raise ValueError('aliased target')
 if len(ref['native_profiles_full'])!=6:raise ValueError('native inventory')
 for film_id,q in zip(range(306,312),ref['native_profiles_full']):
  if q['film_id']!=film_id:raise ValueError('native identity')
  verify_profile(q)
 from scripts.fit_gr3_anime_e6_native import native_header
 if (root/'native/gr3/m10v_anime_e6_native_profiles.h').read_text()!=native_header(ref):raise ValueError('native header readback')
 return payloads
if __name__=='__main__':print('Verified',len(verify()),'anime/E6 native references')
