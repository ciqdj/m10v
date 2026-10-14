"""Losslessly embed the existing simulation tables; no fitting or resampling."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'web/gr3/film-catalog.json'
TARGET=ROOT/'native/gr3/m10v_legacy_data.h'

def generate():
    raw=SOURCE.read_bytes();looks=json.loads(raw)['looks']
    if len(looks)!=32 or len({f['id'] for f in looks})!=32:raise ValueError('legacy catalogue changed')
    packed=bytearray();rows=[]
    for f in looks:
        name=f['name'].encode('ascii')
        if len(name)>23:raise ValueError('name too long')
        for key in ('matrixQ13','postQ512'):
            if len(f[key])!=9 or any(not isinstance(v,int) or not -16384<=v<=16384 for v in f[key]):raise ValueError('matrix range')
        start=len(packed)
        for key,count in [('curves',256),('knots',33)]:
            if len(f[key])!=3:raise ValueError('channels')
            for values in f[key]:
                if len(values)!=count:raise ValueError('curve length')
                previous=0
                for value in values:
                    if not isinstance(value,int) or not previous<=value<=16383:raise ValueError('curve range/monotonicity')
                    delta=value-previous;previous=value
                    if delta<128:packed.append(delta)
                    else:packed.extend([(delta&127)|128,delta>>7])
        row='{'+json.dumps(f['name'])+',{'+','.join(map(str,f['matrixQ13']))+'},{'+','.join(map(str,f['postQ512']))+'},'+str(start)+','+str(len(packed)-start)+'}'
        rows.append(row)
    text='/* Generated losslessly from the existing catalogue; retain its source notices. */\n'
    text+='#define M10V_LEGACY_SOURCE_SHA256 "'+hashlib.sha256(raw).hexdigest()+'"\n'
    text+='typedef struct {char name[24];int16_t matrix[9],post[9];uint32_t offset,size;} m10v_legacy_record;\n'
    text+='static const m10v_legacy_record legacy_records[32]={\n'+',\n'.join(rows)+'\n};\n'
    text+='static const uint8_t legacy_bytes['+str(len(packed))+']={\n'
    text+='\n'.join(','.join(map(str,packed[i:i+64]))+',' for i in range(0,len(packed),64))+'\n};\n'
    return text

if __name__=='__main__':
    TARGET.write_text(generate())
    print('embedded 32 exact matrices, 256-point curves and 33-point knots')
