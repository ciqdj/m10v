"""Verify the complete spectral stock identity, provenance and C/web payloads."""
import hashlib,json,re
from pathlib import Path
def verify(root):
 root=Path(root);ref=json.loads((root/'native/gr3/spectral-reference.json').read_text());web=json.loads((root/'web/gr3/spectral-luts.json').read_text())
 if [s['id'] for s in web['stocks']]!=[77,298] or (web['size'],web['bits'],web['order'])!=(15,8,'RGB, blue fastest'):raise ValueError('spectral identities differ')
 for path,sha in ref['files'].items():
  if hashlib.sha256((root/path).read_bytes()).hexdigest()!=sha:raise ValueError('spectral source changed: '+path)
 extra=b''.join(bytes(map(int,v)) for v in re.findall(r'\{(\d+),(\d+),(\d+)\}',(root/'native/gr3/film_spectral_data.h').read_text()))
 current=json.loads((root/'web/gr3/newstocks-luts.json').read_text())
 payloads=[bytes(next(s for s in current['stocks'] if s['id']==77)['values']),extra]
 for stock,report,payload in zip(web['stocks'],ref['stocks'],payloads):
  if len(payload)!=10125 or bytes(stock['values'])!=payload or hashlib.sha256(payload).hexdigest()!=report['table_sha256']:raise ValueError('spectral C/web payload mismatch')
 if [s['symbol'] for s in ref['stocks']]!=['KODAK_AEROCOLOR','KODAK_5213'] or ref['parameters']['color_masking']['77']!=0:raise ValueError('wrong spectral stock or colour masking')
 if ref['parameters']['camera_calibrated'] or ref['parameters']['film_calibrated']:raise ValueError('invalid spectral calibration claim')
 from scripts.fit_gr3_spectral_native import native_header
 if (root/'native/gr3/m10v_spectral_native_profiles.h').read_text()!=native_header(ref):raise ValueError('stale spectral preview profiles')
 return payloads
if __name__=='__main__':print('Verified',len(verify(Path(__file__).resolve().parents[1])),'spectral LUTs')
