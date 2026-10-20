import hashlib,json,re
from pathlib import Path
def verify(root):
 root=Path(root);report=json.loads((root/'native/gr3/newstocks-reference.json').read_text());web=json.loads((root/'web/gr3/newstocks-luts.json').read_text());tables=[]
 for p,h in report['files'].items():
  if hashlib.sha256((root/p).read_bytes()).hexdigest()!=h:raise ValueError('new stock source changed: '+p)
 if [s['id'] for s in web['stocks']]!=list(range(73,79)):raise ValueError('new stock IDs differ')
 raw=b''.join(bytes(map(int,v)) for v in re.findall(r'\{(\d+),(\d+),(\d+)\}',(root/'native/gr3/film_newstocks_data.h').read_text()))
 for i,(s,m) in enumerate(zip(web['stocks'],report['stocks'])):
  t=bytes(s['values'])
  if len(t)!=10125 or raw[i*10125:(i+1)*10125]!=t or hashlib.sha256(t).hexdigest()!=m['table_sha256']:raise ValueError('new stock table mismatch')
  tables.append(t)
 if len(raw)!=60750 or len(tables)!=6 or not report['stocks'][3]['approximation']:raise ValueError('new stock inventory mismatch')
 return tables
if __name__=='__main__':verify(Path(__file__).resolve().parents[1])
