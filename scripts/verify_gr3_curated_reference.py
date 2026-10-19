"""Dependency-free verification of curated C/web tables and source provenance."""
import hashlib,json,re
from pathlib import Path
def verify(root):
 root=Path(root)
 ref=json.loads((root/'native/gr3/curated-reference.json').read_text())
 web=json.loads((root/'web/gr3/curated-luts.json').read_text())
 if ref['schema']!='m10v-curated-reference/v1' or any(ref[k] is not False for k in ['camera_calibrated','film_calibrated','official_lut']):raise ValueError('unsupported curated reference')
 for path,digest in ref['files'].items():
  if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:raise ValueError('curated source hash differs: '+path)
 if (web['size'],web['bits'],web['order'])!=(15,8,'RGB, blue fastest'):raise ValueError('curated table format')
 text=(root/'native/gr3/film_curated_data.h').read_text()
 payloads=[bytes(map(int,v)) for v in re.findall(r'\{(\d+),(\d+),(\d+)\}',text)]
 flat=b''.join(payloads)
 if len(flat)!=4*10125 or len(web['stocks'])!=4 or len(ref['stocks'])!=4:raise ValueError('curated inventory')
 out=[]
 for i in range(4):
  w=web['stocks'][i];s=ref['stocks'][i]
  if w['id']!=69+i or s['id']!=w['id'] or s['name']!=w['name']:raise ValueError('curated identity')
  if len(w['values'])!=10125 or any(type(v) is not int or not 0<=v<=255 for v in w['values']):raise ValueError('curated bounds')
  b=bytes(w['values'])
  if b!=flat[i*10125:(i+1)*10125] or hashlib.sha256(b).hexdigest()!=s['table_sha256']:raise ValueError('curated C/web mismatch')
  out.append(b)
 return out
if __name__=='__main__':print('Verified curated LUT bytes:',list(map(len,verify(Path(__file__).resolve().parents[1]))))
