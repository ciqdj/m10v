"""Verify source provenance, output inventory and complete C/web LUT equality."""
import hashlib,json,re
from pathlib import Path

def verify(root):
 root=Path(root);ref=json.loads((root/'native/gr3/style-filters-reference.json').read_text());web=json.loads((root/'web/gr3/style-filters-luts.json').read_text())
 if [s['id'] for s in web['stocks']]!=list(range(291,298)) or (web['size'],web['bits'],web['order'])!=(15,8,'RGB, blue fastest'):raise ValueError('style inventory differs')
 for path,sha in ref['files'].items():
  if hashlib.sha256((root/path).read_bytes()).hexdigest()!=sha:raise ValueError('style source changed: '+path)
 raw=b''.join(b''.join(bytes(map(int,v)) for v in re.findall(r'\{(\d+),(\d+),(\d+)\}',(root/f'native/gr3/film_style_filters_{bank}_data.h').read_text())) for bank in range(2))
 if len(raw)!=7*10125:raise ValueError('style native extent differs')
 payloads=[]
 for i,(spec,stock) in enumerate(zip(ref['stocks'],web['stocks'])):
  if spec['id']!=291+i or len(stock['values'])!=10125 or any(type(v)is not int or not 0<=v<=255 for v in stock['values']):raise ValueError('style table bounds differ')
  payload=bytes(stock['values'])
  if raw[i*10125:(i+1)*10125]!=payload or hashlib.sha256(payload).hexdigest()!=spec['table_sha256']:raise ValueError('style table readback differs')
  payloads.append(payload)
 if ref['camera_calibrated'] or ref['film_calibrated'] or ref['official_lut']:raise ValueError('style calibration claim invalid')
 return payloads
if __name__=='__main__':
 print('Verified',len(verify(Path(__file__).resolve().parents[1])),'style LUTs')
