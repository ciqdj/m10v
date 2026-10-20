#!/usr/bin/env python3
"""Prove module-loader copy/zero semantics, including its deferred sixteenth record."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.analyze_unity_update import official_profile,_machine,FILE_BASE

LOADERS={
    'gr2':dict(loop=0xA0040538,finish=0xA0040636,seek=0xA0055268,read=0xA0055252,
               allocate=0xA0024D6E,progress=0xA0040CBE,deferred=0xA0046E92,
               context_setter=0xA0040C88,log=0xA0039DE4),
    'gr1':dict(loop=0xA003F0FA,finish=0xA003F2A0,seek=0xA00524C0,read=0xA00524AA,
               allocate=0xA0023E08,progress=0xA003D40E,deferred=0xA0043E9C,
               context_setter=0xA003D3D8,log=0xA003890A),
}

def probe_loader(code:bytes,model:str,*,short_read_index:int|None=None)->dict:
    """Execute the original record loop against synthetic files, RAM and boot state.

    The final callback executes original state-staging code. The eventual low-RAM
    commit and startup jump are outside this probe and are not simulated as success.
    """
    official_profile(code,model);profile=LOADERS[model]
    if short_read_index is not None and (type(short_read_index) is not int or not 0<=short_read_index<16):
        raise ValueError('short-read index must be 0..15')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R6,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
    machine=_machine(code)
    for address,size in ((0,0x1000),(0x51000000,0x10000),(0x52000000,0x20000),(0x53000000,0x1000)):
        machine.mem_map(address,size);machine.mem_write(address,b'\xa5'*size)
    context=0x53000000;stack=0x50010000
    # Decode the exact official setter's PC-relative global-pointer load.
    setter=profile['context_setter'];instruction=struct.unpack_from('>H',code,setter-FILE_BASE)[0]
    if instruction&0xf800!=0x4800:raise ValueError('official context pointer instruction differs')
    literal=((setter+4)&~3)+(instruction&0xff)*4
    pointer=struct.unpack_from('>I',code,literal-FILE_BASE)[0]
    machine.mem_write(pointer,struct.pack('>I',context));machine.mem_write(context+0x108,bytes(16))
    records=[];header=bytearray(512);stream=bytearray(512+16*512)
    lengths=(0,1,2,3,4,7,8,15,16,31,32,33,63,64,65,31)
    zero_lengths=(0,1,2,3,4,7,8,15,16,31,32,33,63,64,65,7)
    for index in range(16):
        source=index*512;address=0x52001000+index*0x100 if index<15 else 0x400
        zero_address=0x52001080+index*0x100
        length=lengths[index];zero_length=zero_lengths[index]
        payload=bytes((index*17+i)%251+1 for i in range(length))
        struct.pack_into('>5I',header,0x20+index*20,source,address,length,zero_address,zero_length)
        stream[source+512:source+512+length]=payload
        records.append(dict(source=source,address=address,length=length,zero_address=zero_address,zero_length=zero_length,payload=payload))
    entry=records[0]['address'];struct.pack_into('>I',header,0x160,entry)
    machine.mem_write(stack+8,bytes(header))
    for offset,value in ((4,1),(0x43c,0xffffffff),(0x440,0),(0x448,0),(0x44c,0x52020000),
                         (0x45c,0),(0x460,0x52000000),(0x468,profile['progress']|1),(0x480,profile['deferred']|1)):
        machine.mem_write(stack+offset,struct.pack('>I',value))
    machine.reg_write(UC_ARM_REG_SP,stack);machine.reg_write(UC_ARM_REG_R6,0)
    position=0;seeks=[];reads=[];loaded=[];finished=False

    def helper(uc,address,size,context_arg):
        nonlocal position,finished
        first,second,count=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        if address==profile['finish']:finished=True;uc.emu_stop();return
        if address==profile['progress']:
            if first>=16:raise ValueError('unexpected loaded-record index')
            loaded.append(first);return # Execute original progress writer.
        if address==profile['seek']:
            if first!=1 or count!=0:raise ValueError('loader seek ABI differs')
            position=second;seeks.append(second);result=0
        elif address==profile['read']:
            index=(position-512)//512
            if first!=1 or not 0<=index<16:raise ValueError('loader read ABI differs')
            row=records[index]
            if position!=row['source']+512 or count!=row['length']:raise ValueError('loader source/size differs')
            if second!=(row['address'] if index<15 else 0x51000000):raise ValueError('loader destination differs')
            actual=max(0,count-1) if index==short_read_index else count
            part=stream[position:position+actual]
            if part:uc.mem_write(second,bytes(part))
            reads.append(dict(index=index,source_file_offset=position,address=second,requested=count,returned=actual))
            position+=actual;result=actual
        elif address==profile['allocate']:
            if first!=records[15]['length']:raise ValueError('deferred allocation size differs')
            result=0x51000000
        elif address==profile['log']:result=0
        else:raise ValueError('unexpected loader boundary')
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

    for key in ('finish','progress','seek','read','allocate','log'):
        address=profile[key];machine.hook_add(UC_HOOK_CODE,helper,begin=address,end=address)
    machine.emu_start(profile['loop']|1,0,timeout=5000000,count=100000)
    if not finished:raise RuntimeError('original loader loop exceeded execution budget')
    def same(address,expected):return bytes(machine.mem_read(address,len(expected)))==expected if expected else True
    direct=all(same(r['address'],r['payload']) for r in records[:15])
    zeroed=all(same(r['zero_address'],bytes(r['zero_length'])) for r in records[:15])
    guards=all(same(r['address']-1,b'\xa5') and same(r['address']+r['length'],b'\xa5')
               and same(r['zero_address']-1,b'\xa5') and same(r['zero_address']+r['zero_length'],b'\xa5') for r in records[:15])
    deferred_values=struct.unpack('>5I',machine.mem_read(context+0xf4,20))
    return dict(loop_entry=hex(profile['loop']),loop_finish=hex(profile['finish']),
                all_records_processed=loaded==list(range(16)),loaded_indices=loaded,seeks=seeks,reads=reads,
                direct_bytes_match=direct,aux_zeroed=zeroed,guards_unchanged=guards,
                low_target_unchanged=same(0x400,b'\xa5'*records[15]['length']),
                deferred_buffer_matches=same(0x51000000,records[15]['payload']),
                deferred_record=dict(zip(('buffer','address','length','zero_address','zero_length'),deferred_values)),
                returned_entry=struct.unpack('>I',machine.mem_read(stack+0x448,4))[0],
                boot_context_pointer=hex(pointer),helpers_intercepted=['seek','file_read','allocation','diagnostic_log'],
                fixture='synthetic records, file bytes, target RAM and boot context; original zero/deferred/progress instructions')

def analyze_runtime(component:bytes,model:str)->dict:
    official_profile(component,model);rows=[]
    for index in range(16):
        source,address,length,zero_address,zero_length=struct.unpack_from('>5I',component,0x20+index*20)
        file_offset=source+512
        if file_offset+length>len(component):raise ValueError('official load record exceeds component')
        rows.append(dict(index=index,source_field=source,source_file_offset=file_offset,address=address,length=length,
                         zero_address=zero_address,zero_length=zero_length,mode='direct' if index<15 else 'deferred',
                         payload_sha256=hashlib.sha256(component[file_offset:file_offset+length]).hexdigest()))
    proof=probe_loader(component,model)
    if not all(proof[k] for k in ('all_records_processed','direct_bytes_match','aux_zeroed','guards_unchanged','low_target_unchanged','deferred_buffer_matches')):
        raise ValueError('original loader synthetic contract proof failed')
    return dict(schema='m10v-unity-loader-proof/v1',model=model,component_sha256=hashlib.sha256(component).hexdigest(),
                entry_field=hex(struct.unpack_from('>I',component,0x160)[0]),load_records=rows,loader_cpu=proof,
                record_semantics_proved=True,deferred_commit_proved=False,hardware_tested=False,
                limits=['CPU entry is the record loop after file/header verification and frame initialization.',
                        'File services, allocation and diagnostic logging are synthetic. Destinations and boot context are synthetic.',
                        'Official copy-control, aux zeroing, progress writer and sixteenth-record staging execute unchanged.',
                        'Actual original header fields are parsed separately; their target addresses are not substituted into the synthetic fixture.',
                        'Deferred low-address commit, complete boot-ROM/update sequencing and final startup jump require further analysis.',
                        'Aux zero ranges are not free injection space. No writable native runtime profile is emitted.'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,choices=LOADERS)
    parser.add_argument('--component',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.component.resolve()==args.out.resolve():raise ValueError('output must not overwrite official input')
    report=analyze_runtime(args.component.read_bytes(),args.model)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(args.out),model=args.model,records=len(report['load_records']),deferred_commit_proved=False)))

if __name__=='__main__':main()
