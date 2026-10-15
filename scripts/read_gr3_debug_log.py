"""Decode CRC-protected GR III debug pages; accepts all four SD .BIN files."""
import argparse
import json
import struct
import zlib
from pathlib import Path

EVENTS={10:'menu.enter.before',11:'menu.enter.after',20:'menu.key.before',21:'menu.key.after',
        30:'menu.focus.before',31:'menu.focus.after',40:'menu.confirm.before',41:'menu.confirm.after',
        50:'menu.redraw.before',51:'menu.redraw.after',60:'settings.commit.before',61:'settings.commit.after',
        70:'detail.change',71:'detail.reset',112:'capture.settings',113:'capture.settings.source',114:'capture.highlight.energy',100:'capture.before',101:'capture.after',110:'capture.render.before',111:'capture.render.after',120:'capture.clock'}

def page_records(data):
    if len(data)!=4096:return None
    h=struct.unpack_from('<16I',data)
    if h[0]!=0x4744564d or h[1]!=1 or h[3]>63 or h[4]>=63 or not 0<h[5]<0xffffff00 or h[5]<h[3] or h[6] not in (1,2) or h[15]!=zlib.crc32(data[:60]) or (h[3]<63 and h[4]!=h[3]):return None
    records=[]
    for index in range(h[3]):
        raw=data[64+index*64:128+index*64];r=struct.unpack('<16I',raw)
        if r[0]!=0x474c564d or r[1]!=1 or not 0<r[2]<=h[5] or r[8]!=h[2] or r[9]!=h[6] or r[15]!=zlib.crc32(raw[:60]):return None
        records.append({'sequence':r[2],'event':r[3],'stage':EVENTS.get(r[3],f'unknown.{r[3]}'),
                        'arguments':list(r[4:8]),'build_id':f'{r[8]:08x}','channel':'menu' if r[9]==1 else 'capture'})
    for record in records:
        if record['event']==112:
            slot,packed,sequence,revision=record['arguments']
            record['settings']={'slot':slot,'gain':packed&15,'spread':(packed>>4)&15,
                'threshold':(packed>>8)&15,'grain':(packed>>12)&15,'soft':(packed>>16)&15,
                'sequence':sequence,'renderer_revision':revision}
        if record['event']==114:
            peak,active,pixels,gate=record['arguments']
            record['highlight_energy']={'maximum':peak,'active_pixels':active,'image_pixels':pixels,'gate':gate}
        if record['event']==113:
            slot,source,sequence,namespace=record['arguments']
            record['provenance']={'slot':slot,'source':{0:'journal-v3',1:'defaults',2:'migrated-v2',3:'migrated-v1'}.get(source,'unknown'),
                'sequence':sequence,'journal_namespace':namespace}
    return (h[2],h[6],h[5]),records

def decode_logs(pages):
    selected={};rejected=0
    for data in pages:
        parsed=page_records(data)
        if parsed is None:rejected+=1;continue
        (build,channel,sequence),records=parsed;key=(build,channel)
        if key not in selected or sequence>selected[key][0]:selected[key]=(sequence,records)
    records=[record for _,entries in selected.values() for record in entries]
    records.sort(key=lambda r:(r['build_id'],r['channel'],r['sequence']))
    return {'schema':'m10v-gr3-sd-debug/v1','build_ids':sorted({r['build_id'] for r in records}),
            'rejected_pages':rejected,'records':records}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('files',nargs='+',type=Path)
    args=parser.parse_args();result=decode_logs([p.read_bytes() for p in args.files])
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['records']:raise SystemExit(1)
