"""Production verification uses only the Python standard library."""
import hashlib,json,re
from pathlib import Path
def verify(root):
 root=Path(root);ref=json.loads((root/'native/gr3/d76-reference.json').read_text());web=json.loads((root/'web/gr3/d76-luts.json').read_text())
 if (web['size'],web['bits'],web['order'])!=(15,8,'RGB, blue fastest') or [s['id'] for s in web['stocks']]!=list(range(299,306)):raise ValueError('D76 inventory differs')
 for p,h in ref['files'].items():
  if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('D76 source changed: '+p)
 raw=b''.join(b''.join(bytes(map(int,v)) for v in re.findall(r'\{(\d+),(\d+),(\d+)\}',(root/f'native/gr3/film_d76_{bank}_data.h').read_text())) for bank in range(2))
 if len(raw)!=7*10125:raise ValueError('D76 native extent differs')
 payloads=[]
 for i,(spec,stock) in enumerate(zip(ref['stocks'],web['stocks'])):
  if spec['id']!=299+i or len(stock['values'])!=10125 or any(type(v)is not int or not 0<=v<=255 for v in stock['values']):raise ValueError('D76 table bounds differ')
  p=bytes(stock['values'])
  if raw[i*10125:(i+1)*10125]!=p or hashlib.sha256(p).hexdigest()!=spec['table_sha256']:raise ValueError('D76 table readback differs')
  if stock['camera_calibrated'] or stock['film_calibrated'] or stock['official_lut'] or not stock['approximation']:raise ValueError('D76 calibration claim invalid')
  if any(p[j]!=p[j+1] or p[j]!=p[j+2] for j in range(0,len(p),3)):raise ValueError('D76 chroma differs')
  payloads.append(p)
 if len(set(payloads))!=7:raise ValueError('D76 stocks aliased')
 if 'native_profiles_full' in ref:
  from scripts.fit_gr3_d76_native import native_header
  if (root/'native/gr3/m10v_d76_native_profiles.h').read_text()!=native_header(ref):raise ValueError('D76 preview header differs')
 return payloads
if __name__=='__main__':print('Verified',len(verify(Path(__file__).resolve().parents[1])),'D76 LUTs')
