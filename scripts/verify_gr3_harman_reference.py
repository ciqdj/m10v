"""Independent standard-library asset/provenance verifier; no model import."""
import ast
import hashlib
import json
from pathlib import Path
import re


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def verify(root):
    root=Path(root)
    try:
        manifest=json.loads((root/'native/gr3/harman-reference.json').read_text())
        web=json.loads((root/'web/gr3/harman-luts.json').read_text())
        header=(root/'native/gr3/film_harman_data.h').read_text()
        if manifest['schema']!='m10v-harman-reference/v1': raise ValueError('schema')
        for key in ['camera_calibrated','film_calibrated','spectral_calibrated','official_lut']:
            if manifest[key] is not False: raise ValueError('unsupported calibration claim')
        for key in ['parameters','sources']:
            if digest(canonical(manifest[key]))!=manifest[key+'_sha256']: raise ValueError(key+' hash')
        generator=manifest['generator']
        if generator['path']!='scripts/build_gr3_harman_reference.py': raise ValueError('generator path')
        source=(root/generator['path']).read_bytes()
        if digest(source)!=generator['sha256']: raise ValueError('generator hash')
        # Parse constants without executing or importing the model/dependencies.
        definitions={}
        for node in ast.parse(source).body:
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Name) and target.id in ('PARAMETERS','SOURCES','STOCKS'):
                        definitions[target.id]=ast.literal_eval(node.value)
        if canonical(definitions['PARAMETERS'])!=canonical(manifest['parameters']): raise ValueError('parameter/source definition mismatch')
        if canonical(definitions['SOURCES'])!=canonical(manifest['sources']): raise ValueError('provenance/source definition mismatch')
        if (web['size'],web['bits'],web['order'])!=(15,8,'RGB, blue fastest'): raise ValueError('web format')
        if (manifest['table_size'],manifest['table_bits'],manifest['order'])!=(15,8,'RGB, blue fastest'): raise ValueError('manifest format')
        if len(web['stocks'])!=5 or len(manifest['stocks'])!=5: raise ValueError('stock count')
        clean=re.sub(r'/\*.*?\*/','',header,flags=re.S)
        match=re.fullmatch(r'\s*static const uint8_t m10v_harman_luts\[5\]\[3375\]\[3\]\s*=\s*\{(.*)\};\s*',clean,re.S)
        if not match or re.search(r'[^\d,\s{}]',match.group(1)): raise ValueError('C format')
        # Validate every nested array dimension, not just the total number count.
        body=re.sub(r',\s*}', '}', '{'+match.group(1)+'}')
        arrays=json.loads(body.replace('{','[').replace('}',']'))
        if len(arrays)!=5 or any(len(t)!=3375 or any(len(v)!=3 for v in t) for t in arrays): raise ValueError('C dimensions')
        expected=[(67,200,'phoenix-ii'),(68,125,'red'),(68,64,'red'),(68,250,'red'),(67,120,'phoenix-ii')]
        results=[]
        for i,(stock,ref) in enumerate(zip(web['stocks'],manifest['stocks'])):
            if (stock['id'],stock['ei'],stock['model'])!=expected[i]: raise ValueError('stock identity')
            for key in ['id','ei','model','name']:
                if stock[key]!=ref[key]: raise ValueError('stock mismatch')
            vals=stock['values']
            if len(vals)!=10125 or any(type(v) is not int or not 0<=v<=255 for v in vals): raise ValueError('uint8 payload')
            cvals=[v for triple in arrays[i] for v in triple]
            if vals!=cvals: raise ValueError('C/web mismatch')
            payload=bytes(vals)
            if ref['table_bytes']!=len(payload) or ref['table_sha256']!=digest(payload): raise ValueError('payload hash')
            results.append(payload)
        return results
    except (KeyError,TypeError,IndexError,OSError,SyntaxError,json.JSONDecodeError) as exc:
        raise ValueError('invalid HARMAN reference assets') from exc


if __name__=='__main__':
    print('Verified HARMAN tables:',[len(v) for v in verify(Path(__file__).resolve().parents[1])])
