"""Independent build-time reference source and payload validation (stdlib only)."""
import hashlib
import json
from pathlib import Path
import re


def verify(root: Path) -> bytes:
    manifest=json.loads((root/'native/gr3/5207-reference.json').read_text())
    if manifest.get('table_size')!=15 or manifest.get('table_bits')!=8 or manifest.get('camera_calibrated') is not False or manifest.get('film_calibrated') is not False:
        raise ValueError('unsupported 5207 reference contract')
    for name,digest in manifest['sources'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not (name.startswith('third_party/spectral-film-lut/') or name=='scripts/build_gr3_5207_reference.py'):
            raise ValueError('5207 source path outside model')
        if hashlib.sha256((root/p).read_bytes()).hexdigest()!=digest:
            raise ValueError('5207 model source digest differs: '+name)
    web=json.loads((root/'web/gr3/5207-lut.json').read_text())
    if web.get('size')!=15 or web.get('bits')!=8:
        raise ValueError('5207 web table shape differs')
    values=web['values']
    if len(values)!=10125 or any(type(v) is not int or not 0<=v<=255 for v in values):
        raise ValueError('5207 table bounds differ')
    payload=bytes(values)
    header=(root/'native/gr3/film_5207_data.h').read_text()
    triples=re.findall(r'\{(\d+),(\d+),(\d+)\},',header)
    if len(triples)!=3375 or bytes(int(v) for triple in triples for v in triple)!=payload:
        raise ValueError('5207 C and web table payloads differ')
    if len(payload)!=manifest['table_bytes'] or hashlib.sha256(payload).hexdigest()!=manifest['table_sha256']:
        raise ValueError('5207 reference table digest differs')
    return payload
