#!/usr/bin/env python3
"""Assemble a research GR II executable component; never package or flash firmware."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_unity_update import official_profile,compute_update_checksum
from scripts.analyze_unity_runtime import parse_executable_load_map
from scripts.build_gr2_runtime import BASE,LIMIT,early_bootstrap,memory_reservations

# Source edits take effect when their original module is loaded. No running
# eight-byte Thumb instruction window is overwritten by this assembler.
HOOKS=(
    (0xA0020AB4,'f002fbbE1c41d10b','gr2_startup_chain','startup'),
    (0xA02AD48C,'0004000db0ad2198','gr2_producer_chain','producer'),
    (0xA02ADC98,'a806f684fc0e980a','gr2_jpeg_chain','jpeg'),
    (0xA0394950,'0006000d24002900','gr2_ui_event_chain','ui_event'),
    (0xA03948C4,'0004b084f493fa65','gr2_menu_route_chain','menu_route'),
    (0xA03C1380,'b5f14d872601b084','gr2_menu_categories','menu_categories'),
    (0xA039D168,'0007000d694e6908','gr2_menu_descriptor_chain','menu_descriptor'),
)

def build_gr2_component(official:bytes,runtime_report:dict)->tuple[bytes,dict]:
    profile=official_profile(official,'gr2');before=parse_executable_load_map(official)
    try:
        runtime=bytes.fromhex(runtime_report['runtime_hex']);symbols=runtime_report['symbols']
        valid=(runtime_report['official_sha256']==profile['sha'] and runtime_report['base']==BASE and
               runtime_report['endianness']=='big' and runtime_report['be8'] is False and runtime_report['can_package'] is False and
               runtime_report['code_bytes']==len(runtime) and len(runtime)%4==0 and
               len(runtime)<=runtime_report['memory_bytes']<=LIMIT-BASE and
               hashlib.sha256(runtime).hexdigest()==runtime_report['runtime_sha256'])
    except (KeyError,TypeError,ValueError) as error:raise ValueError('audited GR II BE32 runtime required') from error
    if not valid:raise ValueError('runtime identity, layout or research gate differs')
    early=early_bootstrap(official)
    if runtime_report.get('early_bootstrap')!=early or runtime_report.get('memory_reservations')!=memory_reservations(official):
        raise ValueError('early-load or memory-reservation contract differs')
    source_field=(len(official)-512+511)&~511
    candidate=bytearray(official);candidate.extend(bytes(512+source_field-len(candidate)));candidate.extend(runtime)
    if len(candidate)>0x81fc00:raise ValueError('candidate exceeds original executable partition policy')
    patches=[]
    def write(offset:int,expected:bytes,value:bytes,purpose:str,address:int|None=None):
        if len(expected)!=len(value) or bytes(candidate[offset:offset+len(value)])!=expected:raise ValueError(purpose+' source preimage differs')
        if any(offset<row['offset']+row['bytes'] and row['offset']<offset+len(value) for row in patches):raise ValueError('source patch ranges overlap')
        candidate[offset:offset+len(value)]=value
        patches.append(dict(offset=offset,address=address,bytes=len(value),purpose=purpose,expected_hex=expected.hex(),replacement_hex=value.hex()))
    def offset(address:int,count:int)->int:
        matches=[row['source_file_offset']+address-row['address'] for row in before[:15]
                 if row['address']<=address and address+count<=row['address']+row['length']]
        if len(matches)!=1:raise ValueError('source edit does not have exactly one original load owner')
        return matches[0]
    for row in memory_reservations(official):
        write(row['source_file_offset'],struct.pack('>I',row['expected']),struct.pack('>I',row['replacement']),row['purpose'],row['address'])
    write(early['source_file_offset'],bytes(len(bytes.fromhex(early['stub_hex']))),bytes.fromhex(early['stub_hex']),'early module14 bootstrap',early['address'])
    write(early['site_source_offset'],bytes.fromhex('24010020'),bytes.fromhex(early['site_patch_hex']),'early startup dispatch',early['site'])
    write(early['load_length_source_offset'],struct.pack('>I',early['original_load_bytes']),struct.pack('>I',early['extended_load_bytes']),'module0 bootstrap load extent')
    for address,preimage,symbol,label in HOOKS:
        target=symbols.get(symbol)
        if type(target) is not int or target&3 or not BASE<=target<BASE+len(runtime):raise ValueError(label+' hook target is outside native code')
        patch=bytes.fromhex('4b004718')+struct.pack('>I',target)
        report_key='startup_patch_hex' if label=='startup' else label+'_hook_patch_hex'
        if runtime_report.get(report_key)!=patch.hex():raise ValueError(label+' runtime hook contract differs')
        write(offset(address,8),bytes.fromhex(preimage),patch,label+' source hook',address)
    if runtime_report.get('menu_raster_classifier_patch_hex')!='2d6a':raise ValueError('private raster classifier contract differs')
    write(offset(0xA039D60E,2),bytes.fromhex('2d68'),bytes.fromhex('2d6a'),'two private caption raster classes',0xA039D60E)
    at=0x20+14*20
    write(at,official[at:at+20],struct.pack('>5I',source_field,BASE,len(runtime),BASE+len(runtime),runtime_report['memory_bytes']-len(runtime)),'native module14 load record')
    checksum=compute_update_checksum(bytes(candidate[512:]),initial_position=struct.unpack_from('>I',candidate,0x20)[0])
    write(0x164,official[0x164:0x170],struct.pack('>3I',len(candidate)-512,len(candidate),checksum),'component lengths and weighted checksum')
    result=bytes(candidate);after=parse_executable_load_map(result)
    if after[15]!=before[15] or result[0x170:0x180]!=official[0x170:0x180] or result[:0x20]!=official[:0x20]:
        raise ValueError('original identity, verification policy or deferred record changed')
    # A data-vector bootstrap is installed by native activation, never by source
    # edits before the early runtime exists. The original callback remains code.
    for address in (0xA00AF884,0xA0044F4C):
        at=offset(address,4)
        if result[at:at+4]!=official[at:at+4]:raise ValueError('cache bootstrap was installed prematurely')
    return result,dict(schema='m10v-gr2-research-component/v1',official_sha256=profile['sha'],sha256=hashlib.sha256(result).hexdigest(),
                       file_bytes=len(result),data_bytes=len(result)-512,weighted_checksum=checksum,patches=patches,load_map=after,
                       early_bootstrap=early,runtime_sha256=runtime_report['runtime_sha256'],can_package=False,activation_ready=False,
                       limits=['Research component only; native post-load activation and UI-owned journal restoration remain incomplete.',
                               'Original low/deferred payload and all verification switches are preserved; no hardware boot or flash proof.'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official',type=Path,required=True);parser.add_argument('--runtime-audit',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();candidate,audit=build_gr2_component(args.official.read_bytes(),json.loads(args.runtime_audit.read_text()))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_bytes(candidate)
    report=args.out.with_suffix(args.out.suffix+'.audit.json');report.write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(component=str(args.out),audit=str(report),bytes=len(candidate),can_package=False,activation_ready=False)))

if __name__=='__main__':main()
