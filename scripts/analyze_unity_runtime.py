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

def probe_gr2_bootstrap_extension(code:bytes,*,contract:dict)->dict:
    """Run original indexed loader on the complete extended module0 source."""
    official_profile(code,'gr2')
    from scripts.build_gr2_runtime import early_bootstrap
    from scripts.analyze_gr2_native_contract import runtime_machine
    if contract!=early_bootstrap(code):raise ValueError('identity-locked early bootstrap contract required')
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=runtime_machine(code);rows=parse_executable_load_map(code);row=rows[0]
    source=bytearray(code);struct.pack_into('>I',source,contract['load_length_source_offset'],contract['extended_load_bytes'])
    stub=bytes.fromhex(contract['stub_hex']);site=bytes.fromhex(contract['site_patch_hex'])
    source[contract['source_file_offset']:contract['source_file_offset']+len(stub)]=stub
    source[contract['site_source_offset']:contract['site_source_offset']+len(site)]=site
    header=0x50004000;uc.mem_write(header,bytes(source[:512]));stream=bytes(source[512:]);reads=[]
    context=0xA0020000;uc.mem_write(_context_pointer(code,'gr2'),struct.pack('>I',context))
    end=row['address']+contract['extended_load_bytes'];uc.mem_write(end,b'\xa5'*16)
    neighbor=bytes(uc.mem_read(rows[1]['address'],32));uc.mem_write(row['zero_address'],b'\xa5'*row['zero_length'])
    def boundary(machine,address,size,unused):
        a,b,c=[machine.reg_read(register) for register in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1,r.UC_ARM_REG_R2)]
        if address==0xA00566BC:result=header
        elif address==0xA005658E:machine.mem_write(b,bytes(60));machine.mem_write(b+0x2c,struct.pack('>I',0x5001D001));result=0
        else:
            if (b+c)*512>len(stream):raise ValueError('module0 source read exceeds original component')
            reads.append([b,c]);machine.mem_write(a,stream[b*512:(b+c)*512]);result=0
        machine.reg_write(r.UC_ARM_REG_R0,result);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (0xA00566BC,0xA005658E,0x5001D000):uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    uc.reg_write(r.UC_ARM_REG_R0,0);uc.reg_write(r.UC_ARM_REG_R1,0);uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
    uc.emu_start(0xA0056723,0x5001f000,count=3000000)
    if uc.reg_read(r.UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('extended original module0 loader budget exceeded')
    expected=bytes(source[row['source_file_offset']:row['source_file_offset']+contract['extended_load_bytes']])
    return dict(returned=uc.reg_read(r.UC_ARM_REG_R0),extended_payload_matches=bytes(uc.mem_read(row['address'],len(expected)))==expected,
                guard_preserved=bytes(uc.mem_read(end,16))==b'\xa5'*16,next_module_preserved=bytes(uc.mem_read(rows[1]['address'],32))==neighbor,
                bss_zeroed=bytes(uc.mem_read(row['zero_address'],row['zero_length']))==bytes(row['zero_length']),
                completion_flag_set=uc.mem_read(context+0x108,1)==b'\x01',read_requests=reads,
                helpers_intercepted=['component-header lookup','storage descriptor','bounded sector read'],hardware_tested=False,
                scope='Full original module0 indexed-loader copy, tail, BSS zero and completion flag with extended44-byte bootstrap in existing source padding. Header/storage are synthetic; no boot-ROM, flash write or hardware cache claim.')

def probe_gr2_module_guard(code:bytes,*,loaded:bool)->dict:
    """Execute original record14 wrapper prefix through its load-status guard."""
    official_profile(code,'gr2')
    if type(loaded) is not bool:raise ValueError('explicit synthetic completion flag required')
    from unicorn import UC_HOOK_CODE
    from unicorn import arm_const as r
    uc=_machine(code);context=0x50003000;requests=[]
    uc.mem_write(_context_pointer(code,'gr2'),struct.pack('>I',context))
    uc.mem_write(context+0x108+14,bytes([int(loaded)]))
    def boundary(machine,address,size,unused):
        if address==0xA0022E60:machine.emu_stop();return
        if address==0xA003FB02:requests.append([machine.reg_read(r.UC_ARM_REG_R0),machine.reg_read(r.UC_ARM_REG_R1)])
        machine.reg_write(r.UC_ARM_REG_R0,0);machine.reg_write(r.UC_ARM_REG_PC,machine.reg_read(r.UC_ARM_REG_LR))
    for address in (0xA00AFDA4,0xA00AFDAC,0xA003FB02,0xA0022E60):uc.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    uc.reg_write(r.UC_ARM_REG_R0,14);uc.reg_write(r.UC_ARM_REG_SP,0x50018000);uc.reg_write(r.UC_ARM_REG_LR,0x5001f001)
    uc.emu_start(0xA0022E29,0x5001f000,count=1000)
    return dict(indexed_load_requests=requests,reached_guard_continuation=uc.reg_read(r.UC_ARM_REG_PC)==0xA0022E60,
                helpers_intercepted=['profiling initialize/start','module-load request observation'],
                scope='Original wrapper prefix, boot-kind getter and loaded-byte getter/branch; actual loading and post-module actions are boundaries. Stops at guard continuation, not a full wrapper return.')

def probe_gr2_startup_order(code:bytes,*,phase_results:dict[int,int]|None=None,native_runtime:dict|None=None,early_native:bool=False,fail_native_read:bool=False,candidate_component:bytes|None=None)->dict:
    """Run original startup orchestration; subsystem bodies are external boundaries."""
    official_profile(code,'gr2');phase_results=phase_results or {}
    if (early_native or fail_native_read) and native_runtime is None:raise ValueError('native runtime required for early bootstrap')
    if fail_native_read and not early_native:raise ValueError('early bootstrap required for native read failure')
    if any(type(k) is not int or type(v) is not int or not 0<=k<16 or not 0<=v<=0xffffffff for k,v in phase_results.items()):
        raise ValueError('invalid synthetic startup phase results')
    from unicorn import UC_HOOK_CODE
    from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
    candidate_mode=candidate_component is not None
    if candidate_mode:
        if not early_native or native_runtime is None:raise ValueError('candidate startup requires early native runtime')
        from scripts.build_gr2_component import build_gr2_component
        from scripts.analyze_gr2_native_contract import runtime_machine
        expected,_=build_gr2_component(code,native_runtime)
        if candidate_component!=expected:raise ValueError('candidate is not the audited source assembly')
        machine=runtime_machine(code);candidate_rows=parse_executable_load_map(candidate_component);row=candidate_rows[0]
        machine.mem_write(row['address'],candidate_component[row['source_file_offset']:row['source_file_offset']+row['length']])
        machine.mem_write(row['zero_address'],bytes(row['zero_length']))
        for unloaded in candidate_rows[1:14]:machine.mem_write(unloaded['address'],b'\xa5'*unloaded['length'])
    else:machine=_machine(code)
    modules=[];events=[];post_load_return=None
    native_result={};native_load_count=0;native_stream=b'';context=0xA0020000 if candidate_mode else 0x50003000;header_address=0x50004000
    if native_runtime is not None:
        runtime=bytes.fromhex(native_runtime['runtime_hex']);base=native_runtime['base'];memory=native_runtime['memory_bytes']
        if base!=0xa0798000 or memory<len(runtime) or memory>0x68000 or len(runtime)%4:
            raise ValueError('bounded aligned native runtime required')
        if hashlib.sha256(runtime).hexdigest()!=native_runtime['runtime_sha256'] or native_runtime['endianness']!='big' or native_runtime['be8']:
            raise ValueError('audited BE32 runtime required')
        patch=bytes.fromhex(native_runtime['startup_patch_hex'])
        if len(patch)!=8 or patch[:4]!=bytes.fromhex('4b004718'):raise ValueError('native startup veneer differs')
        if not candidate_mode:machine.mem_map(base,0x68000)
        machine.mem_write(base,b'\xa5'*memory)
        if candidate_mode:
            if bytes(machine.mem_read(0xA0020AB4,8))!=patch:raise ValueError('candidate post-load source differs')
        else:machine.mem_write(0xA0020AB4,patch)
        if early_native:
            from scripts.build_gr2_runtime import early_bootstrap
            early=native_runtime['early_bootstrap']
            if early!=early_bootstrap(code):raise ValueError('early native bootstrap identity mismatch')
            if candidate_mode:
                if bytes(machine.mem_read(early['address'],len(bytes.fromhex(early['stub_hex']))))!=bytes.fromhex(early['stub_hex']):raise ValueError('candidate module0 extension differs')
            else:
                machine.mem_write(early['address'],bytes.fromhex(early['stub_hex']))
                machine.mem_write(early['site'],bytes.fromhex(early['site_patch_hex']))
            machine.mem_write(early['preserved_stub_address'],b'\xa5'*4)
        if candidate_mode:
            header=bytearray(candidate_component[:512]);native_stream=candidate_component[512:]
            native_stream+=bytes((-len(native_stream))%512);machine.mem_write(context+0x108,b'\x01')
        else:
            header=bytearray(code[:512]);struct.pack_into('>5I',header,0x20+14*20,0,base,len(runtime),base+len(runtime),memory-len(runtime))
            native_stream=runtime+bytes((-len(runtime))%512)
        machine.mem_write(header_address,bytes(header));machine.mem_write(_context_pointer(code,'gr2'),struct.pack('>I',context))
        machine.mem_map(0x54000000,4096)
    calls=(0xA002270C,0xA0022E28,0xA002323A,0xA002323C,0xA002323E,
           0xA0023240,0xA00AFD9C,0xA00C63A6,0xA015D458,0xA0296804,0xA039130A)
    def boundary(uc,address,size,ctx):
        nonlocal post_load_return,native_load_count
        if address==0xA0020ABC:
            post_load_return=uc.reg_read(UC_ARM_REG_R0);return
        if address==0xA0020AB4:
            events.append(['post_load',0])
            if native_runtime is not None:
                native_result['native_loaded_by_original_indexed_loader']=(machine.mem_read(context+0x108+14,1)==b'\x01' and bytes(machine.mem_read(base,len(runtime)))==runtime)
                native_result['native_bss_zero_before_init']=bytes(machine.mem_read(base+len(runtime),memory-len(runtime)))==bytes(memory-len(runtime))
            return
        first=uc.reg_read(UC_ARM_REG_R0)
        if early_native and address==0xA0056722:
            if first==14:events.append(['native_early_load',14]);native_load_count+=1
            elif not candidate_mode:raise ValueError('early bootstrap selected wrong native record')
            if candidate_mode:events.append(['indexed_load',first])
            return

        if native_runtime is not None and address in (0xA00566BC,0xA005658E,0x54000000):
            from unicorn.arm_const import UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
            second,count,fourth=[uc.reg_read(r) for r in (UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
            if address==0xA00566BC:result=header_address
            elif address==0xA005658E:
                uc.mem_write(second,bytes(60));uc.mem_write(second+0x2c,struct.pack('>I',0x54000001));result=0
            else:
                if (second+count)*512>len(native_stream):raise ValueError('native module read exceeds synthetic storage')
                if fail_native_read:result=0xffffffff
                else:uc.mem_write(first,native_stream[second*512:(second+count)*512]);result=0
            uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        if address==0xA0022E28:
            if first==0xffffffff:events.append(['finalize',first])
            else:modules.append(first);events.append(['module',first])
            if native_runtime is not None and (first==14 or candidate_mode and 0<first<15):
                # The original wrapper skips its indexed load when its context
                # flag is already set; the guard is proved separately.
                if not early_native or machine.mem_read(context+0x108+first,1)!=b'\x01':
                    from unicorn.arm_const import UC_ARM_REG_R1
                    if not early_native and first==14:native_load_count+=1
                    uc.reg_write(UC_ARM_REG_R1,0);uc.reg_write(UC_ARM_REG_PC,0xA0056723);return
            result=0
        elif address==0xA00C63A6:
            if early_native and first==1:machine.mem_write(native_runtime['symbols']['gr2_code_sync_status'],struct.pack('>I',0x12345678))
            events.append(['phase',first]);result=phase_results.get(first,0)
        else:result=0
        uc.reg_write(UC_ARM_REG_R0,result);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    extra=(0xA00566BC,0xA005658E,0x54000000,*((0xA0056722,) if early_native else ())) if native_runtime is not None else ()
    for address in (*calls,0xA0020AB4,0xA0020ABC,*extra):machine.hook_add(UC_HOOK_CODE,boundary,begin=address,end=address)
    from unicorn import arm_const as registers
    saved=[0x33440000+index for index in range(8)]
    for index,value in enumerate(saved):machine.reg_write(registers.UC_ARM_REG_R4+index,value)
    machine.reg_write(UC_ARM_REG_SP,0x50018000);machine.reg_write(UC_ARM_REG_LR,0x5001f001)
    machine.emu_start(0xA0020945,0x5001f000,count=8000000 if candidate_mode else 10000)
    if machine.reg_read(UC_ARM_REG_PC)!=0x5001f000:raise RuntimeError('startup orchestration exceeded execution budget')
    if native_runtime is not None:
        native_result['native_load_count']=native_load_count
        if early_native:native_result['original_stub_restored']=bytes(machine.mem_read(early['preserved_stub_address'],4))==bytes.fromhex(early['preserved_stub_hex'])
        native_result['native_bss_canary']=struct.unpack('>I',machine.mem_read(native_runtime['symbols']['gr2_code_sync_status'],4))[0]
        native_result['native_boot_count']=struct.unpack('>I',machine.mem_read(native_runtime['symbols']['gr2_boot_count'],4))[0]
        if candidate_mode:
            native_result['candidate_loaded_records']=[i for i in range(15) if machine.mem_read(context+0x108+i,1)==b'\x01']
            native_result['candidate_reservations_loaded']=all(struct.unpack('>I',machine.mem_read(row['address'],4))[0]==row['replacement'] for row in native_runtime['memory_reservations'])
    return dict(**native_result,stack_preserved=machine.reg_read(UC_ARM_REG_SP)==0x50018000,
                callee_saved_preserved=[machine.reg_read(registers.UC_ARM_REG_R4+index) for index in range(8)]==saved,entry='0xa0020944',module_indices=modules,events=events,returned=machine.reg_read(UC_ARM_REG_R0),
                post_load_call='0xa0020ab4',post_load_original_target='0xa0023234',post_load_return=post_load_return,
                post_load_original_bytes=code[0xA0020AB4-FILE_BASE:0xA0020AB8-FILE_BASE].hex(),
                helpers_intercepted=[hex(a) for a in calls],
                scope='Original startup branch/call order with explicit subsystem/wrapper-postaction boundaries. Candidate mode uses its actual source header/complete NAND byte stream and original indexed copy/zero/flag routines for requested modules; initial module0 load is separately proved. Storage device remains synthetic; no full hardware boot claim.')

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
        if startup['module_indices'][-1]!=14 or startup['events'][-5:]!=[['module',14],['post_load',0],['phase',0],['phase',0xffffffff],['finalize',0xffffffff]]:
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
