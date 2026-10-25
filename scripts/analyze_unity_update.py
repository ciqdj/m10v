#!/usr/bin/env python3
"""Identity-locked GR/GR II header and weighted-checksum CPU evidence. No flash I/O."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

FILE_BASE=0xA0020200
PROFILES={
    'gr2':dict(sha='13fa830bff194679628eb1bb3f233420ee23c4fca3a28c4b650c53692820de95',
               header=0xA0057684,copy=0xA00A027C,compare=0xA009FE7C,
               checksum=0xA003FD72,success=0xA003FEC4,failure=0xA003FFDE,
               checksum_compare=0xA003FEB8,allocate=0xA0024D6E,free=0xA0024E0E,
               read=0xA0055252,modulo=0xA00B0B88),
    'gr1':dict(sha='08c19e07fafb12e075e1e5cc4f74fe22a1b57132614a4e8d4174c669a865e728',
               header=0xA0053994,copy=0xA009DB2C,compare=0xA009D72C,
               checksum=0xA00546E2,success=0xA0054834,failure=0xA0054898,
               checksum_compare=0xA0054828,allocate=0xA0023E08,free=0xA0023EC6,
               read=0xA00524AA,modulo=0xA00AE644),
}

def official_profile(code:bytes,model:str)->dict:
    if model not in PROFILES:raise ValueError('unsupported model')
    profile=PROFILES[model]
    if hashlib.sha256(code).hexdigest()!=profile['sha']:
        raise ValueError(f'exact {model} executable component identity required')
    return profile

def compute_update_checksum(payload:bytes,*,initial_position:int=0)->int:
    """Sum byte*(2+(u32 position % 6)), wrapping the accumulator to u32."""
    if not isinstance(payload,bytes) or type(initial_position) is not int or not 0<=initial_position<=0xffffffff:
        raise ValueError('payload bytes and unsigned 32-bit initial position required')
    total=0;at=0;position=initial_position
    while at<len(payload):
        count=min(len(payload)-at,0x100000000-position)
        block=payload[at:at+count]
        total+=sum((2+(position+i)%6)*sum(block[i::6]) for i in range(6))
        at+=count;position=0
    return total&0xffffffff

def _machine(code:bytes):
    from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_BIG_ENDIAN
    machine=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_BIG_ENDIAN)
    machine.mem_map(0xA0020000,(len(code)+0x2200+4095)&~4095)
    machine.mem_write(FILE_BASE,code)
    machine.mem_map(0x50000000,0x20000)
    return machine

def execute_update_checksum(code:bytes,model:str,payload:bytes,expected:int,*,
                            initial_position:int=0,chunks:list[int]|None=None,
                            declared_size:int|None=None)->dict:
    """Execute original checksum loop, ARM modulo helper and comparison branches.

    Entry is after header validation. Only allocation, file-read and free boundaries
    are replaced. No arithmetic or comparison helper is replaced.
    """
    profile=official_profile(code,model)
    if not isinstance(payload,bytes) or len(payload)>64*1024*1024:raise ValueError('payload size invalid')
    declared_size=len(payload) if declared_size is None else declared_size
    if any(type(n) is not int or not 0<=n<=0xffffffff for n in (initial_position,expected,declared_size)):
        raise ValueError('unsigned 32-bit checksum fields required')
    if chunks is not None and any(type(n) is not int or not 0<n<=0x20000 for n in chunks):
        raise ValueError('read chunks must be 1..131072 bytes')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    machine=_machine(code);machine.mem_map(0x51000000,0x20000)
    stack=0x50010000;header=bytearray(512)
    for offset,value in ((0x20,initial_position),(0x164,declared_size),(0x16c,expected),(0x178,1)):
        struct.pack_into('>I',header,offset,value)
    machine.mem_write(stack,bytes(header));machine.mem_write(stack+0x478,struct.pack('>I',1))
    machine.reg_write(UC_ARM_REG_SP,stack)
    position=0;read_sizes=[];accepted=None;compared=None

    def helper(uc,address,size,context):
        nonlocal position,accepted,compared
        if address==profile['checksum_compare']:
            compared=[uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)];return
        if address in (profile['success'],profile['failure']):
            accepted=address==profile['success'];uc.emu_stop();return
        first,second,count=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        if address==profile['allocate']:
            if first!=0x20000:raise ValueError('original checksum allocation size differs')
            result=0x51000000
        elif address==profile['free']:
            if first!=0x51000000:raise ValueError('original checksum frees unexpected pointer')
            result=0
        elif address==profile['read']:
            if (first,second,count)!=(1,0x51000000,0x20000):raise ValueError('original checksum read contract differs')
            limit=chunks[len(read_sizes)] if chunks and len(read_sizes)<len(chunks) else count
            part=payload[position:position+limit]
            if part:uc.mem_write(second,part)
            position+=len(part);read_sizes.append(len(part));result=len(part)
        else:raise ValueError('unexpected checksum interception')
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))

    for key in ('allocate','free','read','success','failure','checksum_compare'):
        address=profile[key];machine.hook_add(UC_HOOK_CODE,helper,begin=address,end=address)
    machine.emu_start(profile['checksum']|1,0,timeout=30000000,count=60*len(payload)+10000)
    if accepted is None:raise RuntimeError('original checksum CPU exceeded execution budget')
    actual=struct.unpack('>I',machine.mem_read(stack+0x480,4))[0]
    return dict(accepted=accepted,computed_checksum=actual,expected_checksum=expected,
                bytes_read=position,declared_size=declared_size,read_sizes=read_sizes,
                initial_position=initial_position,comparison_registers=compared,
                entry=hex(profile['checksum']),comparison_entry=hex(profile['checksum_compare']),
                modulo_entry=hex(profile['modulo']),helpers_intercepted=['allocation','file_read','free'])

def _header_cases(code:bytes,profile:dict)->list:
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    cases=[]
    for kind in ('official_header','low_bit_changed','high_bit_changed'):
        machine=_machine(code);header=bytearray(code[:512]);calls=[]
        if kind=='low_bit_changed':header[0]^=1
        if kind=='high_bit_changed':header[0]^=0x80
        machine.mem_write(0x50000000,bytes(header))
        def helper(uc,address,size,context):
            first,second,count=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
            if count!=16:raise ValueError('header checker helper length differs')
            if address==profile['copy']:
                uc.mem_write(first,bytes(uc.mem_read(second,count)));operation='copy'
            else:
                uc.reg_write(UC_ARM_REG_R0,0 if uc.mem_read(first,count)==uc.mem_read(second,count) else 1)
                operation='compare_equal_only'
            calls.append(dict(entry=hex(address),operation=operation,bytes=count))
            uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        for address in (profile['copy'],profile['compare']):machine.hook_add(UC_HOOK_CODE,helper,begin=address,end=address)
        machine.reg_write(UC_ARM_REG_SP,0x5000f000);machine.reg_write(UC_ARM_REG_LR,0x50010001)
        machine.reg_write(UC_ARM_REG_R0,0x50000000)
        machine.emu_start(profile['header']|1,0x50010000,count=1000)
        if machine.reg_read(UC_ARM_REG_PC)!=0x50010000:raise RuntimeError('header checker exceeded instruction budget')
        cases.append(dict(input=kind,returned=True,comparison_equal=machine.reg_read(UC_ARM_REG_R0)==0,helper_calls=calls))
    return cases

def analyze_update(component:bytes,model:str)->dict:
    profile=official_profile(component,model)
    entry,data_bytes,file_bytes,checksum=struct.unpack_from('>4I',component,0x160)
    if file_bytes!=len(component) or data_bytes!=len(component)-512:raise ValueError('component header lengths differ')
    position=struct.unpack_from('>I',component,0x20)[0]
    proof=execute_update_checksum(component,model,component[512:],checksum,initial_position=position)
    if not proof['accepted'] or compute_update_checksum(component[512:],initial_position=position)!=checksum:
        raise ValueError('official checksum differs from original CPU')
    records=[]
    for index in range(16):
        source,address,length,aux_address,aux_length=struct.unpack_from('>5I',component,0x20+index*20)
        records.append(dict(source_field=hex(source),address_field=hex(address),length_field=length,
                            aux_address_field=hex(aux_address),aux_length_field=aux_length))
    return dict(schema='m10v-unity-update-proof/v1',model=model,updater_sha256=profile['sha'],byte_order='big-endian',
                header_check_entry=hex(profile['header']),initial_instruction_mapping=dict(file_base=hex(FILE_BASE),entry_field=hex(entry)),
                header=dict(data_bytes=data_bytes,file_bytes=file_bytes,update_checksum=hex(checksum),verify_flags=list(struct.unpack_from('>4I',component,0x170))),
                raw_load_records=records,cases=_header_cases(component,profile),modified_checksum_proved=True,checksum_cpu=proof,
                checksum_algorithm=dict(formula='sum(byte[i] * (2 + (u32(initial_position+i) % 6))) modulo 2^32',
                                        payload_file_offset=512,payload_bytes=data_bytes,initial_position_header_offset=0x20),
                limits=['Checksum starts after header validation; allocation, file read and free are synthetic boundaries.',
                        'Original Thumb arithmetic, ARM modulo-6 helper, size comparison and checksum comparison execute unchanged.',
                        'Header copy/equality helpers are intercepted; comparison sign is not asserted.',
                        'Complete update sequencing, peripheral/flash I/O and hardware acceptance are not proved.'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',required=True,choices=PROFILES)
    parser.add_argument('--component',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if args.component.resolve()==args.out.resolve():raise ValueError('output must not overwrite official component')
    report=analyze_update(args.component.read_bytes(),args.model)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(report=str(args.out),model=args.model,checksum=report['header']['update_checksum'],cpu_accepted=report['checksum_cpu']['accepted'])))

if __name__=='__main__':main()
