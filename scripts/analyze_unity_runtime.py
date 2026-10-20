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

def _context_pointer(code:bytes,model:str)->int:
    setter=LOADERS[model]['context_setter'];instruction=struct.unpack_from('>H',code,setter-FILE_BASE)[0]
    if instruction&0xf800!=0x4800:raise ValueError('official context pointer instruction differs')
    literal=((setter+4)&~3)+(instruction&0xff)*4
    return struct.unpack_from('>I',code,literal-FILE_BASE)[0]

def probe_gr2_rom_capacity(code:bytes,image_kind:int,requested_bytes:int)->dict:
    """Execute original storage descriptor, NAND unit arithmetic and size policy."""
    official_profile(code,'gr2')
    if image_kind not in (1,2) or type(requested_bytes) is not int or not 0<=requested_bytes<=0xffffffff:
        raise ValueError('GR II executable/resource kind and u32 byte count required')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=_machine(code);descriptor=0x50000000;stop=0x5001f000
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,stop|1)
    machine.reg_write(UC_ARM_REG_R0,image_kind);machine.reg_write(UC_ARM_REG_R1,descriptor)
    machine.emu_start(0xA005658F,stop,count=1000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop:raise RuntimeError('storage descriptor exceeded execution budget')
    fields=struct.unpack('>15I',machine.mem_read(descriptor,60))
    if fields[6]!=0xA0056561:raise ValueError('original ROM-size callback differs')
    capacity=None;block_bytes=None
    def observe_or_boundary(uc,address,size,ctx):
        nonlocal capacity,block_bytes
        if address==0xA005656C:
            block_bytes=struct.unpack('>I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0];return
        if address==0xA0056580:capacity=uc.reg_read(UC_ARM_REG_R0);return
        # Driver initialization/locking has no substituted size arithmetic.
        uc.reg_write(UC_ARM_REG_R0,0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for address in (0xA005FC9A,0xA00671B8,0xA005656C,0xA0056580):
        machine.hook_add(UC_HOOK_CODE,observe_or_boundary,begin=address,end=address)
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,stop|1)
    machine.reg_write(UC_ARM_REG_R0,requested_bytes);machine.reg_write(UC_ARM_REG_R1,descriptor)
    machine.emu_start(fields[6],stop,count=1000)
    if machine.reg_read(UC_ARM_REG_PC)!=stop or capacity is None or block_bytes is None:
        raise RuntimeError('ROM-size policy exceeded execution budget')
    return dict(image_kind=image_kind,requested_bytes=requested_bytes,capacity_bytes=capacity,
                returned=machine.reg_read(UC_ARM_REG_R0),block_bytes=block_bytes,
                partition_blocks=fields[1],extra_sectors=fields[3],descriptor_entry='0xa005658e',
                policy_entry=hex(fields[6]&~1),helpers_intercepted=['NAND_driver_ready','driver_unlock'],
                scope='Original constant descriptor, 256-sector NAND block calculation and inclusive size comparison; no flash access.')

def probe_gr2_startup_order(code:bytes,*,phase_results:dict[int,int]|None=None)->dict:
    """Run original startup orchestration; subsystem bodies are external boundaries."""
    official_profile(code,'gr2');phase_results=phase_results or {}
    if any(type(k) is not int or type(v) is not int or not 0<=k<16 or not 0<=v<=0xffffffff for k,v in phase_results.items()):
        raise ValueError('invalid synthetic startup phase results')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=_machine(code);modules=[];events=[]
    calls=(0xA002270C,0xA0022E28,0xA0023234,0xA002323A,0xA002323C,0xA002323E,
           0xA0023240,0xA00AFD9C,0xA00C63A6,0xA015D458,0xA0296804,0xA039130A)
    def boundary(uc,address,size,ctx):
        if address==0xA0020AB4:
            events.append(['post_load',0]);return
        first=uc.reg_read(UC_ARM_REG_R0)
        if address==0xA0022E28:
            modules.append(first);events.append(['module',first]);result=0
        elif address==0xA00C63A6:result=phase_results.get(first,0)
        else:result=0
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    for address in (*calls,0xA0020AB4):machine.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,0x5001f001)
    machine.emu_start(0xA0020945,0x5001f000,count=10000)
    if machine.reg_read(UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('startup orchestration exceeded execution budget')
    return dict(entry='0xa0020944',module_indices=modules,events=events,returned=machine.reg_read(UC_ARM_REG_R0),
                post_load_call='0xa0020ab4',post_load_original_target='0xa0023234',
                post_load_original_bytes=code[0xA0020AB4-FILE_BASE:0xA0020AB8-FILE_BASE].hex(),
                helpers_intercepted=[hex(a) for a in calls],
                scope='Original startup branch/call order only; subsystem initialization and module reads are synthetic boundaries.')

def probe_gr2_indexed_loader(code:bytes,*,source_offset:int=0,length:int=513,
                             record_index:int=14,fail_read:int|None=None)->dict:
    """Run the official startup-used single-record loader, with a block-device boundary.

    Header lookup and storage descriptor are synthetic. The original sector math,
    aligned/unaligned copy, memcpy, BSS zero, status update and returns execute.
    """
    official_profile(code,'gr2')
    if any(type(v) is not int or not 0<=v<=4096 for v in (source_offset,length)) or not 0<=record_index<=16:
        raise ValueError('bounded synthetic loader fixture required')
    if fail_read is not None and (type(fail_read) is not int or fail_read<0):raise ValueError('invalid failing read index')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_PC,UC_ARM_REG_LR
    machine=_machine(code)
    machine.mem_map(0x52000000,0x10000);machine.mem_write(0x52000000,b'\xa5'*0x10000)
    machine.mem_map(0x53000000,0x2000);machine.mem_map(0x54000000,0x1000)
    context=0x53000000;header_address=0x53001000;destination=0x52001000
    zero_address=0x52004000;zero_length=37;out=0x52006000
    header=bytearray(code[:512])
    if record_index<16:struct.pack_into('>5I',header,0x20+record_index*20,source_offset,destination,length,zero_address,zero_length)
    machine.mem_write(header_address,bytes(header));machine.mem_write(_context_pointer(code,'gr2'),struct.pack('>I',context))
    machine.mem_write(out,bytes.fromhex('deadbeef'))
    payload=bytes((i*13+7)%251+1 for i in range(length))
    stream=bytearray(b'\x5a'*max(512,((source_offset+length+511)//512)*512))
    stream[source_offset:source_offset+length]=payload
    reads=[];descriptor_address=None

    def helper(uc,address,size,ctx):
        nonlocal descriptor_address
        first,second,count,fourth=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if address==0xA00566BC:
            if first!=1:raise ValueError('indexed loader header source differs')
            result=header_address
        elif address==0xA005658E:
            if first!=1:raise ValueError('indexed loader storage kind differs')
            descriptor_address=second;uc.mem_write(second,bytes(0x3c))
            uc.mem_write(second+0x2c,struct.pack('>I',0x54000001));result=0
        elif address==0x54000000:
            if fourth!=descriptor_address or count*512>8192 or (second+count)*512>len(stream):
                raise ValueError('indexed loader block-read contract differs')
            failed=len(reads)==fail_read
            reads.append(dict(sector=second,count=count,destination=first,failed=failed))
            if not failed and count:uc.mem_write(first,bytes(stream[second*512:(second+count)*512]))
            result=1 if failed else 0
        else:raise ValueError('unexpected indexed-loader boundary')
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

    for address in (0xA00566BC,0xA005658E,0x54000000):machine.hook_add(UC_HOOK_CODE,helper,begin=address,end=address)
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,0x5001f001)
    machine.reg_write(UC_ARM_REG_R0,record_index);machine.reg_write(UC_ARM_REG_R1,out)
    machine.emu_start(0xA0056723,0x5001f000,timeout=5000000,count=300000)
    if machine.reg_read(UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('indexed loader exceeded execution budget')
    def same(address,expected):return bytes(machine.mem_read(address,len(expected)))==expected if expected else True
    return dict(entry='0xa0056722',record_index=record_index,source_offset=source_offset,length=length,
                returned=machine.reg_read(UC_ARM_REG_R0),entry_out=struct.unpack('>I',machine.mem_read(out,4))[0],reads=reads,
                payload_matches=same(destination,payload),aux_zeroed=same(zero_address,bytes(zero_length)),
                guards_unchanged=same(destination-1,b'\xa5') and same(destination+length,b'\xa5') and same(zero_address-1,b'\xa5') and same(zero_address+zero_length,b'\xa5'),
                loaded=record_index<16 and machine.mem_read(context+0x108+record_index,1)[0]==1,
                helpers_intercepted=['header_accessor','storage_descriptor','block_read'],
                storage_base='synthetic component payload, excluding its 512-byte header')

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
    pointer=_context_pointer(code,model)
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

def parse_executable_load_map(component:bytes)->list:
    """Independent structural gate; callers must separately verify source identity/checksum."""
    if not isinstance(component,bytes) or len(component)<512 or component[0x10]!=1:
        raise ValueError('executable component header required')
    if struct.unpack_from('>I',component,0x168)[0]!=len(component):raise ValueError('component file length differs')
    rows=[]
    for index in range(16):
        source,address,length,zero_address,zero_length=struct.unpack_from('>5I',component,0x20+index*20)
        file_offset=source+512
        if source%512 or file_offset+length>len(component):raise ValueError('load record source bounds/alignment invalid')
        if address%4 or address+length>0x100000000:raise ValueError('load destination bounds/alignment invalid')
        if zero_address%4 or zero_address+zero_length>0x100000000:raise ValueError('load zero bounds/alignment invalid')
        for previous in rows:
            if length and previous['length']:
                if file_offset<previous['source_file_offset']+previous['length'] and previous['source_file_offset']<file_offset+length:
                    raise ValueError('load source ranges overlap')
                if address<previous['address']+previous['length'] and previous['address']<address+length:
                    raise ValueError('load destination ranges overlap')
        rows.append(dict(index=index,source_field=source,source_file_offset=file_offset,address=address,length=length,
                         zero_address=zero_address,zero_length=zero_length,mode='direct' if index<15 else 'deferred',
                         payload_sha256=hashlib.sha256(component[file_offset:file_offset+length]).hexdigest()))
    for row in rows:
        if not row['zero_length']:continue
        lo=row['zero_address'];hi=lo+row['zero_length']
        for code in rows:
            if code['length'] and lo<code['address']+code['length'] and code['address']<hi:
                raise ValueError('load zero range overlaps code destination')
        for previous in rows[:row['index']]:
            if previous['zero_length'] and lo<previous['zero_address']+previous['zero_length'] and previous['zero_address']<hi:
                raise ValueError('load zero ranges overlap')
    entry=struct.unpack_from('>I',component,0x160)[0]
    if not any(row['address']<=entry<row['address']+row['length'] for row in rows[:15]):
        raise ValueError('entry is not inside a directly loaded code segment')
    return rows

def analyze_runtime(component:bytes,model:str)->dict:
    official_profile(component,model);rows=parse_executable_load_map(component)
    proof=probe_loader(component,model)
    if not all(proof[k] for k in ('all_records_processed','direct_bytes_match','aux_zeroed','guards_unchanged','low_target_unchanged','deferred_buffer_matches')):
        raise ValueError('original loader synthetic contract proof failed')
    startup_evidence={}
    if model=='gr2':
        indexed=probe_gr2_indexed_loader(component)
        startup=probe_gr2_startup_order(component)
        capacity=[probe_gr2_rom_capacity(component,kind,0) for kind in (1,2)]
        for row in capacity:
            maximum=probe_gr2_rom_capacity(component,row['image_kind'],row['capacity_bytes'])
            overflow=probe_gr2_rom_capacity(component,row['image_kind'],row['capacity_bytes']+1)
            if maximum['returned']!=0 or overflow['returned']!=0xffffffff:
                raise ValueError('original storage size boundary proof failed')
            row['boundary_checks']=dict(at_capacity_returned=maximum['returned'],over_capacity_returned=overflow['returned'])
        if not all(indexed[k] for k in ('payload_matches','aux_zeroed','guards_unchanged','loaded')) or indexed['returned']!=0:
            raise ValueError('original indexed loader contract proof failed')
        if startup['module_indices'][-1]!=14 or startup['events'][-2:]!=[['module',14],['post_load',0]]:
            raise ValueError('original startup ordering proof failed')
        startup_evidence=dict(indexed_loader_cpu=indexed,startup_cpu=startup,rom_capacity_cpu=capacity)
    return dict(schema='m10v-unity-loader-proof/v2',model=model,component_sha256=hashlib.sha256(component).hexdigest(),
                entry_field=hex(struct.unpack_from('>I',component,0x160)[0]),load_records=rows,loader_cpu=proof,**startup_evidence,
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
